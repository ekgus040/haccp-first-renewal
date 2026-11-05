"""기획서 v4: (1) 반납·취소 주분석, 보정 미갱신은 확장 (2) 운영 모수=인증원 현행 API
(3) 첫 연장×단일품목 상호작용 (4) 업체 군집 강건표준오차 (5) 설계 기반 최소탐지효과"""
import os, re, json, math, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
src = open("4_분석/코드/eda_09_report_tables.py", encoding="utf-8").read().split("R[\"사후검증\"] = BT")[0]
src = src.replace("for S in [pd.Timestamp", "DUES = {}; XS = {}\nfor S in [pd.Timestamp").replace("    comp = due.groupby", "    DUES[lab] = due.copy(); XS[lab] = x.copy()\n    comp = due.groupby")
exec(src)
from math import erf, sqrt
pval = lambda z: 2*(1-0.5*(1+erf(abs(z)/sqrt(2))))
def logit_cl(X, y, g, names):
    Xm = np.c_[np.ones(len(X)), X]; b = np.zeros(Xm.shape[1])
    for _ in range(40):
        p = 1/(1+np.exp(-Xm@b)); H = Xm.T@(Xm*(p*(1-p))[:,None]); b += np.linalg.solve(H, Xm.T@(y-p))
    p = 1/(1+np.exp(-Xm@b)); H = Xm.T@(Xm*(p*(1-p))[:,None]); Hi = np.linalg.inv(H)
    S = pd.DataFrame(Xm*(y-p)[:,None]).groupby(np.asarray(g)).sum().values; G = len(S)
    V = Hi@(S.T@S)@Hi*G/(G-1); se = np.sqrt(np.diag(V)); se_naive = np.sqrt(np.diag(Hi))
    out = {}
    for k, nm in enumerate(names, start=1):
        out[nm] = dict(OR=round(math.exp(b[k]),2), lo=round(math.exp(b[k]-1.96*se[k]),2), hi=round(math.exp(b[k]+1.96*se[k]),2),
                       p=round(pval(b[k]/se[k]),4), se_ratio=round(se[k]/se_naive[k],2))
    return out, b, V
O = {"BT": [], "STRAT": [], "LOGIT": {}, "INTER": {}, "ROB": [], "CAP": [], "SINGLE": [], "FIRMNEW": []}
pool = []
first_y0 = d.groupby("LCNS_NO").y0.min()
for lab, due in DUES.items():
    due["items"] = due.groupby("LCNS_NO").LCNS_NO.transform("size"); due["single"] = due["items"] == 1
    due["firm_new"] = due.y0 <= due.LCNS_NO.map(first_y0); due["snap"] = lab
    g1, g0 = due[due.fc], due[~due.fc]
    r = lambda s: s.mean()*100
    O["BT"].append(dict(lab=lab, n1=len(g1), e1=int(g1.y.sum()), r1=round(r(g1.y),1), n0=len(g0), e0=int(g0.y.sum()), r0=round(r(g0.y),1),
        rr=round(g1.y.mean()/g0.y.mean(),2), x1=round(r(g1.out),1), x0=round(r(g0.out),1), xrr=round(g1.out.mean()/g0.out.mean(),2)))
    for k, m in [("의무", due["의무"]), ("자율", ~due["의무"]), ("수도권", ~due["비수도권"]), ("비수도권", due["비수도권"])]:
        s = due[m]; O["STRAT"].append((lab, k, round(r(s[s.fc].y),1), round(r(s[~s.fc].y),1), round(s[s.fc].y.mean()/s[~s.fc].y.mean(),2)))
    X = np.c_[due.fc, due["비수도권"], due["김치절임"], due["의무"], np.log(due["items"])].astype(float)
    O["LOGIT"][lab], _, _ = logit_cl(X, due.y.astype(float).values, due.LCNS_NO.values, ["첫 연장","비수도권","김치·절임","의무 품목","업체 품목 수(로그)"])
    comp = due.groupby("LCNS_NO").agg(fc=("fc","max"), lost=("y","all"))
    O["ROB"].append((lab, round(g1.y.mean()/g0.y.mean(),2), round(g1.out.mean()/g0.out.mean(),2), round(g1.raw.mean()/g0.raw.mean(),2),
                     round(comp[comp.fc].lost.mean()/comp[~comp.fc].lost.mean(),2)))
    O["CAP"].append((lab, len(due), int(due.fc.sum()), round(due.fc.mean()*100,1), int(due.y.sum()), int(g1.y.sum()), round(g1.y.sum()/due.y.sum()*100,1), round((g1.y.sum()/due.y.sum())/due.fc.mean(),2)))
    O["SINGLE"].append((lab, round(r(g1[g1.single].y),1), round(r(g1[~g1.single].y),1), round(r(g0[g0.single].y),1), round(r(g0[~g0.single].y),1),
                        round(g1.single.mean()*100,1), round(g0.single.mean()*100,1)))
    O["FIRMNEW"].append((lab, round((~g1.firm_new).mean()*100,1), round(r(g1[g1.firm_new].y),1), round(r(g1[~g1.firm_new].y),1), round(r(g0.y),1)))
    pool.append(due)
P = pd.concat(pool)
snapd = pd.get_dummies(P.snap, drop_first=True).astype(float).values
base = [P.fc, P["비수도권"], P["김치절임"], P["의무"]]
X = np.c_[tuple(base) + (np.log(P["items"]),)].astype(float); X = np.c_[X, snapd]
O["LOGIT"]["통합"], _, _ = logit_cl(X, P.y.astype(float).values, P.LCNS_NO.values, ["첫 연장","비수도권","김치·절임","의무 품목","업체 품목 수(로그)"])
# 상호작용: 첫 연장 × 단일품목 (통합, 시점 고정효과, 업체 군집)
X = np.c_[P.fc, P.single, P.fc & P.single, P["비수도권"], P["김치절임"], P["의무"]].astype(float); X = np.c_[X, snapd]
res, b, V = logit_cl(X, P.y.astype(float).values, P.LCNS_NO.values, ["첫 연장","단일품목","첫 연장×단일품목","비수도권","김치·절임","의무 품목"])
c = np.zeros(len(b)); c[1] = 1; c[3] = 1; est = c@b; se = math.sqrt(c@V@c)
res["첫 연장(단일품목 업체 내)"] = dict(OR=round(math.exp(est),2), lo=round(math.exp(est-1.96*se),2), hi=round(math.exp(est+1.96*se),2), p=round(pval(est/se),4))
c = np.zeros(len(b)); c[2] = 1; c[3] = 1; est = c@b; se = math.sqrt(c@V@c)
res["단일품목(첫 연장 내)"] = dict(OR=round(math.exp(est),2), lo=round(math.exp(est-1.96*se),2), hi=round(math.exp(est+1.96*se),2), p=round(pval(est/se),4))
O["INTER"] = res
g1 = P[P.fc]; O["POOL_RATES"] = {"첫연장_단일": round(g1[g1.single].y.mean()*100,1), "첫연장_복수": round(g1[~g1.single].y.mean()*100,1),
    "2회차_단일": round(P[~P.fc & P.single].y.mean()*100,1), "2회차_복수": round(P[~P.fc & ~P.single].y.mean()*100,1),
    "첫연장": round(g1.y.mean()*100,2), "2회차": round(P[~P.fc].y.mean()*100,2), "n첫": len(g1), "n2": int((~P.fc).sum())}

# ---- (2) 운영 모수: 인증원 현행 API
full = open("4_분석/코드/eda_09_report_tables.py", encoding="utf-8").read()
exec(full[full.index("N_BUK = "):full.index("u[\"지원\"] = u.SITE_ADDR")])
A2 = A.copy(); A2["start"] = pd.to_datetime(A2.issuedate, errors="coerce"); A2["end"] = pd.to_datetime(A2.issueenddate, errors="coerce")
A2 = A2[A2.start.notna() & A2.end.notna()]
A2["y0"] = A2.appointno.str[:4].astype(int)
# 인증원 API의 issuedate는 최초 지정일 → (종료일-최초지정일)/3년으로 현재 주기 회차 산출
A2["cyc"] = np.maximum(1, np.round((A2.end - A2.start).dt.days/1095.75)).astype(int); A2["fc"] = A2.cyc == 1
O["회차분포"] = A2.cyc.value_counts().sort_index().to_dict()
O["회차_잔차_일"] = float(((A2.end - A2.start).dt.days - A2.cyc*1095.75).abs().quantile(0.95))
A2["items"] = A2.groupby("licenseno").licenseno.transform("size")
A2 = A2[A2.end > T]
u = A2.sort_values("fc", ascending=False).drop_duplicates(["licenseno","issueenddate"])
O["모수"] = {"인증원_인증": len(A2), "인증원_업체": A2.licenseno.nunique(), "업체x만료일": len(u)}
O["연장연도별"] = [(int(y), len(g), int(g.fc.sum()), round(g.fc.mean()*100,1)) for y, g in u.groupby(u.end.dt.year) if 2026 <= y <= 2029]
u["지원"] = (A2.loc[u.index, "sido"] + " " + A2.loc[u.index, "sgg"]).map(br)
w = u[(u.end.dt.year >= 2027) & (u.end.dt.year <= 2028)]
O["지원연도"] = [(b_, int((g.end.dt.year==2027).sum()), int(((g.end.dt.year==2027)&g.fc).sum()), int((g.end.dt.year==2028).sum()), int(((g.end.dt.year==2028)&g.fc).sum())) for b_, g in w.groupby("지원")]
mon = w.groupby(w.end.dt.strftime("%Y-%m")).size()
O["월별"] = {"min": int(mon.min()), "argmin": mon.idxmin(), "max": int(mon.max()), "argmax": mon.idxmax(), "top3": mon.sort_values(ascending=False).head(3).to_dict(),
            "11_12월비중": round(mon[[m for m in mon.index if m[-2:] in ("11","12")]].sum()/mon.sum()*100,1)}
f27 = w[(w.end.dt.year==2027) & w.fc]
O["첫연장품목27"] = A2.loc[f27.index].species.str.replace(r"\(.*\)", "", regex=True).value_counts().head(5).to_dict()
fw = w[w.fc]; O["단일품목_첫연장2728"] = (int((fw["items"]==1).sum()), round((fw["items"]==1).mean()*100,1))
SV = pd.read_csv("1_원천데이터/한국식품안전관리인증원_HACCP 인증업체 사회적약자기업 현황_20260818.csv", dtype=str, encoding="cp949")
fcert = A2[(A2.end.dt.year>=2027)&(A2.end.dt.year<=2028)&A2.fc]
O["사회적약자_첫연장2728"] = (int(SV.인증번호.isin(fcert.appointno).sum()), SV[SV.인증번호.isin(fcert.appointno)].업체명.nunique())
# I0580 판정과의 일치(첫 연장 여부)
m = A2.merge(d[["HACCP_APPN_NO","y0"]].drop_duplicates("HACCP_APPN_NO"), left_on="appointno", right_on="HACCP_APPN_NO", how="left", suffixes=("","_i"))
O["첫지정연도_일치"] = round((m.y0 == m.y0_i)[m.y0_i.notna()].mean()*100, 1)
iv = d[act].copy(); iv["fc_i"] = iv.y0 >= iv.start.dt.year
mm2 = A2.merge(iv[["HACCP_APPN_NO","fc_i"]].drop_duplicates("HACCP_APPN_NO"), left_on="appointno", right_on="HACCP_APPN_NO", how="inner")
O["첫연장판정_일치(인증원vsI0580)"] = (round((mm2.fc == mm2.fc_i).mean()*100,1), len(mm2))
# 차트 데이터
mm = w.groupby([w.end.dt.strftime("%Y-%m"), "fc"]).size().unstack(fill_value=0); mm.columns = ["2회차 이상","첫 연장"]
mm.to_csv("4_분석/결과/chart_data/c2_월별_연장물량_인증원.csv", encoding="utf-8-sig")
bb = w.groupby(["지원","fc"]).size().unstack(fill_value=0); bb.columns = ["2회차 이상","첫 연장"]; bb.to_csv("4_분석/결과/chart_data/c3_지원별_연장물량_인증원.csv", encoding="utf-8-sig")
bt = pd.DataFrame(O["BT"]); bt.to_csv("4_분석/결과/chart_data/c1_첫연장_반납취소율.csv", index=False, encoding="utf-8-sig")

# ---- (5) 설계 기반 최소탐지효과: 업체 단위 무작위(지원별 층화) 2군, 2027~2028 첫 연장
N = int(fw.shape[0]); n = N//2
def mde(p1, n, a=1.959964, z=0.841621):
    lo, hi = 0.0, p1
    for _ in range(60):
        mid = (lo+hi)/2; p2 = p1-mid; pb = (p1+p2)/2
        need = ((a*math.sqrt(2*pb*(1-pb))+z*math.sqrt(p1*(1-p1)+p2*(1-p2)))**2)/mid**2
        lo, hi = (mid, hi) if need > n else (lo, mid)
    return hi
O["검정력"] = {"N": N, "arm": n}
for lab, p1 in [("반납취소", g1.y.mean()), ("확장(보정 미갱신 포함)", P[P.fc].out.mean())]:
    d_ = mde(p1, n); O["검정력"][lab] = {"p1": round(p1*100,2), "MDE_pp": round(d_*100,2), "MDE_rel": round(d_/p1*100,1)}
gap = P[P.fc].y.mean() - P[~P.fc].y.mean(); O["격차_pp"] = round(gap*100,2)
O["NNT_half_main"] = round(1/(gap/2)); gapx = P[P.fc].out.mean() - P[~P.fc].out.mean(); O["NNT_half_ext"] = round(1/(gapx/2))
json.dump(O, open("4_분석/결과/revision_v4.json","w",encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(O, ensure_ascii=False, default=str))
