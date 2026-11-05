"""기준별 같은 물량 포착률 차이(첫 연장 − 직관 기준)의 업체 단위 부트스트랩 95% 구간(3시점 통합, 1,000회)"""
import os, sys, pandas as pd, numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
code = open("4_분석/코드/eda_18_presentation_support.py", encoding="utf-8").read().split("# ---- (2)")[0]
exec(code)
Q = P[P.snap != "2025.9"].copy()
cols = {"fc":"첫 연장","비수도권":"비수도권","단일품목":"단일품목","의무":"의무 품목","김치절임":"김치·절임","직관 조합(비수도권 또는 단일품목)":"직관 조합"}
agg = {"N": Q.groupby("LCNS_NO").size(), "E": Q.groupby("LCNS_NO").y.sum()}
for c in cols:
    m = Q[c].astype(bool); agg["N_"+c] = Q[m].groupby("LCNS_NO").size(); agg["E_"+c] = Q[m].groupby("LCNS_NO").y.sum()
F = pd.DataFrame(agg).fillna(0); A_ = F.values; names = list(F.columns); ix = {n:i for i,n in enumerate(names)}
def stat(S):
    N, E = S[ix["N"]], S[ix["E"]]; k = S[ix["N_fc"]]/N; out = {}
    for c in cols:
        s = S[ix["N_"+c]]/N; cap = S[ix["E_"+c]]/E
        out[c] = cap*k/s if s >= k else cap + (k-s)/(1-s)*(1-cap)
    return out
base = stat(A_.sum(0)); rng = np.random.default_rng(42); B = []
for _ in range(1000):
    S = A_[rng.integers(0, len(A_), len(A_))].sum(0); B.append(stat(S))
B = pd.DataFrame(B)
print("업체 수", len(F), "이벤트", int(A_[:, ix["E"]].sum()))
for c, nm in cols.items():
    d = B["fc"] - B[c]
    print(f"{nm}: 포착 {base[c]*100:.1f}%  [{B[c].quantile(.025)*100:.1f}, {B[c].quantile(.975)*100:.1f}]  첫연장과 차이 {(base['fc']-base[c])*100:.1f}%p [{d.quantile(.025)*100:.1f}, {d.quantile(.975)*100:.1f}]")
