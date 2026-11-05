"""v6 보강: (A) 첫 주기 이탈의 주기 내 시점 분포 (B) 이탈 유형: 품목 정리형 vs 업체 전체 이탈 (C) 설계효과(ICC) (D) 지원별 월평균 첫 연장 건수"""
import os, re, json, math, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
src = open("4_분석/코드/eda_09_report_tables.py", encoding="utf-8").read().split("R[\"사후검증\"] = BT")[0]
src = src.replace("for S in [pd.Timestamp", "DUES = {}\nfor S in [pd.Timestamp").replace("    comp = due.groupby", "    DUES[lab] = due.copy()\n    comp = due.groupby")
exec(src)
O = {}
# (A) 주기 내 이탈 시점: 이탈 시점의 현재 주기 시작(start) 기준 경과연수
e = d[d.ev & (d.et.dt.year >= 2017)].copy()
e["fcyc"] = e.start.dt.year == e.y0
e["yr"] = ((e.et - e.start).dt.days / 365.25).clip(lower=0)
e["bucket"] = pd.cut(e.yr, [0,1,2,3.1], right=False, labels=["1년차","2년차","3년차"])
for k, g in [("첫 주기", e[e.fcyc]), ("2주기 이상", e[~e.fcyc])]:
    vc = g.bucket.value_counts(normalize=True).reindex(["1년차","2년차","3년차"]).round(3)*100
    O.setdefault("주기내시점", {})[k] = dict(n=len(g), **vc.round(1).to_dict())
# 첫 주기 1년차 이탈 중 '정기 조사·평가 이전(인증 후 6개월 내)' 비중
g = e[e.fcyc]; O["첫주기_6개월내"] = round((g.yr < 0.5).mean()*100,1); O["첫주기_12개월내"] = round((g.yr < 1).mean()*100,1)
# (B) 이탈 유형: 이탈 시점에 같은 업체(인허가번호)의 다른 유효 인증이 남아 있는지
alive = d[["LCNS_NO","HACCP_APPN_NO","start","end","ev","et","clos"]]
def keeps_other(r):
    o = alive[(alive.LCNS_NO == r.LCNS_NO) & (alive.HACCP_APPN_NO != r.HACCP_APPN_NO)]
    o = o[(o.start <= r.et) & ((~o.ev) | (o.et > r.et)) & ((o.clos.isna()) | (o.clos > r.et))]
    return len(o) > 0
TY = []
for lab, due in DUES.items():
    ex = due[due.y].copy(); ex["keep"] = ex.apply(keeps_other, axis=1)
    for grp, g in [("첫 연장", ex[ex.fc]), ("2회차 이상", ex[~ex.fc])]:
        TY.append((lab, grp, len(g), int(g.keep.sum()), round(g.keep.mean()*100,1) if len(g) else None))
O["이탈유형"] = TY
P = pd.concat([x.assign(snap=k_) for k_, x in DUES.items()])
for grp, g in [("첫 연장", P[P.fc & P.y]), ("2회차 이상", P[~P.fc & P.y])]:
    kk = g.apply(keeps_other, axis=1); O.setdefault("이탈유형_통합", {})[grp] = (len(g), int(kk.sum()), round(kk.mean()*100,1))
# 업체 전체 이탈 기준 첫 연장 위험(업체×기준시점 단위, 도래 인증 전부 이탈 AND 다른 유효 인증도 없음)
# (C) 설계효과: 2027~2028 첫 연장 대상, 업체 단위 배정·업체×만료일 단위 분석
full = open("4_분석/코드/eda_12_revision_v4.py", encoding="utf-8").read()
exec(full[full.index("A2 = A.copy()"):full.index("O[\"모수\"]")])
u = A2.sort_values("fc", ascending=False).drop_duplicates(["licenseno","issueenddate"])
w = u[(u.end.dt.year >= 2027) & (u.end.dt.year <= 2028) & u.fc]
m = w.groupby("licenseno").size(); mbar = (m**2).sum()/m.sum()
F1 = P[P.fc]; grp = F1.groupby(["snap","LCNS_NO"]).y
# ANOVA ICC
k = grp.size(); ybar = F1.y.mean(); N = len(F1); G = len(k)
msb = ((grp.mean()-ybar)**2 * k).sum()/(G-1); msw = ((F1.y - grp.transform("mean"))**2).sum()/(N-G)
k0 = (N - (k**2).sum()/N)/(G-1); icc = max(0,(msb-msw)/(msb+(k0-1)*msw))
O["설계효과"] = dict(대상=len(w), 업체=int(m.size), 가중평균군집크기=round(mbar,2), ICC=round(icc,3), DEFF=round(1+(mbar-1)*icc,2))
# (D) 지원별 월평균 첫 연장(2027~2028)
w = w.copy(); w["지원"] = (A2.loc[w.index,"sido"]+" "+A2.loc[w.index,"sgg"])
O["첫연장_월평균_전체"] = round(len(w)/24,1)
json.dump(O, open("4_분석/결과/weakness_support.json","w",encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(O, ensure_ascii=False, indent=1, default=str))
