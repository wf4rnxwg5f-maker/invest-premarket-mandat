"""Скачивает с MOEX ISS данные для пилота «расхождение прочтений»:
- история торгов TQBR за последние N торговых дней (оборот по каждой бумаге);
- составы индексов IMOEX, MOEXBMI, MOEXBC, MCXSM, MOEXRE.
Запуск: python3 -I fetch_iss.py <каталог_данных> [N_дней]
"""
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = "https://iss.moex.com/iss"


def get(url):
    # curl использует системное хранилище сертификатов (у python.org-сборки его нет)
    for attempt in range(4):
        try:
            res = subprocess.run(["curl", "-sS", "-m", "30", "--fail", url],
                                 capture_output=True, check=True)
            return json.loads(res.stdout.decode("utf-8"))
        except Exception:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))


def main():
    out = Path(sys.argv[1])
    ndays = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    out.mkdir(parents=True, exist_ok=True)

    # 0) снимки режимов TQBR (акции) и TQCB (корпоративные облигации) на текущий день
    snap = {
        "tqbr.json": "/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off&iss.only=securities,marketdata"
                     "&securities.columns=SECID,SHORTNAME,SECNAME,LISTLEVEL,SECTYPE,ISIN,LOTSIZE,ISSUESIZE"
                     "&marketdata.columns=SECID,VALTODAY,ISSUECAPITALIZATION,NUMTRADES,SYSTIME",
        "tqcb.json": "/engines/stock/markets/bonds/boards/TQCB/securities.json?iss.meta=off&iss.only=securities,marketdata"
                     "&securities.columns=SECID,SHORTNAME,LISTLEVEL,ISIN,MATDATE,OFFERDATE,FACEUNIT,COUPONPERCENT"
                     "&marketdata.columns=SECID,YIELD,VALTODAY,NUMTRADES,DURATION,SYSTIME",
    }
    for name, path in snap.items():
        (out / name).write_text(json.dumps(get(BASE + path), ensure_ascii=False))

    # 1) торговые дни — по истории SBER
    h = get(f"{BASE}/history/engines/stock/markets/shares/boards/TQBR/securities/SBER.json"
            f"?iss.meta=off&iss.only=history&history.columns=TRADEDATE,VALUE&from=2026-09-20&till=2026-11-13")
    dates = [r[0] for r in h["history"]["data"] if r[1]]
    dates = dates[-ndays:]
    print("торговые дни:", dates[0], "…", dates[-1], len(dates))

    # 2) история по всем бумагам TQBR за каждый день
    rows = []
    for d in dates:
        start = 0
        while True:
            j = get(f"{BASE}/history/engines/stock/markets/shares/boards/TQBR/securities.json"
                    f"?iss.meta=off&iss.only=history,history.cursor&date={d}&start={start}"
                    f"&history.columns=SECID,TRADEDATE,VALUE,NUMTRADES,CLOSE")
            data = j["history"]["data"]
            rows.extend(data)
            cur = j["history.cursor"]["data"][0]  # INDEX, TOTAL, PAGESIZE
            start = cur[0] + cur[2]
            if start >= cur[1]:
                break
    (out / "tqbr_history.json").write_text(json.dumps({"dates": dates, "rows": rows}, ensure_ascii=False))
    print("строк истории:", len(rows))

    # 3) составы индексов
    idx = {}
    for code in ["IMOEX", "MOEXBMI", "MOEXBC", "MCXSM", "MOEXRE"]:
        j = get(f"{BASE}/statistics/engines/stock/markets/index/analytics/{code}.json?iss.meta=off&limit=100")
        cols = j["analytics"]["columns"]
        data = j["analytics"]["data"]
        start = 100
        cur = j.get("analytics.cursor", {}).get("data", [[0, len(data), 100]])[0]
        while start < cur[1]:
            jj = get(f"{BASE}/statistics/engines/stock/markets/index/analytics/{code}.json?iss.meta=off&limit=100&start={start}")
            data += jj["analytics"]["data"]
            start += 100
        i_sec = cols.index("secids") if "secids" in cols else cols.index("ticker")
        i_w = cols.index("weight")
        i_d = cols.index("tradedate")
        idx[code] = {"date": data[0][i_d] if data else None,
                     "members": {r[i_sec]: r[i_w] for r in data}}
        print(code, idx[code]["date"], len(idx[code]["members"]))
    (out / "indices.json").write_text(json.dumps(idx, ensure_ascii=False))

    # 4) пример «одна компания»: бумаги эмитентов по справочнику эмитентов ISS (полный список, без поиска)
    emitters = {"711": "ПАО «Газпром»", "4682": "ООО «Газпром капитал»", "1039": "ПАО «Газпром нефть»", "196": "АО «Газпромбанк»"}
    em = {}
    for eid, title in emitters.items():
        j = get(f"{BASE}/emitters/{eid}/securities.json?iss.meta=off")
        cols = j["securities"]["columns"]
        em[eid] = {"title": title, "rows": [dict(zip(cols, r)) for r in j["securities"]["data"]]}
        print(title, len(em[eid]["rows"]))
    (out / "gazprom_emitters.json").write_text(json.dumps(em, ensure_ascii=False))


if __name__ == "__main__":
    main()
