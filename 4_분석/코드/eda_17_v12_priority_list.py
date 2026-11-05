"""기획서 v12: 2027~2028 첫 연장 우선관리 명단(업체×만료일) 전체 산출 + 본문 예시 표용 마스킹 샘플
정의는 eda_16_v9_final_export.py와 동일(회차=(종료일-최초지정일)/1095.75 반올림, 업체×만료일 단위)
산출: 4_분석/결과/v12_명단/첫연장_우선관리명단_2027-2028.csv, 명단_예시_마스킹.csv, 명단_요약.txt
"""
import os, pandas as pd, numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
T = pd.Timestamp("2026-09-26"); OUT = "4_분석/결과/v12_명단"; os.makedirs(OUT, exist_ok=True)
A = pd.read_csv("1_원천데이터/02_인증원_식품제조가공_HACCP업체정보.csv", dtype=str).fillna("")
A["start"] = pd.to_datetime(A.issuedate, errors="coerce"); A["end"] = pd.to_datetime(A.issueenddate, errors="coerce")
A = A[A.start.notna() & A.end.notna()].copy()
A["cyc"] = np.maximum(1, np.round((A.end - A.start).dt.days / 1095.75)).astype(int); A["fc"] = A.cyc == 1
A = A[A.end > T]
N_BUK = ("가평","고양","구리","남양주","동두천","양주","연천","의정부","파주","포천")
def br(a):
    p = a.split(); s = p[0][:2] if p else ""; g = p[1] if len(p) > 1 else ""
    if s in ("서울","강원"): return "서울"
    if s == "경기": return "서울" if g.startswith(N_BUK) else "경인"
    if s == "인천": return "경인"
    if s in ("대전","세종","충남","충북","충청"): return "대전"
    if s in ("광주","전남","전북","제주","전라"): return "광주"
    if s in ("대구","경북"): return "대구"
    if s in ("부산","울산","경남"): return "부산"
    if s == "경상": return "대구" if "북" in p[0] else "부산"
    return "기타"
A["지역지원"] = (A.sido + " " + A.sgg).map(br).map(lambda b: b + "지원" if b != "기타" else "주소 미분류")
SM = pd.read_csv("1_원천데이터/07_인증원_식품_스마트HACCP_인증업체.csv", dtype=str).fillna("")
SV = pd.read_csv("1_원천데이터/한국식품안전관리인증원_HACCP 인증업체 사회적약자기업 현황_20260818.csv", dtype=str, encoding="cp949").fillna("")
sm_lic = set(SM.licenseno); sv_no = set(SV.인증번호)
A["사회적약자"] = A.appointno.isin(sv_no)
g = A.groupby(["licenseno", "issueenddate"])
L = g.agg(지역지원=("지역지원","first"), 업체명=("company","first"), 시도=("sido","first"), 시군구=("sgg","first"),
          첫연장=("fc","any"), 품목수=("species","size"),
          첫주기_품목=("species", lambda s: ", ".join(sorted(set(s[A.loc[s.index,"fc"]])))),
          인증번호=("appointno", lambda s: ", ".join(sorted(s[A.loc[s.index,"fc"]]))),
          최초지정일=("start","min"), 만료일=("end","first"), 사회적약자=("사회적약자","any")).reset_index()
L = L[L.첫연장 & L.만료일.dt.year.between(2027, 2028)].copy()
L["스마트HACCP등록"] = L.licenseno.isin(sm_lic)
L["접점2_T12"] = (L.만료일 - pd.DateOffset(months=12)).dt.strftime("%Y-%m")
L["T6"] = (L.만료일 - pd.DateOffset(months=6)).dt.strftime("%Y-%m")
L["안내유형"] = np.where(L.만료일 < pd.Timestamp("2028-01-01"), "단축형(남은 기간 맞춤)", "T-12 선제지원")
L["지원구분"] = np.select([L.사회적약자, L.스마트HACCP등록], ["집중 지원 후보(사회적약자)", "기본 안내(스마트HACCP 우대 안내)"], "기본 안내(내부평가 하위 시 집중)")
L = L.sort_values(["만료일", "지역지원", "licenseno"])
cols = ["지역지원","licenseno","업체명","시도","시군구","인증번호","첫주기_품목","품목수","최초지정일","만료일","접점2_T12","T6","안내유형","스마트HACCP등록","사회적약자","지원구분"]
L[cols].assign(최초지정일=L.최초지정일.dt.strftime("%Y-%m-%d"), 만료일=L.만료일.dt.strftime("%Y-%m-%d")).to_csv(f"{OUT}/첫연장_우선관리명단_2027-2028.csv", index=False, encoding="utf-8-sig")
# 요약
s = [f"명단 행수(업체×만료일): {len(L)}", f"업체 수: {L.licenseno.nunique()}",
     f"단축형: {(L.안내유형.str.startswith('단축')).sum()}, T-12 선제: {(L.안내유형=='T-12 선제지원').sum()}",
     f"스마트HACCP 등록: {L.스마트HACCP등록.sum()}, 사회적약자: {L.사회적약자.sum()}",
     "지역지원별: " + L.지역지원.value_counts().to_dict().__repr__()]
open(f"{OUT}/명단_요약.txt","w",encoding="utf-8").write("\n".join(s)); print("\n".join(s))
# 예시: 2027년 하반기(T-12 선제 대상) 첫 만료 건, 지역지원별 1건
P = L[(L.안내유형=="T-12 선제지원") & (L.지역지원!="주소 미분류")]
pick=[]; used=set()
for cond in [P.사회적약자, P.스마트HACCP등록]:
    c = P[cond & ~P.지역지원.isin(used)].head(1); pick.append(c); used |= set(c.지역지원)
for b in ["경인지원","대전지원","서울지원","광주지원","부산지원","대구지원"]:
    if b not in used: pick.append(P[P.지역지원==b].head(1)); used.add(b)
E = pd.concat(pick).sort_values(["만료일","지역지원"])
def mask_no(x):
    n = x.split(", "); return n[0][:7] + "****" + (f" 외 {len(n)-1}" if len(n) > 1 else "")
def mask_nm(x):
    for k in ["주식회사","(주)","㈜","농업회사법인","영농조합법인","유한회사"]: x = x.replace(k, "")
    x = x.strip(); return (x[0] + "○○") if x else "○○"
E2 = pd.DataFrame({"지역지원": E.지역지원, "업체": E.업체명.map(mask_nm), "인증번호": E.인증번호.map(mask_no),
    "첫 주기 품목": E.첫주기_품목, "최초 지정": E.최초지정일.dt.strftime("%Y.%m"), "만료": E.만료일.dt.strftime("%Y.%m"),
    "T-12 안내": E.접점2_T12.str.replace("-", "."), "T-6 안내": E.T6.str.replace("-", "."),
    "스마트HACCP": np.where(E.스마트HACCP등록, "등록", "미등록"), "구분": E.지원구분})
E2.to_csv(f"{OUT}/명단_예시_마스킹.csv", index=False, encoding="utf-8-sig"); print(E2.to_string())
