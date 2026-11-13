import json, glob, sys, collections, datetime as dt
D=dt.date
hol=set()
def add(y,m,days):
    for d in days: hol.add(D(y,m,d))
add(2024,1,[1,2,3,4,5,8]); add(2024,2,[23]); add(2024,3,[8]); add(2024,4,[29,30]); add(2024,5,[1,9,10]); add(2024,6,[12]); add(2024,11,[4]); add(2024,12,[30,31])
add(2025,1,[1,2,3,6,7,8]); add(2025,5,[1,2,8,9]); add(2025,6,[12,13]); add(2025,11,[3,4]); add(2025,12,[31])
add(2026,1,[1,2,5,6,7,8,9]); add(2026,2,[23]); add(2026,3,[9]); add(2026,5,[1,11]); add(2026,6,[12]); add(2026,11,[4]); add(2026,12,[31])
add(2027,1,[1,4,5,6,7,8]); add(2027,2,[23]); add(2027,3,[8]); add(2027,5,[3,10]); add(2027,6,[14]); add(2027,11,[4])
worksat={D(2024,4,27),D(2024,11,2),D(2024,12,28),D(2025,11,1)}
def isw(d): return (d.weekday()<5 and d not in hol) or d in worksat
def prevw(d):
    d-=dt.timedelta(days=1)
    while not isw(d): d-=dt.timedelta(days=1)
    return d
def last5_before(d):
    e=prevw(d); s=e
    for _ in range(4): s=prevw(s)
    return s,e
def last5_incl(d):
    e=d if isw(d) else prevw(d); s=e
    for _ in range(4): s=prevw(s)
    return s,e
def wdays_between(a,b):
    n=0; d=a
    while d<=b:
        if isw(d): n+=1
        d+=dt.timedelta(days=1)
    return n
prefix=sys.argv[1]
rows=[]; cols=None
for f in sorted(glob.glob(prefix+"_*.json")):
    d=json.load(open(f)); cols=d["offers"]["columns"]; rows+=d["offers"]["data"]
i={c:k for k,c in enumerate(cols)}
filled=[r for r in rows if r[i["offerdatestart"]] and r[i["offerdateend"]]]
print("total", len(rows), "filled", len(filled))
res=collections.Counter(); misses=[]; wd=collections.Counter(); bytype=collections.defaultdict(collections.Counter)
for r in filled:
    sec=r[i["secid"]]; od=D.fromisoformat(r[i["offerdate"]]); s=D.fromisoformat(r[i["offerdatestart"]]); e=D.fromisoformat(r[i["offerdateend"]])
    try:
        cd=json.load(open(f"cpn/{sec}.json"))["coupons"]; ci={c:k for k,c in enumerate(cd["columns"])}
        cps=sorted(D.fromisoformat(x[ci["coupondate"]]) for x in cd["data"] if x[ci["coupondate"]])
    except Exception as ex:
        cps=[]
    wd[wdays_between(s,e)]+=1
    prior=[c for c in cps if c<=od]
    if not prior:
        res["no_coupon_before_offer"]+=1; misses.append((r,None,"nocpn")); bytype[r[i["offertype"]]]["miss"]+=1; continue
    cdate=prior[-1]
    A=last5_before(cdate); B=last5_incl(cdate)
    ok_full = (s,e)==A or (s,e)==B
    ok_end = e in (A[1],B[1])
    tol = abs((e-A[1]).days)<=1 or abs((e-B[1]).days)<=1
    if (s,e)==A: res["full_A(5wd before coupon date)"]+=1
    elif (s,e)==B: res["full_B(5wd incl coupon date)"]+=1
    if ok_full: res["full_any"]+=1
    if ok_end: res["end_any"]+=1
    if tol: res["end_within_1d"]+=1
    bytype[r[i["offertype"]]]["hit" if ok_end else "miss"]+=1
    if not ok_end: misses.append((r,cdate,(od-cdate).days))
n=len(filled)
for k,v in res.most_common(): print(f"{k}: {v} ({v/n:.1%})")
print("working days in actual window:", sorted(wd.items()))
print("by type (end-date rule):", {k:dict(v) for k,v in bytype.items()})
print("MISSES (end date):", len(misses))
for r,cdate,x in misses[:70]:
    print("  ", r[i["offerdate"]], r[i["offerdatestart"]], r[i["offerdateend"]], "cpn:",cdate, x, "|", r[i["offertype"]], "|", r[i["name"]], r[i["primary_boardid"]], r[i["price"]])
