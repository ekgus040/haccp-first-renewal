"""검증: 정의·집계 착시 점검"""
import os, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
T = pd.Timestamp("2026-09-26")
d = pd.read_csv("1_원천데이터/10_식품안전나라_I0580_HACCP지정현황.csv", dtype=str).fillna("")
d = d[d.INDUTY_CD_NM == "식품제조가공업"].copy()
f = lambda s: pd.to_datetime(s, format="%Y%m%d", errors="coerce")
for a,b in [("start","HACCP_APPN_DT"),("end","CRTFC_ENDDT"),("retn","CRTFC_RETN_DT"),("canc","ASGN_CANCL_DT"),("clos","CLSBIZ_DT")]: d[a]=f(d[b])
d = d[d.start.notna() & d.end.notna() & (d.end > d.start) & ~(d.clos.notna() & (d.clos < d.start))]
mid = (d.retn.notna() & (d.clos.isna() | (d.clos > d.retn))) | (d.retn.isna() & (d.canc < d.end) & (d.canc <= T))
act = (~mid) & (d.end >= T) & d.clos.isna()
lapse = (~mid) & (d.end < T - pd.Timedelta(days=180)) & d.clos.isna()   # 만료 6개월 경과·미갱신·영업중
print("[A] 이탈 경로(인증 단위): 주기 중 반납·취소", int(mid.sum()), "/ 만료 후 미갱신(6개월+)", int(lapse.sum()))

d["mid"], d["act"], d["lapse"] = mid, act, lapse
g = d.groupby("LCNS_NO").agg(n=("mid","size"), m=("mid","sum"), a=("act","sum"), l=("lapse","sum"),
                             closed=("clos", lambda s: s.notna().all()), sido=("SITE_ADDR", lambda s: s.iloc[0][:2]),
                             kim=("PRDLST_NM", lambda s: s.str.contains("김치|절임").any()),
                             lastend=("end","max"))
op = g[~g.closed].copy()
op["full_mid"] = (op.a == 0) & (op.m > 0)
op["full_any"] = (op.a == 0) & ((op.m > 0) | (op.l > 0))
op["full_lapse_only"] = (op.a == 0) & (op.m == 0) & (op.l > 0)
print(f"[A] 영업 중 업체 {len(op):,}: 완전이탈(반납·취소) {op.full_mid.sum()} / 만료미갱신만 {op.full_lapse_only.sum()} / 합계 {op.full_any.sum()} ({op.full_any.mean():.1%})")

# [B] 요인 효과가 정의를 바꿔도 유지되는가 (full_any 기준)
op["권역"] = np.where(op.sido.isin(["서울","경기","인천"]),"수도권","비수도권")
op["품목수"] = pd.cut(op.n,[0,1,3,999],labels=["1개","2-3개","4+"])
for c in ["권역","kim","품목수"]:
    print("[B]", c, op.groupby(c, observed=True)[["full_mid","full_any"]].mean().round(3).to_dict("index"))
# 권역 효과: 김치·절임 제외해도?
nk = op[~op.kim]; print("[B] 김치·절임 제외 권역:", nk.groupby("권역")[["full_mid","full_any"]].mean().round(3).to_dict("index"))
# 품목수 기계적 효과 점검: 업체의 '첫 품목'만 보고 반납 여부 (품목 단위 확률)
d["n_items"] = d.groupby("LCNS_NO").LCNS_NO.transform("size")
d2 = d[d.clos.isna()]
print("[B] 품목 단위 주기중 이탈률(영업중):", d2.groupby(pd.cut(d2.n_items,[0,1,3,999],labels=["1개","2-3개","4+"]), observed=True).mid.mean().round(3).to_dict())

# [C] 첫 주기 집중 — 노출 보정: 최초 지정일 추정(3년 주기 역산) 후 인증 연차별 연간 위험률
d["y0"] = d.HACCP_APPN_NO.str[:4].astype(int)
k = ((d.start.dt.year - d.y0) / 3).round().clip(lower=0)
d["orig"] = d.start - pd.to_timedelta(k*1095.75, unit="D")
d["exit_t"] = np.where(mid, d.retn.fillna(d.canc), pd.NaT)
cens = pd.concat([d.end, d.clos.fillna(pd.Timestamp.max), pd.Series(T,index=d.index)],axis=1).min(axis=1)
d["stop"] = pd.to_datetime(np.where(mid, d.exit_t, cens))
d["dur"] = (d.stop - d.orig).dt.days/365.25
rows=[]
for lo,hi in [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,9),(9,30)]:
    atrisk = d[d.dur > lo]
    expo = (atrisk.dur.clip(upper=hi) - lo).clip(lower=0).sum()
    ev = ((d.dur > lo) & (d.dur <= hi) & mid).sum()
    rows.append((f"{lo}-{hi}년", len(atrisk), int(ev), round(ev/expo*100,2)))
print("[C] 인증 연차별 연간 이탈률(%/인증·년):"); print(pd.DataFrame(rows,columns=["연차","위험집단","이탈","연간이탈률%"]).to_string(index=False))
print("[C] 주의: 1998~2016 지정분 중 과거 반납 기록 보존 여부 불명(좌측 절단 가능)")

# [D] 완전 이탈 추세 — 모수 보정
yrs = {}
full_ids = op[op.full_mid].index
e = d[d.LCNS_NO.isin(full_ids) & mid].groupby("LCNS_NO").exit_t.max()
cnt = pd.to_datetime(e).dt.year.value_counts().sort_index()
base = {2021:9251,2022:10356,2023:10741,2024:11130,2025:11319}  # 연차보고서 식품 인증업소 수
print("[D] 완전 이탈 업체/인증업소(%):", {y: f"{cnt.get(y,0)} / {b} = {cnt.get(y,0)/b*100:.2f}%" for y,b in base.items()})
print("[D] 반납일 연도별 기록 수(전체):", d.retn.dt.year.value_counts().sort_index().loc[2012:].to_dict())

# [E] 연장심사: 인증 건 vs 실제 심사 단위(업체×만료일)
a = pd.read_csv("1_원천데이터/02_인증원_식품제조가공_HACCP업체정보.csv", dtype=str)
a["y"]=a.issueenddate.str[:4]
u = a.drop_duplicates(["licenseno","issueenddate"])
print("[E] 연도별 인증건 vs 업체×만료일 묶음:", {y:(int((a.y==y).sum()), int((u.y==y).sum())) for y in ["2026","2027","2028","2029"]})
m = u[u.y.isin(["2027","2028"])].issueenddate.str[:7].value_counts()
print("[E] 묶음 기준 2027~28 월별 최소/최대/평균:", m.min(), m.max(), round(m.mean()), m.idxmax())
