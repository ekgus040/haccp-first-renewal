"""첫 인증주기 전체의 연간 반납·취소 규모(두 접점 적용 범위)"""
import os, pandas as pd, numpy as np, json, warnings; warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
src = open("4_분석/코드/eda_09_report_tables.py", encoding="utf-8").read().split("# ---- 사후 검증")[0]
exec(src)
e = d[d.ev].copy(); e["fcyc"] = e.start.dt.year == e.y0; e["yr"] = e.et.dt.year
tab = e[(e.yr >= 2020) & (e.yr <= 2025)].groupby(["yr","fcyc"]).size().unstack(fill_value=0)
print(tab)
g = e[e.fcyc]; g["cy"] = (e.et - e.start).dt.days/365.25
print("첫주기 2·3년차 비중(2023~2025):", round(((g.cy>=1)&(g.cy<3.1)&(g.yr.between(2023,2025))).sum()/ (g.yr.between(2023,2025)&(g.cy<3.1)).sum()*100,1))
json.dump({int(k):{str(c):int(v) for c,v in r.items()} for k,r in tab.iterrows()}, open("4_분석/결과/first_cycle_scale.json","w"), ensure_ascii=False)
