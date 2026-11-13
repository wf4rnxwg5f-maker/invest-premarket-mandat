import json, glob, sys, collections, datetime as dt
exec(open("ruletest.py").read().split("prefix=sys.argv[1]")[0])
def nwd_before(d,k):
    for _ in range(k): d=prevw(d)
    return d
def coupons(sec):
    try:
        cd=json.load(open(f"cpn/{sec}.json"))["coupons"]; ci={c:k for k,c in enumerate(cd["columns"])}
        return sorted(D.fromisoformat(x[ci["coupondate"]]) for x in cd["data"] if x[ci["coupondate"]])
    except Exception: return []
for prefix in ("y25","fwd"):
    rows=[]; cols=None
    for f in sorted(glob.glob(prefix+"_*.json")):
        d=json.load(open(f)); cols=d["offers"]["columns"]; rows+=d["offers"]["data"]
    i={c:k for k,c in enumerate(cols)}
    filled=[r for r in rows if r[i["offerdatestart"]] and r[i["offerdateend"]]]
    tot=collections.Counter(); hit=collections.Counter(); kdist=collections.Counter()
    for r in filled:
        sec=r[i["secid"]]; od=D.fromisoformat(r[i["offerdate"]]); e=D.fromisoformat(r[i["offerdateend"]]); name=r[i["name"]]; b=r[i["primary_boardid"]]
        cps=coupons(sec); prior=[c for c in cps if c<=od]; near=prior and (od-prior[-1]).days<=10
        struct = b in ("EQRP","RPEY") or "структур" in name.lower() or "ИОС" in name or "CIB" in name
        if struct:
            c="B структурные"; pred={nwd_before(od,2)}
            k=0; dd=od
            while dd>e and k<30: dd=prevw(dd); k+=1
            kdist[k if dd==e else None]+=1
        elif near and r[i["price"]] in (100,None):
            c="E целевой"; pred={last5_before(prior[-1])[1], last5_incl(prior[-1])[1]}
        else:
            c="C/D прочие (по соглашению, цена != 100, нет купона рядом)"; pred=set()
        tot[c]+=1; hit[c]+= (e in pred)
    n=len(filled); H=sum(hit.values())
    print("=====",prefix,"filled:",n,"| two-rule baseline end-date accuracy:",H,f"({H/n:.1%})")
    for c in tot: print(f"   {c}: {hit[c]}/{tot[c]} ({hit[c]/tot[c]:.1%})")
    print("   structured: working days from window end to offerdate:", sorted(kdist.items(), key=lambda x:-x[1])[:6])
