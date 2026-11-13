"""Пилот 1: насколько расходятся разумные прочтения расплывчатых понятий
на реальном списке бумаг Мосбиржи (данные MOEX ISS, торговый день 12.11.2026).

Запуск: python3 -I readings.py <каталог_данных> > readings.txt
"""
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

D = Path(sys.argv[1])
KEY_RATE = 14.0  # ключевая ставка Банка России на 12.11.2026 (сбор фактов, cbr.ru)

tq = json.loads((D / "tqbr.json").read_text())
sec_cols = tq["securities"]["columns"]
md_cols = tq["marketdata"]["columns"]
sec = {r[0]: dict(zip(sec_cols, r)) for r in tq["securities"]["data"]}
md = {r[0]: dict(zip(md_cols, r)) for r in tq["marketdata"]["data"]}
shares = {k: v for k, v in sec.items() if v["SECTYPE"] in ("1", "2", "D")}

hist = json.loads((D / "tqbr_history.json").read_text())
turn = defaultdict(list)
for secid, date, value, ntr, close in hist["rows"]:
    turn[secid].append(value or 0.0)
ndays = len(hist["dates"])
med_turn = {k: statistics.median(turn[k] + [0.0] * (ndays - len(turn[k]))) if turn[k] else 0.0 for k in shares}

idx = json.loads((D / "indices.json").read_text())
in_bmi = set(idx["MOEXBMI"]["members"])
in_imoex = set(idx["IMOEX"]["members"])
in_bc = set(idx["MOEXBC"]["members"])

cap = {k: (md.get(k, {}).get("ISSUECAPITALIZATION") or 0.0) for k in shares}

print(f"Данные: MOEX ISS, режим TQBR, {len(shares)} акций и расписок; история оборота за {ndays} торговых дней "
      f"({hist['dates'][0]} — {hist['dates'][-1]}); составы индексов на {idx['IMOEX']['date']}.")
print()

# ---------- «Третий эшелон» ----------
THR = 10e6
r1 = {k for k, v in shares.items() if str(v["LISTLEVEL"]) == "3"}
r2 = {k for k in shares if k not in in_bmi}
r3 = {k for k in shares if med_turn[k] < THR}
readings = {"R1: третий уровень листинга": r1,
            "R2: вне индекса широкого рынка MOEXBMI": r2,
            f"R3: медианный оборот < {THR/1e6:.0f} млн ₽ в день": r3}
print("=== «Третий эшелон» — три разумных прочтения ===")
for name, s in readings.items():
    print(f"{name}: {len(s)} бумаг")
all3 = r1 & r2 & r3
any3 = r1 | r2 | r3
print(f"Совпадают во всех трёх прочтениях (запрещены везде): {len(all3)}")
print(f"Запрещены хотя бы в одном прочтении: {len(any3)}")
dis = any3 - all3
print(f"Бумаг, по которым решение зависит от прочтения: {len(dis)} из {len(shares)} ({len(dis)/len(shares):.0%})")


def jacc(a, b):
    return len(a & b) / len(a | b) if a | b else 1.0


names = list(readings)
for i in range(3):
    for j in range(i + 1, 3):
        a, b = readings[names[i]], readings[names[j]]
        print(f"  {names[i][:2]} vs {names[j][:2]}: Жаккар {jacc(a, b):.2f}; только в {names[i][:2]}: {len(a-b)}, только в {names[j][:2]}: {len(b-a)}")

top_turn = sorted(shares, key=lambda k: -med_turn[k])
rank = {k: i + 1 for i, k in enumerate(top_turn)}
print("\nПримеры: 3-й уровень листинга, но ликвидные (в топ-60 по медианному обороту):")
ex = sorted([k for k in r1 if rank[k] <= 60], key=lambda k: rank[k])
for k in ex[:10]:
    print(f"  {k} {shares[k]['SHORTNAME']}: место по обороту {rank[k]}, медиана {med_turn[k]/1e6:.0f} млн ₽/день, "
          f"капитализация {cap[k]/1e9:.0f} млрд ₽, в MOEXBMI: {'да' if k in in_bmi else 'нет'}")
print("Примеры: 1-й уровень листинга, но неликвидные (медиана < 10 млн ₽):")
ex2 = sorted([k for k, v in shares.items() if str(v["LISTLEVEL"]) == "1" and med_turn[k] < THR], key=lambda k: med_turn[k])
print(f"  всего таких: {len(ex2)}; например: " + ", ".join(f"{k} ({med_turn[k]/1e6:.1f} млн)" for k in ex2[:8]))
print("Примеры: в индексе MOEXBMI, но медианный оборот < 10 млн ₽:")
ex3 = sorted([k for k in in_bmi if k in shares and med_turn[k] < THR], key=lambda k: med_turn[k])
print(f"  всего таких: {len(ex3)}; например: " + ", ".join(f"{k} ({med_turn[k]/1e6:.1f} млн)" for k in ex3[:8]))
zero = [k for k in shares if med_turn[k] == 0]
print(f"Бумаг с медианным оборотом 0 (торгов не было в большинство дней): {len(zero)}")

# ---------- «Голубые фишки» ----------
print("\n=== «Голубые фишки» — три прочтения по 15 бумаг ===")
b1 = set(k for k in in_bc if k in shares)
b2 = set(sorted(shares, key=lambda k: -cap[k])[:15])
b3 = set(top_turn[:15])
print(f"B1 индекс MOEXBC: {sorted(b1)}")
print(f"B2 топ-15 по капитализации: {sorted(b2)}")
print(f"B3 топ-15 по медианному обороту: {sorted(b3)}")
print(f"Во всех трёх: {len(b1&b2&b3)}; хотя бы в одном: {len(b1|b2|b3)}")
print(f"  только B2 (крупные, но не в индексе): {sorted(b2 - b1)}")
print(f"  только B3 (ликвидные, но не в индексе): {sorted(b3 - b1)}")

# ---------- «ВДО» ----------
cb = json.loads((D / "tqcb.json").read_text())
cs = {r[0]: dict(zip(cb["securities"]["columns"], r)) for r in cb["securities"]["data"]}
cm = {r[0]: dict(zip(cb["marketdata"]["columns"], r)) for r in cb["marketdata"]["data"]}
rub = [k for k, v in cs.items() if v["FACEUNIT"] in ("SUR", "RUB")]
traded = [k for k in rub if (cm.get(k, {}).get("NUMTRADES") or 0) > 0 and (cm[k].get("YIELD") or 0) > 0]
v1 = {k for k in traded if str(cs[k]["LISTLEVEL"]) == "3"}
v2 = {k for k in traded if cm[k]["YIELD"] >= KEY_RATE + 5}
v3 = {k for k in traded if cm[k]["YIELD"] >= KEY_RATE + 3}
print(f"\n=== «ВДО» — рублёвые корпоративные облигации TQCB с ненулевой доходностью и сделками 12.11.2026: {len(traded)} ===")
print(f"V1 третий уровень листинга: {len(v1)}")
print(f"V2 доходность ≥ ключевая ставка + 5 п.п. (≥ {KEY_RATE+5:.0f}%): {len(v2)}")
print(f"V3 доходность ≥ ключевая ставка + 3 п.п. (≥ {KEY_RATE+3:.0f}%): {len(v3)}")
print(f"V1 и V2 одновременно: {len(v1&v2)}; только V1: {len(v1-v2)}; только V2: {len(v2-v1)}; Жаккар {jacc(v1, v2):.2f}")
print(f"Решение зависит от прочтения (V1 vs V2): {len(v1 ^ v2)} из {len(traded)} ({len(v1 ^ v2)/len(traded):.0%})")

# ---------- «Одна компания» ----------
em = json.loads((D / "gazprom_emitters.json").read_text())
print("\n=== «Не больше 10% в Газпром» — кого считать (справочник эмитентов MOEX ISS, торгуемые инструменты) ===")
for eid, e in em.items():
    tr = [r for r in e["rows"] if r.get("IS_TRADED") == 1]
    kinds = Counter(r.get("TYPE") for r in tr)
    print(f"  эмитент {eid} {e['title']}: {len(tr)} торгуемых — {dict(kinds)}")

print(f"\nКлючевая ставка, принятая в расчёте: {KEY_RATE}%")
