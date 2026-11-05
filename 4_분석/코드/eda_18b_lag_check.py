"""2025.9 시점 반영 지연 점검: 이벤트 관측창을 9개월로 줄여 4개 시점을 같은 조건에서 비교"""
import os, sys, pandas as pd, numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
sys.argv = sys.argv[:1] + sys.argv[1:]
code = open("4_분석/코드/eda_18_presentation_support.py", encoding="utf-8").read().split("# ---- (2)")[0]
exec(code)
for lab, g in P.groupby("snap"):
    S = pd.Timestamp(lab.replace(".9", "-09-26"))
    for months in (6, 9, 12):
        y = g.ev & (g.et > S) & (g.et <= S + pd.DateOffset(months=months))
        r1, r0 = y[g.fc].mean(), y[~g.fc].mean()
        print(lab, f"{months}개월", f"첫연장 {r1*100:.2f}%", f"2회차 {r0*100:.2f}%", f"RR {r1/r0:.2f}")
    # 2회차 이상 이탈 시점 분포(만료 전후)
