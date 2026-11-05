"""I0580 반납일 기록이 2026.2에서 멈춤 → 4개 시점을 같은 5개월 관측창(기준일+5개월)으로 비교
실행: python eda_18d_equal_window.py [원천데이터 폴더] [기준일]"""
import os, sys, math, json, pandas as pd, numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
code = open("4_분석/코드/eda_18_presentation_support.py", encoding="utf-8").read().split("# ---- (2)")[0]
exec(code)
R = {"반납일_최근월": str(d.retn.max().date()), "취소포함_이벤트_최근": str(d[d.ev].et.max().date())}
rows = []; pool = []
for lab, g in P.groupby("snap"):
    S = pd.Timestamp(lab.replace(".9", "-09-26")); E5 = S + pd.DateOffset(months=5)
    g = g.copy(); g["y5"] = g.ev & (g.et > S) & (g.et <= E5); pool.append(g)
    X = np.c_[g.fc, g["비수도권"], g["김치절임"], g["의무"], np.log(g["items"])].astype(float)
    b, V = logit_cl(X, g.y5.astype(float).values, g.LCNS_NO.values); o = orci(b, V, 1)
    r1, r0 = g[g.fc].y5.mean(), g[~g.fc].y5.mean()
    rows.append(dict(시점=lab, 첫연장=f"{int(g[g.fc].y5.sum())}/{int(g.fc.sum())} ({r1*100:.2f}%)", 회차2이상=f"{int(g[~g.fc].y5.sum())}/{int((~g.fc).sum())} ({r0*100:.2f}%)", RR=round(r1/r0,2), **o))
R["5개월창_시점별"] = rows
Q = pd.concat(pool)
for nm, Z in [("통합_3시점_5개월", Q[Q.snap != "2025.9"]), ("통합_4시점_5개월", Q)]:
    sd_ = pd.get_dummies(Z.snap, drop_first=True).astype(float).values
    X = np.c_[Z.fc, Z["비수도권"], Z["김치절임"], Z["의무"], np.log(Z["items"]), sd_].astype(float)
    b, V = logit_cl(X, Z.y5.astype(float).values, Z.LCNS_NO.values); R[nm] = orci(b, V, 1)
# 12개월 주 분석 재현(새 데이터)
Z = P[P.snap != "2025.9"]; sd_ = pd.get_dummies(Z.snap, drop_first=True).astype(float).values
X = np.c_[Z.fc, Z["비수도권"], Z["김치절임"], Z["의무"], np.log(Z["items"]), sd_].astype(float)
b, V = logit_cl(X, Z.y.astype(float).values, Z.LCNS_NO.values); R["재현_3시점_12개월"] = orci(b, V, 1)
out = "4_분석/결과/equal_window" + ("" if DATA == "1_원천데이터" else "_" + os.path.basename(DATA)) + ".json"
json.dump(R, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(R, ensure_ascii=False, indent=1))
