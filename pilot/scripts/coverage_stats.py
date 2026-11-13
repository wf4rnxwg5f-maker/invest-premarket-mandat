"""Пилот 2: статистика покрытия правил инвесторов формой лимитов.

Вход: JSON результата сбора и разметки (sets, items, checks, passes).
Запуск: python3 -I coverage_stats.py <raw.json> <out_dir>
"""
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

raw = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

items = {it["id"]: it for it in raw["items"]}
sets = {s["sid"]: s for s in raw["sets"]}

p1, p2, adj = {}, {}, {}
for ch in raw["passes"]:
    for l in ch["p1"]:
        p1[l["id"]] = l
    for l in ch["p2"]:
        p2[l["id"]] = l
    for l in ch["adj"]:
        adj[l["id"]] = l

final = {}
for cid in items:
    a, b = p1.get(cid), p2.get(cid)
    if a and b and a["cat"] == b["cat"]:
        final[cid] = dict(a, src="agree")
    elif cid in adj:
        final[cid] = dict(adj[cid], src="adjudicated")
    elif a or b:
        final[cid] = dict(a or b, src="single")
cats = "ABCDE"


def kappa(x, y):
    ids = [i for i in items if i in x and i in y]
    n = len(ids)
    po = sum(x[i]["cat"] == y[i]["cat"] for i in ids) / n
    cx = Counter(x[i]["cat"] for i in ids)
    cy = Counter(y[i]["cat"] for i in ids)
    pe = sum(cx[c] * cy[c] for c in cats) / n / n
    return n, po, (po - pe) / (1 - pe) if pe < 1 else 1.0


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def cluster_boot(ids, pred, B=4000, seed=20261113):
    """Бутстреп по наборам правил (кластер = автор/источник)."""
    by = defaultdict(list)
    for i in ids:
        by[items[i]["sid"]].append(i)
    keys = list(by)
    rng = random.Random(seed)
    vals = []
    for _ in range(B):
        sample = [rng.choice(keys) for _ in keys]
        num = den = 0
        for k in sample:
            for i in by[k]:
                den += 1
                num += pred(i)
        if den:
            vals.append(num / den)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]


lines = []
P = lines.append

n_sets = len(sets)
by_kind = Counter(s["source_kind"] for s in sets.values())
by_lang = Counter(s["lang"] for s in sets.values())
P(f"Наборов правил: {n_sets} (по типу: {dict(by_kind)}; по языку: {dict(by_lang)})")
P(f"Правил (атомарных): {len(items)}; размечено: {len(final)}")
n, po, k = kappa(p1, p2)
P(f"Согласие двух независимых проходов: {po:.0%} совпадений, каппа Коэна {k:.2f} (n={n}); "
  f"расхождений разобрано арбитражем: {sum(1 for f in final.values() if f['src']=='adjudicated')}")

checks = raw.get("checks", [])
if checks:
    qt = sum(c.get("quotes_total", 0) for c in checks)
    qf = sum(c.get("quotes_found", 0) for c in checks)
    op = sum(1 for c in checks if c.get("opened"))
    fp = sum(1 for c in checks if c.get("first_person"))
    P(f"Выборочная сверка с первоисточником: {len(checks)} источников, открылись {op}, "
      f"цитат найдено {qf} из {qt} ({qf/qt:.0%}), от первого лица {fp}")
    bad_urls = {c["source_url"] for c in checks if not c.get("opened") or c.get("quotes_total", 0) and c.get("quotes_found", 0) / c["quotes_total"] < 0.5}
    P(f"Источников, не прошедших сверку (не открылись или найдено < 50% цитат): {len(bad_urls)}")
else:
    bad_urls = set()


def report(title, ids):
    cnt = Counter(final[i]["cat"] for i in ids if i in final)
    tot = sum(cnt.values())
    P(f"\n=== {title}: {tot} правил из {len({items[i]['sid'] for i in ids})} наборов ===")
    for c, name in zip(cats, ["A форма", "B язык правил, не форма", "C расплывчатое понятие", "D не проверяется на заявке", "E правило-обязанность"]):
        P(f"  {name}: {cnt[c]} ({cnt[c]/tot:.0%})")
    enf = [i for i in ids if i in final and final[i]["cat"] in "ABC"]
    a = sum(1 for i in enf if final[i]["cat"] == "A")
    a_strict = sum(1 for i in enf if final[i]["cat"] == "A" and not final[i].get("approx"))
    if enf:
        lo, hi = wilson(a, len(enf))
        blo, bhi = cluster_boot(enf, lambda i: final[i]["cat"] == "A")
        P(f"  Проверяемых ограничений (A+B+C): {len(enf)}")
        P(f"  Покрытие формой (A / A+B+C): {a/len(enf):.0%}  [Уилсон {lo:.0%}–{hi:.0%}; бутстреп по наборам {blo:.0%}–{bhi:.0%}]")
        P(f"  Покрытие формой без приближений (A без approx): {a_strict/len(enf):.0%}")
        tail = len(enf) - a
        P(f"  «Хвост» (B+C): {tail} ({tail/len(enf):.0%}); из них C: {sum(1 for i in enf if final[i]['cat']=='C')}")
        sets_with_tail = len({items[i]["sid"] for i in enf if final[i]["cat"] in "BC"})
        sets_enf = len({items[i]["sid"] for i in enf})
        P(f"  Наборов, где есть хотя бы одно ограничение вне формы: {sets_with_tail} из {sets_enf} ({sets_with_tail/sets_enf:.0%})")
    fields = Counter(final[i].get("field", "") for i in ids if i in final and final[i]["cat"] == "A")
    P(f"  Поля формы (A): {dict(fields.most_common())}")
    preds = Counter((final[i].get("predicate") or "").strip().lower()[:60] for i in ids if i in final and final[i]["cat"] == "B")
    P(f"  Типы предикатов (B), топ-12: {preds.most_common(12)}")
    conc = Counter((final[i].get("concept") or "").strip().lower()[:40] for i in ids if i in final and final[i]["cat"] == "C")
    P(f"  Расплывчатые понятия (C), топ-15: {conc.most_common(15)}")


all_ids = list(items)
report("ВСЕ источники", all_ids)
real = [i for i in all_ids if items[i]["kind"] in ("personal", "strategy")]
report("Только личные правила и стратегии (без статей-подборок)", real)
ru = [i for i in real if items[i]["lang"] == "ru"]
report("Личные и стратегии, русскоязычные", ru)
en = [i for i in real if items[i]["lang"] == "en"]
report("Личные и стратегии, англоязычные", en)
if bad_urls:
    good = [i for i in real if sets[items[i]["sid"]]["source_url"] not in bad_urls]
    report("Личные и стратегии без источников, не прошедших сверку", good)

# примеры для анкеты
P("\n=== Примеры правил вне формы (B и C), по 2 на набор, до 40 ===")
shown = Counter()
for i in real:
    f = final.get(i)
    if f and f["cat"] in "BC" and shown[items[i]["sid"]] < 2 and sum(shown.values()) < 40:
        shown[items[i]["sid"]] += 1
        P(f"  [{f['cat']}] {items[i]['paraphrase']}  ←  {(f.get('predicate') or f.get('concept') or '')}")

(out / "stats.txt").write_text("\n".join(lines), encoding="utf-8")
(out / "labels.json").write_text(json.dumps({"final": final}, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n".join(lines))
