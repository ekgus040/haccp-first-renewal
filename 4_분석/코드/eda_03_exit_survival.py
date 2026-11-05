"""HACCP 인증 이탈(영업 중 반납·지정취소) 위험 요인 — 생존분석 (I0580 기준)"""
import os, pandas as pd, numpy as np
from lifelines import KaplanMeierFitter, CoxPHFitter
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
TODAY = pd.Timestamp("2026-09-26")
d = pd.read_csv("1_원천데이터/10_식품안전나라_I0580_HACCP지정현황.csv", dtype=str).fillna("")
d = d[d.INDUTY_CD_NM == "식품제조가공업"].copy()
dt = lambda s: pd.to_datetime(s, format="%Y%m%d", errors="coerce")
d["start"], d["end"], d["retn"], d["canc"], d["clos"] = map(dt, [d.HACCP_APPN_DT, d.CRTFC_ENDDT, d.CRTFC_RETN_DT, d.ASGN_CANCL_DT, d.CLSBIZ_DT])
n0 = len(d)
d = d[d.start.notna() & d.end.notna() & (d.end > d.start) & (d.start <= TODAY)]
d = d[~(d.clos.notna() & (d.clos < d.start))]           # 폐업일<지정일 오류 제외
print(f"분석 대상 {len(d):,} / {n0:,} (날짜 오류 제외)")

ev_retn = d.retn.notna() & (d.clos.isna() | (d.clos > d.retn)) & (d.retn <= TODAY)
ev_canc = d.retn.isna() & d.canc.notna() & (d.canc < d.end) & (d.canc <= TODAY)
d["event"] = (ev_retn | ev_canc).astype(int)
d["etype"] = np.where(ev_retn, "반납", np.where(ev_canc, "지정취소", ""))
cens = pd.concat([d.end, d.clos.fillna(pd.Timestamp.max), pd.Series(TODAY, index=d.index)], axis=1).min(axis=1)
d["tend"] = np.where(ev_retn, d.retn, np.where(ev_canc, d.canc, cens))
d["T"] = (pd.to_datetime(d.tend) - d.start).dt.days.clip(lower=1) / 365.25
print("이벤트:", d.etype.value_counts().to_dict(), f"/ 이탈률 {d.event.mean():.1%}")

# 공변량
MAND = ["어묵","어육","냉동","빙과","아이스","비가열","레토르트","배추김치","순대","과자","캔디","빵","떡","초콜릿",
        "음료","즉석섭취","국수","유탕면","특수용도","탄산","과ㆍ채","과채","두유","주스"]
d["의무품목"] = d.PRDLST_NM.apply(lambda s: int(any(k in s for k in MAND)))
cnt = d.groupby("LCNS_NO").HACCP_APPN_NO.transform("count")
d["품목수"] = pd.cut(cnt, [0,1,3,999], labels=["1개","2-3개","4개이상"])
d["갱신경험"] = (d.HACCP_APPN_NO.str[:4] < d.HACCP_APPN_DT.str[:4]).astype(int)
SIDO = {"서울":"수도권","경기":"수도권","인천":"수도권"}
d["시도"] = d.SITE_ADDR.str.split().str[0].str[:2]
d["권역"] = d["시도"].map(lambda s: SIDO.get(s, "비수도권"))
d["주요품목"] = d.PRDLST_NM.apply(lambda s: next((k for k in ["김치","과자","빵","떡","절임","액상차","소스","냉동","두부","음료","장류","면"] if k in s), "기타"))

# 1) 그룹별 3년 내 이탈 확률 (KM)
kmf = KaplanMeierFitter(); out = []
for col in ["의무품목","품목수","갱신경험","권역","주요품목"]:
    for g, sub in d.groupby(col, observed=True):
        if len(sub) < 200: continue
        kmf.fit(sub["T"], sub["event"])
        out.append((col, g, len(sub), int(sub.event.sum()), round(1 - kmf.predict(3.0), 3)))
km = pd.DataFrame(out, columns=["변수","그룹","N","이탈","3년내이탈확률"])
kmf.fit(d["T"], d["event"]); base3 = 1 - kmf.predict(3.0)
print(f"\n전체 3년 내 이탈 확률 {base3:.1%}"); print(km.to_string(index=False))

# 2) Cox 비례위험
X = pd.get_dummies(d[["품목수","주요품목","권역"]].astype(str), drop_first=False)
X = X.drop(columns=["품목수_4개이상","주요품목_기타","권역_수도권"])
X["의무품목"] = d["의무품목"]; X["갱신경험"] = d["갱신경험"]
X = X.astype(float); X["T"] = d["T"].values; X["E"] = d["event"].values
cph = CoxPHFitter(penalizer=0.01).fit(X, "T", "E")
s = cph.summary[["exp(coef)","exp(coef) lower 95%","exp(coef) upper 95%","p"]].round(3)
s.columns = ["HR","하한","상한","p"]; print("\nCox 위험비(HR)"); print(s.sort_values("HR", ascending=False).to_string())
print(f"\nC-index {cph.concordance_index_:.3f}")

# 3) 위험 점수 상위 10% 집중도 (현재 유효 인증 대상)
act = (d.event == 0) & (d.end >= TODAY) & d.clos.isna()
risk = cph.predict_partial_hazard(X.drop(columns=["T","E"]))
d["risk"] = risk
top = d.risk >= d.risk.quantile(0.9)
print(f"\n위험 상위10% 그룹 이탈률 {d[top].event.mean():.1%} vs 나머지 {d[~top].event.mean():.1%}")
print(f"현재 유효 인증 {act.sum():,}건 중 위험 상위10% 기준 이상 {(act & top).sum():,}건")
km.to_csv("4_분석/결과/이탈_KM_그룹별.csv", index=False, encoding="utf-8-sig")
s.to_csv("4_분석/결과/이탈_Cox_HR.csv", encoding="utf-8-sig")
