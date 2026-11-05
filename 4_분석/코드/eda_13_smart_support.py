"""인증원 데이터 확장: 스마트HACCP 기술지원(12)·스마트HACCP 인증업체(07)를 첫 연장 체계에 결합
(A) 연계: 12(사업자번호·업체명·시도·시군구) → 인증원 현행(02)·I0580 업체명+시도+시군구 매칭
(B) 전환: 스마트HACCP 기술지원 식품 업체 중 스마트HACCP 등록(07) 업체 비율
(C) 접점: 2027~2028 첫 연장 대상(업체×만료일) 중 기술지원 이력·스마트HACCP 등록 비율
(D) 사후 검증 기술통계: 첫 연장 인증의 반납·취소율, 업체의 기술지원·스마트 등록 여부별(시점 미상 → 탐색적)"""
import os, re, json, math, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
src = open("4_분석/코드/eda_09_report_tables.py", encoding="utf-8").read().split("R[\"사후검증\"] = BT")[0]
src = src.replace("for S in [pd.Timestamp", "DUES = {}\nfor S in [pd.Timestamp").replace("    comp = due.groupby", "    DUES[lab] = due.copy()\n    comp = due.groupby")
exec(src)
O = {}
SIDO = {"강원특별자치도":"강원","강원도":"강원","전북특별자치도":"전북","전라북도":"전북","전라남도":"전남","경상남도":"경남","경상북도":"경북",
        "충청남도":"충남","충청북도":"충북","제주특별자치도":"제주","세종특별자치시":"세종"}
def sido(a):
    a = str(a).strip().split(" ")[0] if str(a).strip() else ""
    return SIDO.get(a, a[:2])
def sgg(a):
    t = str(a).strip().split(" "); return t[0] if t else ""
# --- 12 스마트HACCP 기술지원
s = pd.read_csv("1_원천데이터/12_인증원_스마트HACCP_기술지원업체.csv", dtype=str).fillna("")
O["12_행"] = len(s)
s = s[s.indutyNm.str.startswith("식품제조가공업")].copy()
s["nm"] = s.companyNm.map(norm); s["sd"] = s.area1.map(sido); s["sg"] = s.area2.map(sgg)
s = s.drop_duplicates(["nm","sd","sg"]); O["12_식품업체"] = len(s)
# 매칭 대상: I0580 식품제조가공업 전체 이력(d) → 업체(인허가번호) 단위
f = d.drop_duplicates("LCNS_NO")[["LCNS_NO","nm","SITE_ADDR"]].copy()
f["sd"] = f.SITE_ADDR.map(sido); f["sg"] = f.SITE_ADDR.str.split(" ").str[1].fillna("")
m = s.merge(f, on=["nm","sd"], how="left", suffixes=("","_f"))
m["ok_sg"] = m.apply(lambda r: isinstance(r.sg_f, str) and (r.sg[:2] == r.sg_f[:2]), axis=1)
m = m[m.LCNS_NO.isna() | m.ok_sg]
hit = m.dropna(subset=["LCNS_NO"])
O["12_매칭업체"] = int(hit.drop_duplicates(["nm","sd","sg"]).shape[0]); O["12_매칭률"] = round(O["12_매칭업체"]/O["12_식품업체"]*100,1)
SUP = set(hit.LCNS_NO)
# 인증원 현행(02) 업체와도 매칭(운영 모수)
A["nm"] = A.company.map(norm); A["sd"] = A.sido.map(sido)
a1 = A.drop_duplicates("licenseno")[["licenseno","nm","sd","sgg"]]
m2 = s.merge(a1, on=["nm","sd"]); m2 = m2[m2.sg.str[:2] == m2.sgg.str[:2]]
SUP |= set(m2.licenseno)
O["12_현행02매칭업체"] = int(m2.drop_duplicates(["nm","sd","sg"]).shape[0])
# --- 07 스마트HACCP 인증(등록) 업체
sm = pd.read_csv("1_원천데이터/07_인증원_식품_스마트HACCP_인증업체.csv", dtype=str).fillna("")
O["07_행"] = len(sm); O["07_업체"] = sm.licenseno.nunique(); O["07_등록연도"] = sm.drop_duplicates("licenseno").year.value_counts().sort_index().to_dict()
SMART = set(sm.licenseno)
# (B) 기술지원 → 스마트 등록 전환
sup_lic = set(hit.LCNS_NO) | set(m2.licenseno)
firms_sup = pd.concat([hit[["nm","sd","sg","LCNS_NO"]].rename(columns={"LCNS_NO":"lic"}), m2[["nm","sd","sg","licenseno"]].rename(columns={"licenseno":"lic"})]).drop_duplicates()
conv = firms_sup.groupby(["nm","sd","sg"]).lic.apply(lambda x: any(l in SMART for l in x))
O["전환_기술지원매칭업체"] = int(len(conv)); O["전환_스마트등록"] = int(conv.sum()); O["전환율"] = round(conv.mean()*100,1)
# (C) 2027~2028 첫 연장 대상 접점
full = open("4_분석/코드/eda_12_revision_v4.py", encoding="utf-8").read()
seg = full[full.index("A2 = A.copy()"):full.index("O[\"모수\"]")]
exec(seg)
u = A2.sort_values("fc", ascending=False).drop_duplicates(["licenseno","issueenddate"])
w = u[(u.end.dt.year >= 2027) & (u.end.dt.year <= 2028)].copy()
w["sup"] = w.licenseno.isin(SUP); w["smart"] = w.licenseno.isin(SMART)
C = {}
for k, g in [("첫 연장", w[w.fc]), ("2회차 이상", w[~w.fc]), ("전체", w)]:
    C[k] = dict(n=len(g), 업체=g.licenseno.nunique(), 기술지원=int(g.sup.sum()), 기술지원비율=round(g.sup.mean()*100,1),
                스마트=int(g.smart.sum()), 스마트비율=round(g.smart.mean()*100,1), 둘중하나=round((g.sup|g.smart).mean()*100,1))
O["접점_2027_2028"] = C
# (D) 사후 검증 기술통계(탐색적)
P = pd.concat([x.assign(snap=k) for k, x in DUES.items()])
SUP_BT = set(hit.LCNS_NO)   # 사후 검증은 전체 이력(I0580) 매칭만 사용(현행 목록 매칭은 생존 편향)
P["sup"] = P.LCNS_NO.isin(SUP_BT); P["smart"] = P.LCNS_NO.isin(SMART)
D = []
for grp, g in [("첫 연장", P[P.fc]), ("2회차 이상", P[~P.fc])]:
    for flag in ["sup","smart"]:
        a, b = g[g[flag]], g[~g[flag]]
        D.append(dict(구분=grp, 변수=flag, n1=len(a), e1=int(a.y.sum()), r1=round(a.y.mean()*100,2) if len(a) else None,
                      n0=len(b), e0=int(b.y.sum()), r0=round(b.y.mean()*100,2)))
O["사후검증_탐색"] = D
json.dump(O, open("4_분석/결과/smart_support.json","w",encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(O, ensure_ascii=False, indent=1, default=str))

# ---- (E) 통합 로지스틱: 첫 연장 × 기술지원 상호작용(시점 고정효과, 업체 군집 강건)
from math import erf, sqrt
pval = lambda z: 2*(1-0.5*(1+erf(abs(z)/sqrt(2))))
def logit_cl(X, y, g):
    Xm = np.c_[np.ones(len(X)), X]; b = np.zeros(Xm.shape[1])
    for _ in range(50):
        p = 1/(1+np.exp(-Xm@b)); H = Xm.T@(Xm*(p*(1-p))[:,None]); b += np.linalg.solve(H, Xm.T@(y-p))
    p = 1/(1+np.exp(-Xm@b)); Hi = np.linalg.inv(Xm.T@(Xm*(p*(1-p))[:,None]))
    S = pd.DataFrame(Xm*(y-p)[:,None]).groupby(np.asarray(g)).sum().values; G = len(S)
    return b, Hi@(S.T@S)@Hi*G/(G-1)
def ci(b, V, idx):
    c = np.zeros(len(b)); [c.__setitem__(i, 1) for i in idx]; e = c@b; se = math.sqrt(c@V@c)
    return dict(OR=round(math.exp(e),2), lo=round(math.exp(e-1.96*se),2), hi=round(math.exp(e+1.96*se),2), p=round(pval(e/se),4))
snapd = pd.get_dummies(P.snap, drop_first=True).astype(float).values
X = np.c_[P.fc, P.sup, P.fc & P.sup, P["비수도권"], P["김치절임"], P["의무"], snapd].astype(float)
b, V = logit_cl(X, P.y.astype(float).values, P.LCNS_NO.values)
O["상호작용_기술지원"] = {"첫 연장(미지원)": ci(b,V,[1]), "기술지원(2회차 이상 내)": ci(b,V,[2]), "첫연장×기술지원": ci(b,V,[3]),
                    "기술지원(첫 연장 내)": ci(b,V,[2,3])}
# 첫 연장 집단만: 기술지원 효과(통제)
F = P[P.fc]; sd_ = pd.get_dummies(F.snap, drop_first=True).astype(float).values
X = np.c_[F.sup, F["비수도권"], F["김치절임"], F["의무"], sd_].astype(float)
b, V = logit_cl(X, F.y.astype(float).values, F.LCNS_NO.values); O["첫연장내_기술지원_조정OR"] = ci(b,V,[1])
# 시점별 첫 연장 반납·취소율(지원/미지원)
O["시점별_첫연장_기술지원"] = [(k, int(g.sup.sum()), round(g[g.sup].y.mean()*100,1), int((~g.sup).sum()), round(g[~g.sup].y.mean()*100,1))
                          for k, g in P[P.fc].groupby("snap")]
# ---- (F) 스마트HACCP: 기준 시점 이전 등록 업체만 노출로 인정
yr = sm.drop_duplicates("licenseno").set_index("licenseno").year.astype(int)
P["smart_pre"] = P.apply(lambda r: r.LCNS_NO in yr.index and yr[r.LCNS_NO] <= int(r.snap[:4]), axis=1)
O["스마트_사전등록"] = [(grp, int(g.smart_pre.sum()), int(g[g.smart_pre].y.sum()), round(g[g.smart_pre].y.mean()*100,2) if g.smart_pre.any() else None,
                   round(g[~g.smart_pre].y.mean()*100,2)) for grp, g in [("첫 연장", P[P.fc]), ("2회차 이상", P[~P.fc])]]
# 매칭 정리
O["12_매칭_합집합업체"] = int(conv.shape[0]); O["12_매칭_합집합률"] = round(conv.shape[0]/O["12_식품업체"]*100,1)
json.dump(O, open("4_분석/결과/smart_support.json","w",encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
for k in ["상호작용_기술지원","첫연장내_기술지원_조정OR","시점별_첫연장_기술지원","스마트_사전등록","12_매칭_합집합업체","12_매칭_합집합률"]: print(k, O[k])
O["시점별_2회차_기술지원"] = [(k, int(g.sup.sum()), round(g[g.sup].y.mean()*100,1), round(g[~g.sup].y.mean()*100,1)) for k, g in P[~P.fc].groupby("snap")]
O["시점별_첫연장_스마트사전"] = [(k, int(g.smart_pre.sum()), int(g[g.smart_pre].y.sum()), round(g[~g.smart_pre].y.mean()*100,1)) for k, g in P[P.fc].groupby("snap")]
O["통합률"] = {k: (round(g[g.sup].y.mean()*100,2), round(g[~g.sup].y.mean()*100,2), int(g.sup.sum()), int((~g.sup).sum())) for k, g in [("첫",P[P.fc]),("2회차",P[~P.fc])]}
json.dump(O, open("4_분석/결과/smart_support.json","w",encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(O["시점별_2회차_기술지원"], O["시점별_첫연장_스마트사전"], O["통합률"])
