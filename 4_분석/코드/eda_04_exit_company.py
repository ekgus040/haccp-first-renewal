"""반납·취소가 '품목 정리'인지 '업체 완전 이탈'인지 구분 + 업체 단위 요인"""
import os, pandas as pd, numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
TODAY = pd.Timestamp("2026-09-26")
d = pd.read_csv("1_원천데이터/10_식품안전나라_I0580_HACCP지정현황.csv", dtype=str).fillna("")
d = d[d.INDUTY_CD_NM == "식품제조가공업"].copy()
dt = lambda s: pd.to_datetime(s, format="%Y%m%d", errors="coerce")
for a,b in [("start","HACCP_APPN_DT"),("end","CRTFC_ENDDT"),("retn","CRTFC_RETN_DT"),("canc","ASGN_CANCL_DT"),("clos","CLSBIZ_DT")]: d[a]=dt(d[b])
d = d[d.start.notna() & d.end.notna() & (d.end > d.start) & ~(d.clos.notna() & (d.clos < d.start))]
d["exit"] = (d.retn.notna() & (d.clos.isna() | (d.clos > d.retn))) | (d.retn.isna() & (d.canc < d.end) & (d.canc <= TODAY))
d["active"] = (~d.exit) & (d.end >= TODAY) & d.clos.isna()
d["first"] = d.HACCP_APPN_NO.str[:4] >= d.HACCP_APPN_DT.str[:4]

g = d.groupby("LCNS_NO").agg(n=("exit","size"), n_exit=("exit","sum"), n_act=("active","sum"),
        closed=("clos", lambda s: s.notna().all()), first_year=("HACCP_APPN_NO", lambda s: s.str[:4].min()),
        sido=("SITE_ADDR", lambda s: s.iloc[0].split()[0][:2] if s.iloc[0] else ""),
        kimchi=("PRDLST_NM", lambda s: s.str.contains("김치|절임").any()))
ex = g[g.n_exit > 0]
full = ex[(ex.n_act == 0) & (~ex.closed)]
part = ex[ex.n_act > 0]
print(f"업체 {len(g):,} / 반납·취소 경험 업체 {len(ex):,}")
print(f"  품목 일부 정리(다른 유효 인증 보유) {len(part):,} ({len(part)/len(ex):.0%})")
print(f"  완전 이탈(영업 중, 유효 인증 0) {len(full):,} ({len(full)/len(ex):.0%})")
print(f"  폐업 동반 {len(ex)-len(part)-len(full):,}")

# 완전 이탈률: 업체 규모(품목 수)별, 김치·절임, 권역, 최초 지정 코호트
g["full_exit"] = g.index.isin(full.index)
g["품목수"] = pd.cut(g.n, [0,1,3,999], labels=["1개","2-3개","4개이상"])
g["권역"] = np.where(g.sido.isin(["서울","경기","인천"]), "수도권", "비수도권")
g2 = g[~g.closed]   # 영업 중 업체만
print(f"\n영업 중 업체 {len(g2):,}, 완전 이탈률 {g2.full_exit.mean():.1%}")
for c in ["품목수","kimchi","권역"]:
    print(g2.groupby(c, observed=True).full_exit.agg(["size","mean"]).round(3).to_string()); print()
g2["코호트"] = pd.cut(g2.first_year.astype(int), [0,2014,2019,2022,2026], labels=["~2014","2015-19","2020-22","2023-26"])
print(g2.groupby("코호트", observed=True).full_exit.agg(["size","mean"]).round(3).to_string())

# 이탈 시점: 인증 주기 내 경과 연수, 첫 주기 여부
e = d[d.exit].copy()
e["tt"] = ((e.retn.fillna(e.canc)) - e.start).dt.days / 365.25
print("\n이탈 시점(주기 시작 후 년) 분포:", e.tt.quantile([.25,.5,.75]).round(2).to_dict())
print("첫 인증 주기 중 이탈 비율:", round(e["first"].mean(),3), "/ 전체 인증 중 첫 주기 비율:", round(d["first"].mean(),3))
lcns_full = set(full.index)
ef = e[e.LCNS_NO.isin(lcns_full)]
print("완전 이탈 업체의 이탈 중 첫 주기 비율:", round(ef["first"].mean(),3))
print("연도별 완전 이탈 업체 수:", ef.groupby("LCNS_NO").apply(lambda x: (x.retn.fillna(x.canc)).max().year).value_counts().sort_index().to_dict())
