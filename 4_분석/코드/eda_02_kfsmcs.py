"""인증원 02(식품 제조가공 HACCP업체) 기준 핵심 수치 재산출"""
import csv, collections, os, datetime as dt
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))
A = rd("1_원천데이터/02_인증원_식품제조가공_HACCP업체정보.csv")
F = rd("1_원천데이터/09_식품안전나라_I1220_식품제조가공업.csv")
TODAY = "2026-09-26"

def sido_norm(s):
    s = s.strip()
    m = {"서울":"서울","부산":"부산","대구":"대구","인천":"인천","광주":"광주","대전":"대전","울산":"울산","세종":"세종",
         "경기":"경기","강원":"강원","충청북":"충북","충북":"충북","충청남":"충남","충남":"충남","전라북":"전북","전북":"전북",
         "전라남":"전남","전남":"전남","경상북":"경북","경북":"경북","경상남":"경남","경남":"경남","제주":"제주"}
    for k,v in m.items():
        if s.startswith(k): return v
    return "기타"

N_BUK = ("가평","고양","구리","남양주","동두천","양주","연천","의정부","파주","포천")
def branch(sido, sgg):
    if sido in ("서울","강원"): return "서울지원(강원출장소 포함)"
    if sido == "경기": return "서울지원(강원출장소 포함)" if sgg.startswith(N_BUK) else "경인지원"
    if sido == "인천": return "경인지원"
    if sido in ("대전","세종","충남","충북"): return "대전지원"
    if sido in ("광주","전남","전북","제주"): return "광주지원(제주출장소 포함)"
    if sido in ("대구","경북"): return "대구지원"
    if sido in ("부산","울산","경남"): return "부산지원"
    return "기타"

valid = [r for r in A if r["issueenddate"] >= TODAY]
print("인증원02 행(품목유형 단위)", len(A), "/ 유효", len(valid))
comp = {}
for r in valid:
    comp.setdefault(r["licenseno"], r)
print("유효 인증 업체", len(comp))

# 시도별 적용률 (분모: I1220 식품제조가공업 인허가번호)
den = collections.Counter(); deno = {}
for r in F:
    s = sido_norm(r["INSTT_NM"] or r["LOCP_ADDR"]); den[s] += 1; deno[r["LCNS_NO"]] = s
num = collections.Counter(deno.get(l) or sido_norm(r["sido"]) for l, r in comp.items())
tot_n = sum(num[s] for s in den if s != "기타"); tot_d = sum(v for s,v in den.items() if s != "기타")
print(f"\n전국 적용률 {tot_n}/{tot_d} = {tot_n/tot_d:.1%}")
rows = sorted(((s, num[s], den[s], num[s]/den[s]) for s in den if s != "기타"), key=lambda x: x[3])
for s,n,d,p in rows: print(f"  {s} {n}/{d} {p:.1%}")
with open("4_분석/결과/시도별_HACCP적용률_인증원기준.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["시도","HACCP업체","식품제조가공업체","적용률"]); w.writerows([(s,n,d,round(p,4)) for s,n,d,p in rows])

# 연장심사 수요: 연도·월·지원
yr = collections.Counter(r["issueenddate"][:4] for r in valid)
print("\n만료(품목유형 단위) 연도별", sorted(yr.items()))
cy = collections.Counter()
for l, rs in collections.defaultdict(list, {}).items(): pass
# 업체 단위: 업체별 가장 이른 만료
first_end = {}
for r in valid:
    l = r["licenseno"]; e = r["issueenddate"]
    if l not in first_end or e < first_end[l][0]: first_end[l] = (e, r)
cyr = collections.Counter(e[:4] for e,_ in first_end.values())
print("만료(업체 단위, 가장 이른 만료) 연도별", sorted(cyr.items()))
mon = collections.Counter(r["issueenddate"][:7] for r in valid if "2027" <= r["issueenddate"][:4] <= "2028")
mv = sorted(mon.values()); print("2027~28 월별 만료: 최소", mv[0], "최대", mv[-1], "평균", round(sum(mv)/len(mv)), "피크", mon.most_common(3))
br = collections.Counter(); bry = collections.Counter()
for r in valid:
    b = branch(sido_norm(r["sido"]), r["sgg"]); br[b]+=1
    if r["issueenddate"][:4] in ("2027","2028"): bry[(b, r["issueenddate"][:4])]+=1
print("\n지원별 만료 2027 / 2028")
for b in sorted(br): print(f"  {b}: {bry[(b,'2027')]} / {bry[(b,'2028')]}")
with open("4_분석/결과/연장심사수요_지원별월별.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["지원","만료연월","건수"])
    c=collections.Counter((branch(sido_norm(r["sido"]),r["sgg"]), r["issueenddate"][:7]) for r in valid)
    for (b,m),v in sorted(c.items()): w.writerow([b,m,v])

# 업종(품목유형) 상위, 업체당 품목유형 수
sp = collections.Counter(r["species"] for r in valid); print("\n상위 품목유형", sp.most_common(8))
per = collections.Counter(r["licenseno"] for r in valid); pv = sorted(per.values())
print("업체당 품목유형 수 중앙값", pv[len(pv)//2], "/ 1개뿐인 업체 비율", round(sum(1 for v in pv if v==1)/len(pv),3))
