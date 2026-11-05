"""기획서 v3 보강 수치: 첫 연장 구성(기존 업체 신규 품목), 품목 수 층화, 사회적약자기업 연계, 시범 표본 규모"""
import os, re, json, math, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
src = open("4_분석/코드/eda_09_report_tables.py", encoding="utf-8").read()
src = src.split("R[\"사후검증\"] = BT")[0]  # 전처리·snapshot·루프 재사용
src = src.replace("for S in [pd.Timestamp", "DUES = {}\nfor S in [pd.Timestamp").replace("    comp = due.groupby", "    DUES[lab] = due.copy()\n    comp = due.groupby")
exec(src)
O = {}
first_y0 = d.groupby("LCNS_NO").y0.min()
for lab, due in DUES.items():
    due["firm_new"] = due.y0 <= due.LCNS_NO.map(first_y0)          # 업체의 최초 인증 연도 = 해당 인증 연도
    due["items"] = due.groupby("LCNS_NO").LCNS_NO.transform("size")
    g1 = due[due.fc]; g0 = due[~due.fc]
    r = lambda g: round(g.out.mean()*100, 1)
    O[lab] = {"첫연장_기존업체비중": round((~g1.firm_new).mean()*100, 1),
              "첫연장_신규업체_이탈률": r(g1[g1.firm_new]), "첫연장_기존업체_이탈률": r(g1[~g1.firm_new]), "2회차_이탈률": r(g0),
              "단일품목_첫/2회차": (r(g1[g1["items"]==1]), r(g0[g0["items"]==1])),
              "2품목이상_첫/2회차": (r(g1[g1["items"]>1]), r(g0[g0["items"]>1])),
              "첫연장_단일품목비중": round((g1["items"]==1).mean()*100,1), "2회차_단일품목비중": round((g0["items"]==1).mean()*100,1)}
# 사회적약자기업 × 2027~2028 첫 연장
SV = pd.read_csv("1_원천데이터/한국식품안전관리인증원_HACCP 인증업체 사회적약자기업 현황_20260818.csv", dtype=str, encoding="cp949")
v = d[act].copy(); v["fc"] = v.y0 >= v.start.dt.year
allv = v[(v.end.dt.year>=2027)&(v.end.dt.year<=2028)]
O["사회적약자"] = {"전체인증": len(SV), "업체": SV.업체명.nunique(), "유형": SV.사회적가치유형.value_counts().to_dict(),
    "27_28_연장도래_인증": int(SV.인증번호.isin(allv.HACCP_APPN_NO).sum()),
    "27_28_첫연장_인증": int(SV.인증번호.isin(v[(v.end.dt.year>=2027)&(v.end.dt.year<=2028)&v.fc].HACCP_APPN_NO).sum()),
    "27_28_첫연장_업체": SV[SV.인증번호.isin(v[(v.end.dt.year>=2027)&(v.end.dt.year<=2028)&v.fc].HACCP_APPN_NO)].업체명.nunique()}
# 시범 표본: 2회차 대비 격차 50% 해소 탐지
def n_per_arm(p1, p2, a=1.96, b=0.8416):
    pb=(p1+p2)/2; return math.ceil(((a*math.sqrt(2*pb*(1-pb))+b*math.sqrt(p1*(1-p1)+p2*(1-p2)))**2)/(p1-p2)**2)
def power(p1,p2,n):
    se=math.sqrt(p1*(1-p1)/n+p2*(1-p2)/n); z=abs(p1-p2)/se-1.96; return round(0.5*(1+math.erf(z/math.sqrt(2))),2)
P = {}
for p1,p0 in [(5.0,2.9),(7.4,4.0),(9.3,3.6)]:
    p1/=100; p0/=100; p2=p1-(p1-p0)/2
    P[f"{p1:.3f}->{p2:.3f}"] = {"arm_n": n_per_arm(p1,p2), "power_1564": power(p1,p2,1564), "NNT_half": round(1/(p1-p2),0), "NNT_full": round(1/(p1-p0),0)}
O["시범표본"] = P
json.dump(O, open("4_분석/결과/revision_support.json","w",encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(O, ensure_ascii=False, indent=1, default=str))
