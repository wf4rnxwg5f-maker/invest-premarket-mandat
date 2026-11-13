"""Пилот 3: компиляция реальных мандатов двумя моделями и стабильность LLM-судьи.

Запуск: python3 -I pilot3_stats.py <raw_p3.json> <pilot_dir>
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

raw = json.loads(Path(sys.argv[1]).read_text())
pdir = Path(sys.argv[2])
labels = json.loads((pdir / "coverage" / "labels.json").read_text())["final"]
lines = []
P = lines.append

# ---------- компиляция ----------
mand = {}
mdir = pdir / "p3" / "mandates"
if not mdir.exists():                      # в публичной копии цитаты авторов убраны
    mdir = pdir / "p3" / "mandates_public"
for f in sorted(mdir.glob("M*.json")):
    m = json.loads(f.read_text())
    mand[m["mid"]] = [c["cid"] for c in m["constraints"]]
n_items = sum(len(v) for v in mand.values())
models = sorted({c["model"] for c in raw["compiled"]})
out = defaultdict(dict)   # model -> cid -> item
for c in raw["compiled"]:
    for it in c["items"]:
        out[c["model"]][it["cid"]] = it

P(f"Компиляция: {len(mand)} мандатов, {n_items} пунктов, модели: {', '.join(models)}")
LIMIT = {"rule", "needs_clarification", "cannot_express"}
NONLIM = {"principle", "duty"}
for model in models:
    o = out[model]
    missing = [cid for cids in mand.values() for cid in cids if cid not in o]
    by = defaultdict(list)
    for cids in mand.values():
        for cid in cids:
            by[labels[cid]["cat"]].append(cid)
    st = lambda cid: o.get(cid, {}).get("status")  # noqa: E731
    lim = by["A"] + by["B"] + by["C"]
    non = by["D"] + by["E"]
    kept = sum(st(c) in LIMIT for c in lim)
    sep = sum(st(c) in NONLIM for c in non)
    cflag = sum(st(c) == "needs_clarification" for c in by["C"])
    csilent = sum(st(c) == "rule" for c in by["C"])
    afalse = sum(st(c) == "needs_clarification" for c in by["A"])
    abrule = sum(st(c) == "rule" for c in by["A"] + by["B"])
    P(f"\n[{model}] пропущено молча: {len(missing)} из {n_items}")
    P(f"  лимиты (A+B+C) не потеряны как «принцип/обязанность»: {kept}/{len(lim)} ({kept/len(lim):.0%})")
    P(f"  принципы и обязанности (D+E) отделены от лимитов: {sep}/{len(non)} ({sep/len(non):.0%})")
    P(f"  расплывчатые (C) помечены «нужно уточнить»: {cflag}/{len(by['C'])}; молча истолкованы как правило: {csilent}/{len(by['C'])}")
    P(f"  точные (A) ошибочно помечены «нужно уточнить»: {afalse}/{len(by['A'])}")
    P(f"  A+B скомпилированы в правило: {abrule}/{len(by['A'])+len(by['B'])}; остальное — «не могу выразить» или уточнение")
    P(f"  статусы: {dict(Counter(st(c) for cids in mand.values() for c in cids))}")

if len(models) == 2:
    a, b = models
    def coarse(s):
        return {"rule": "R", "cannot_express": "R", "needs_clarification": "Q", "principle": "N", "duty": "N"}.get(s, "?")
    ids = [cid for cids in mand.values() for cid in cids if cid in out[a] and cid in out[b]]
    agree = sum(out[a][c]["status"] == out[b][c]["status"] for c in ids)
    agree_c = sum(coarse(out[a][c]["status"]) == coarse(out[b][c]["status"]) for c in ids)
    P(f"\nСогласие двух моделей: по 5 статусам {agree}/{len(ids)} ({agree/len(ids):.0%}); "
      f"по укрупнённым (правило / уточнить / не лимит) {agree_c}/{len(ids)} ({agree_c/len(ids):.0%})")
    for cat in "ABCDE":
        cc = [c for c in ids if labels[c]["cat"] == cat]
        if cc:
            d = sum(out[a][c]["status"] != out[b][c]["status"] for c in cc)
            P(f"  расхождение моделей на пунктах {cat}: {d}/{len(cc)} ({d/len(cc):.0%})")
    both_rule = [c for c in ids if out[a][c]["status"] == "rule" and out[b][c]["status"] == "rule"]
    same_kind = sum(
        (out[a][c].get("rules") or [{}])[0].get("rule_kind") == (out[b][c].get("rules") or [{}])[0].get("rule_kind")
        for c in both_rule)
    P(f"  где обе скомпилировали правило, первый тип правила совпал: {same_kind}/{len(both_rule)}")

# ---------- судья ----------
stocks = {s["ticker"]: s for s in json.loads((pdir / "p3" / "stocks.json").read_text())}
J = defaultdict(dict)   # (pi, run) -> ticker -> decision
for j in raw["judged"]:
    for v in j["verdicts"]:
        J[(j["pi"], j["run"])][v["ticker"]] = v["decision"]
phr = sorted({j["pi"] for j in raw["judged"]})
P(f"\nLLM-судья без уточнения: {len(phr)} перефразировок «третьего эшелона» × 2 прогона × {len(stocks)} акций")
for zone in ("divergent", "control"):
    tick = [t for t, s in stocks.items() if s["zone"] == zone]
    incons = 0
    flips = 0
    pairs = 0
    dist = Counter()
    for t in tick:
        vs = [J[(pi, 1)].get(t) for pi in phr]
        vs = [v for v in vs if v]
        dist.update(vs)
        if len(set(vs)) > 1:
            incons += 1
        for pi in phr:
            x, y = J[(pi, 1)].get(t), J[(pi, 2)].get(t)
            if x and y:
                pairs += 1
                flips += x != y
    P(f"  {zone}: бумаг {len(tick)}; вердикт зависит от формулировки у {incons} ({incons/len(tick):.0%}); "
      f"смена вердикта при повторном прогоне той же формулировки: {flips}/{pairs} ({flips/pairs:.0%}); решения: {dict(dist)}")
for t in ("MGNT", "SIBN", "SPBE", "FESH", "LEAS", "PIKK"):
    if t in stocks:
        P(f"  {t}: " + ", ".join(f"p{pi+1}:{J[(pi,1)].get(t)}/{J[(pi,2)].get(t)}" for pi in phr))

(pdir / "p3" / "stats.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
