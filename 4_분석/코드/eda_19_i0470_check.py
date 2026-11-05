"""행정처분(I0470) 연계 가능성 점검(2026-10-21): 공개 범위·HACCP 업체 처분 건수"""
import os, pandas as pd, numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
R = "1_원천데이터/재수집_20261021/"
x = pd.read_csv(R+"13_식품안전나라_I0470_행정처분결과.csv", dtype=str).fillna("")
A = pd.read_csv(R+"02_인증원_식품제조가공_HACCP업체정보.csv", dtype=str).fillna("")
I = pd.read_csv(R+"10_식품안전나라_I0580_HACCP지정현황.csv", dtype=str).fillna("")
d = pd.to_datetime(x.DSPS_DCSNDT, format="%Y%m%d", errors="coerce")
f = x[x.INDUTY_CD_NM == "식품제조가공업"]
H = set(I[I.INDUTY_CD_NM == "식품제조가공업"].LCNS_NO)
A["fc"] = np.maximum(1, np.round((pd.to_datetime(A.issueenddate, errors="coerce") - pd.to_datetime(A.issuedate, errors="coerce")).dt.days/1095.75)) == 1
firm = A.groupby("licenseno").fc.any()
sub = f[f.DSPS_TYPECD_NM.isin(["영업정지", "품목제조정지"])]
cur = sub[sub.LCNS_NO.isin(firm.index)]
print("전체", len(x), "처분확정일", d.min().date(), "~", d.max().date())
print("식품제조가공업", len(f), "/ HACCP 이력 업체", int(f.LCNS_NO.isin(H).sum()))
print(pd.crosstab(f.DSPS_TYPECD_NM, f.LCNS_NO.isin(H)))
print("영업정지·품목제조정지", len(sub), "/ 현행 인증업체", len(cur), "(첫 주기 보유", int(cur.drop_duplicates("LCNS_NO").LCNS_NO.map(firm).sum()), ")")
