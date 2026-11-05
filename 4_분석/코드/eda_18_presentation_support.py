"""발표 대비 보강 분석(2026-10-21)
(1) 직관 기준 vs 데이터 기준: 연장 도래 인증 중 각 기준으로 골랐을 때 대상 비중·포착률·선별 효율, 같은 물량(첫 연장 비중) 기준 기대 포착률, 시점 외 AUC
(2) 4번째 시점(2025.9) 사후 검증: 반납·취소 주 분석, 4개 시점 통합 OR(업체 군집)
(3) 기술지원 OR 민감도: E-value
실행: python eda_18_presentation_support.py [원천데이터 폴더(기본 1_원천데이터)] [기준일(기본 2026-09-26)]"""
import os, sys, re, json, math, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
DATA = sys.argv[1] if len(sys.argv) > 1 else "1_원천데이터"
TREF = sys.argv[2] if len(sys.argv) > 2 else "2026-09-26"
SNAPS = ["2022-09-26", "2023-09-26", "2024-09-26", "2025-09-26"]
src = open("4_분석/코드/eda_09_report_tables.py", encoding="utf-8").read().split("R[\"사후검증\"] = BT")[0]
src = (src.replace('pd.Timestamp("2026-09-26")', f'pd.Timestamp("{TREF}")')
          .replace('"1_원천데이터/10_', f'"{DATA}/10_').replace('"1_원천데이터/02_', f'"{DATA}/02_')
          .replace('for S in [pd.Timestamp("2022-09-26"), pd.Timestamp("2023-09-26"), pd.Timestamp("2024-09-26")]:',
                   'DUES = {}; XS = {}\nfor S in [pd.Timestamp(s) for s in SNAPS]:')
          .replace("    comp = due.groupby", "    DUES[lab] = due.copy(); XS[lab] = x.copy()\n    comp = due.groupby", 1))
exec(src)
O = {"설정": {"원천데이터": DATA, "기준일": TREF, "I0580_행": len(raw), "02_행": len(A),
             "관측종료_주의": "2025.9 시점은 관측 1년이 기준일 직전에 끝나 반납 기록 반영 지연 가능"}}
from math import erf, sqrt
pval = lambda z: 2*(1-0.5*(1+erf(abs(z)/sqrt(2))))
def logit_cl(X, y, g):
    Xm = np.c_[np.ones(len(X)), X]; b = np.zeros(Xm.shape[1])
    for _ in range(50):
        p = 1/(1+np.exp(-Xm@b)); H = Xm.T@(Xm*(p*(1-p))[:,None]); b += np.linalg.solve(H, Xm.T@(y-p))
    p = 1/(1+np.exp(-Xm@b)); Hi = np.linalg.inv(Xm.T@(Xm*(p*(1-p))[:,None]))
    S = pd.DataFrame(Xm*(y-p)[:,None]).groupby(np.asarray(g)).sum().values; G = len(S)
    return b, Hi@(S.T@S)@Hi*G/(G-1)
def orci(b, V, k): e, se = b[k], math.sqrt(V[k,k]); return dict(OR=round(math.exp(e),2), lo=round(math.exp(e-1.96*se),2), hi=round(math.exp(e+1.96*se),2), p=round(pval(e/se),4))
def auc(score, y):
    s = pd.Series(score).rank().values; y = np.asarray(y).astype(bool); n1, n0 = y.sum(), (~y).sum()
    return (s[y].sum() - n1*(n1+1)/2)/(n1*n0)

pool = []
for lab, due in DUES.items():
    due["items"] = due.groupby("LCNS_NO").LCNS_NO.transform("size"); due["단일품목"] = due["items"] == 1
    due["snap"] = lab; pool.append(due)
P = pd.concat(pool)
CRIT = [("첫 연장(데이터 기준)", "fc"), ("비수도권", "비수도권"), ("단일품목 업체", "단일품목"), ("의무 품목", "의무"), ("김치·절임", "김치절임")]
P["직관 조합(비수도권 또는 단일품목)"] = P["비수도권"] | P["단일품목"]; CRIT.append(("직관 조합(비수도권 또는 단일품목)", "직관 조합(비수도권 또는 단일품목)"))

# ---- (2) 시점별 사후 검증(주 분석: 반납·취소)
BT = []
for lab, g in P.groupby("snap"):
    g1, g0 = g[g.fc], g[~g.fc]
    BT.append(dict(lab=lab, n1=len(g1), e1=int(g1.y.sum()), r1=round(g1.y.mean()*100,2), n0=len(g0), e0=int(g0.y.sum()), r0=round(g0.y.mean()*100,2),
                   rr=round(g1.y.mean()/g0.y.mean(),2), 확장rr=round(g1.out.mean()/g0.out.mean(),2)))
O["시점별_사후검증"] = BT
for lab, g in P.groupby("snap"):
    X = np.c_[g.fc, g["비수도권"], g["김치절임"], g["의무"], np.log(g["items"])].astype(float)
    b, V = logit_cl(X, g.y.astype(float).values, g.LCNS_NO.values); O.setdefault("시점별_OR", {})[lab] = orci(b, V, 1)
for nm, Q in [("통합_3시점(2022~2024)", P[P.snap != "2025.9"]), ("통합_4시점(2022~2025)", P)]:
    sd_ = pd.get_dummies(Q.snap, drop_first=True).astype(float).values
    X = np.c_[Q.fc, Q["비수도권"], Q["김치절임"], Q["의무"], np.log(Q["items"]), sd_].astype(float)
    b, V = logit_cl(X, Q.y.astype(float).values, Q.LCNS_NO.values); O[nm] = orci(b, V, 1)

# ---- (1) 직관 기준 vs 데이터 기준(연장 도래 인증, 주 분석 반납·취소)
def crit_table(Q):
    rows = []; k = Q.fc.mean(); E = Q.y.sum()
    for nm, col in CRIT:
        m = Q[col].astype(bool); s = m.mean(); cap = Q[m].y.sum()/E
        # 같은 물량(k=첫 연장 비중)으로 골랐을 때 기대 포착률(기준 해당 → 우선, 나머지는 무작위)
        eq = cap*k/s if s >= k else cap + (k-s)/(1-s)*(1-cap)
        rows.append(dict(기준=nm, 대상비중=round(s*100,1), 포착률=round(cap*100,1), 선별효율=round(cap/s,2),
                         해당_이탈률=round(Q[m].y.mean()*100,2), 비해당_이탈률=round(Q[~m].y.mean()*100,2),
                         위험비=round(Q[m].y.mean()/Q[~m].y.mean(),2), 같은물량_포착률=round(eq*100,1)))
    return rows
O["기준비교_통합3시점"] = crit_table(P[P.snap != "2025.9"])
O["기준비교_시점별"] = {lab: crit_table(g) for lab, g in P.groupby("snap")}
O["기준비교_통합4시점"] = crit_table(P)
O["무작위_기준_같은물량_포착률"] = round(P[P.snap != "2025.9"].fc.mean()*100,1)
# 시점 외 검증 AUC: 앞 시점으로 학습 → 다음 시점 평가
FEAT = {"직관 변수(비수도권·단일품목·의무·김치절임)": ["비수도권","단일품목","의무","김치절임"],
        "첫 연장 단독": ["fc"], "직관 변수 + 첫 연장": ["비수도권","단일품목","의무","김치절임","fc"]}
AUC = []
labs = sorted(P.snap.unique())
for i in range(1, len(labs)):
    tr, te = P[P.snap.isin(labs[:i])], P[P.snap == labs[i]]
    row = {"학습": "+".join(labs[:i]), "평가": labs[i]}
    for nm, cols in FEAT.items():
        Xtr = tr[cols].astype(float).values; Xte = te[cols].astype(float).values
        b, _ = logit_cl(Xtr, tr.y.astype(float).values, tr.LCNS_NO.values)
        sc = np.c_[np.ones(len(Xte)), Xte]@b; row[nm] = round(auc(sc, te.y.values), 3)
    AUC.append(row)
O["시점외_AUC"] = AUC

# ---- (3) E-value(희귀 결과: OR≈RR)
def ev(rr): rr = 1/rr if rr < 1 else rr; return round(rr + math.sqrt(rr*(rr-1)), 2)
SS = json.load(open("4_분석/결과/smart_support.json", encoding="utf-8"))
t = SS["첫연장내_기술지원_조정OR"]
O["E_value"] = {"기술지원_첫연장_조정OR": dict(OR=t["OR"], lo=t["lo"], hi=t["hi"], E_점추정=ev(t["OR"]), E_신뢰구간=ev(t["hi"])),
                "첫연장_통합OR_3시점": dict(**O["통합_3시점(2022~2024)"], E_점추정=ev(O["통합_3시점(2022~2024)"]["OR"]), E_신뢰구간=ev(O["통합_3시점(2022~2024)"]["lo"])),
                "음성대조_2회차이상_기술지원": SS["상호작용_기술지원"]["기술지원(2회차 이상 내)"]}
out = "4_분석/결과/presentation_support" + ("" if DATA == "1_원천데이터" else "_" + os.path.basename(DATA)) + ".json"
json.dump(O, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(O, ensure_ascii=False, indent=1, default=str))
