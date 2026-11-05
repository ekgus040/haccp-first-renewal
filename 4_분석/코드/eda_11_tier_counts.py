"""기획서 v3: 2027~2028 첫 연장 대상 중 단일품목 업체 규모, 수수료 데이터 행 수"""
import os, pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
src = open("4_분석/코드/eda_09_report_tables.py", encoding="utf-8").read()
pre = src.split("# ---- 연계 품질")[0]
exec(pre)
v = d[act].copy(); v["fc"] = v.y0 >= v.start.dt.year
v["items"] = v.groupby("LCNS_NO").LCNS_NO.transform("size")
u = v.sort_values("fc", ascending=False).drop_duplicates(["LCNS_NO","CRTFC_ENDDT"])
w = u[(u.end.dt.year>=2027)&(u.end.dt.year<=2028)]
f = w[w.fc]
print("첫연장", len(f), "단일품목", int((f["items"]==1).sum()), round((f["items"]==1).mean()*100,1))
c = pd.read_csv("1_원천데이터/04_인증원_HACCP_심사수수료정보.csv", encoding="utf-8-sig")
print("수수료행", len(c), c.auditKndNm.nunique())
