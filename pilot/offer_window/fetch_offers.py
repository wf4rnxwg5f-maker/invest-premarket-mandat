"""Загрузка данных MOEX ISS для проверки «окна оферты» (данные биржи в репозиторий не кладём).

Запуск из этого каталога:  python3 fetch_offers.py
Создаёт: y25_<start>.json (оферты 2025 г.), fwd_<start>.json (оферты на год вперёд от 12.11.2026),
cpn/<secid>.json (купоны выпусков). Затем:  python3 ruletest3.py
"""
import json
import subprocess
import time
from pathlib import Path

BASE = "https://iss.moex.com/iss/statistics/engines/stock/markets/bonds/bondization"


def get(url):
    for attempt in range(4):
        try:
            r = subprocess.run(["curl", "-sS", "-m", "40", "--fail", url], capture_output=True, check=True)
            return json.loads(r.stdout)
        except Exception:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))


def offers(prefix, frm, till):
    secids = set()
    start = 0
    while True:
        d = get(f"{BASE}.json?from={frm}&till={till}&iss.only=offers&iss.meta=off&limit=100&start={start}")
        Path(f"{prefix}_{start}.json").write_text(json.dumps(d, ensure_ascii=False))
        cols = d["offers"]["columns"]
        rows = d["offers"]["data"]
        secids |= {r[cols.index("secid")] for r in rows}
        if len(rows) < 100:
            return secids
        start += 100


def main():
    secids = offers("y25", "2025-01-01", "2025-12-31") | offers("fwd", "2026-11-12", "2027-11-12")
    Path("cpn").mkdir(exist_ok=True)
    for s in sorted(secids):
        out = Path("cpn") / f"{s}.json"
        if out.exists() and out.stat().st_size:
            continue
        d = get(f"{BASE}/{s}.json?iss.only=coupons&iss.meta=off&limit=100&from=2024-06-01&till=2028-03-01")
        out.write_text(json.dumps(d, ensure_ascii=False))
    print("выпусков:", len(secids))


if __name__ == "__main__":
    main()
