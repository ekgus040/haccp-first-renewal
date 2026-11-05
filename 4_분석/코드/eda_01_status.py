"""EDA 1차: I0580(HACCP 지정현황) 인증 상태 분류 + I1220 연계 적용률 (기준일 T)"""
import os
import pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
T = "20260920"
h = pd.read_csv("1_원천데이터/10_식품안전나라_I0580_HACCP지정현황.csv", dtype=str)
m = pd.read_csv("1_원천데이터/09_식품안전나라_I1220_식품제조가공업.csv", dtype=str)
closed = h.CLSBIZ_DVS_CD_NM != "정상"
ret = h.CRTFC_RETN_DT.notna()
valid = h.CRTFC_ENDDT >= T
h["상태"] = "기타"
h.loc[~closed & valid & ~ret, "상태"] = "A_정상_유효"
h.loc[~closed & ~valid & ~ret, "상태"] = "B_영업중_만료방치"
h.loc[~closed & ret, "상태"] = "C_영업중_반납(이탈)"
h.loc[closed & valid & ~ret, "상태"] = "D_폐업_유효인증잔존"
h.loc[closed & ret, "상태"] = "E_폐업_반납"
h["지정취소추정"] = (h.ASGN_CANCL_DT < h.CRTFC_ENDDT) & ~ret
h["폐업일<지정일"] = closed & (h.CLSBIZ_DT < h.HACCP_APPN_DT)
print(h["상태"].value_counts(), "\n지정취소추정", h["지정취소추정"].sum(), "\n폐업일<지정일", h["폐업일<지정일"].sum())

act = set(h.loc[h["상태"] == "A_정상_유효", "LCNS_NO"])
m["시도"] = m.LOCP_ADDR.str.split().str[0]
m["HACCP유효"] = m.LCNS_NO.isin(act)
cov = m.groupby("시도").agg(제조업체=("LCNS_NO", "size"), HACCP=("HACCP유효", "sum"))
cov["적용률"] = (cov.HACCP / cov.제조업체).round(3)
print(cov.sort_values("제조업체", ascending=False), "\n전국", round(m["HACCP유효"].mean(), 3))
h.to_csv("4_분석/결과/I0580_상태분류.csv", index=False, encoding="utf-8-sig")
cov.to_csv("4_분석/결과/시도별_HACCP적용률.csv", encoding="utf-8-sig")
