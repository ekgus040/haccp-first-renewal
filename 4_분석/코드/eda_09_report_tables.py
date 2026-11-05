"""기획서 본문 근거 표 일괄 산출 → 4_분석/결과/report_tables.json"""
import os, re, json, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
T = pd.Timestamp("2026-09-26"); Y = pd.Timedelta(days=365.25); R = {}
raw = pd.read_csv("1_원천데이터/10_식품안전나라_I0580_HACCP지정현황.csv", dtype=str).fillna("")
F = pd.read_csv("1_원천데이터/09_식품안전나라_I1220_식품제조가공업.csv", dtype=str).fillna("")
A = pd.read_csv("1_원천데이터/02_인증원_식품제조가공_HACCP업체정보.csv", dtype=str).fillna("")
M = pd.read_csv("1_원천데이터/01_식품의약품안전처_HACCP_지정현황.csv", dtype=str).fillna("")
f = lambda s: pd.to_datetime(s, format="%Y%m%d", errors="coerce")

# ---- 전처리 단계
steps = [("I0580 원자료", len(raw))]
d = raw[raw.INDUTY_CD_NM == "식품제조가공업"].copy(); steps.append(("식품제조가공업 한정", len(d)))
for a,b in [("start","HACCP_APPN_DT"),("end","CRTFC_ENDDT"),("retn","CRTFC_RETN_DT"),("canc","ASGN_CANCL_DT"),("clos","CLSBIZ_DT")]: d[a]=f(d[b])
d = d[d.start.notna() & d.end.notna()]; steps.append(("날짜 결측 제외", len(d)))
d = d[(d.end > d.start) & (d.start <= T)]; steps.append(("종료일≤지정일·미래 지정 제외", len(d)))
d = d[~(d.clos.notna() & (d.clos < d.start))]; steps.append(("폐업일<지정일 제외", len(d)))
R["전처리"] = steps

ev_r = d.retn.notna() & (d.clos.isna() | (d.clos > d.retn)) & (d.retn <= T)
ev_c = d.retn.isna() & d.canc.notna() & (d.canc < d.end) & (d.canc <= T)
d["ev"] = ev_r | ev_c; d["et"] = pd.to_datetime(np.where(d.ev, d.retn.fillna(d.canc), pd.NaT))
d["y0"] = d.HACCP_APPN_NO.str[:4].astype(int)
d["비수도권"] = ~d.SITE_ADDR.str[:2].isin(["서울","경기","인천"]); d["김치절임"] = d.PRDLST_NM.str.contains("김치|절임")
MAND = "어묵|어육|냉동|빙과|아이스|비가열|레토르트|배추김치|순대|과자|캔디|빵|떡|초콜릿|음료|즉석섭취|국수|유탕면|특수용도|탄산|과ㆍ채|과채|두유|주스"
d["의무"] = d.PRDLST_NM.str.contains(MAND)

# ---- 인증 상태 분류(현재)
act = (~d.ev) & (d.end >= T) & d.clos.isna()
lapse = (~d.ev) & (d.end < T) & d.clos.isna()
closed = (~d.ev) & d.clos.notna()
R["상태분류"] = [("유효(영업 중)", int(act.sum())), ("영업 중 반납", int(ev_r.sum())), ("지정취소 추정", int(ev_c.sum())),
                ("폐업", int(closed.sum())), ("만료 후 미갱신(영업 중)", int(lapse.sum()))]
# ---- 연도별 이탈(반납·취소) 건수
R["연도별이탈"] = {int(k): int(v) for k, v in d[d.ev].et.dt.year.value_counts().sort_index().items() if 2017 <= k <= 2025}
# ---- 인증번호 연도별 신규 지정(현재 남은 기록 기준)
R["지정연도별"] = {int(k): int(v) for k, v in d.y0.value_counts().sort_index().items() if 2010 <= k <= 2026}

# ---- 연계 품질
L02 = set(A.licenseno); N02 = set(A.appointno)
R["연계"] = {"02_업체": len(L02), "02_인증": len(A), "02→I0580_인허가": round(len(L02 & set(raw.LCNS_NO))/len(L02)*100,1),
             "02→I1220_인허가": round(len(L02 & set(F.LCNS_NO))/len(L02)*100,1), "02→I0580_인증번호": round(len(N02 & set(raw.HACCP_APPN_NO))/len(N02)*100,1),
             "I0580→I1220_인허가": round(len(set(d.LCNS_NO) & set(F.LCNS_NO))/d.LCNS_NO.nunique()*100,1),
             "01→I0580_인증번호": round(len(set(M.HACCP_APPN_NO) & set(raw.HACCP_APPN_NO))/M.HACCP_APPN_NO.nunique()*100,1),
             "I1220_업체": F.LCNS_NO.nunique(), "I0580_행": len(raw), "01_행": len(M)}
R["02_issuedate_일치"] = None

# ---- 사후 검증
def snapshot(S):
    x = d[d.y0 <= S.year].copy()
    k = np.ceil(((x.start - S).dt.days/1095.75).clip(lower=0)); x["k"] = k
    x["cs"] = x.start - pd.to_timedelta(k*1095.75, unit="D")
    x = x[(x.cs <= S) & (x.cs.dt.year >= x.y0) & ~(x.ev & (x.et <= S)) & ~(x.clos.notna() & (x.clos <= S + Y))]
    x = x[(x.k > 0) | (x.end > S)]
    x["y"] = x.ev & (x.et > S) & (x.et <= S + Y)
    x["lapse"] = (x.k == 0) & ~x.ev & (x.end > S) & (x.end <= S + Y) & x.clos.isna()
    return x
def norm(s): return re.sub(r"\(주\)|주식회사|농업회사법인|영농조합법인|\(유\)|유한회사|\s|\(|\)", "", s)
d["nm"] = d.BSSH_NM.map(norm)
def logit(X, y):
    Xm = np.c_[np.ones(len(X)), X]; b = np.zeros(Xm.shape[1])
    for _ in range(30):
        p = 1/(1+np.exp(-Xm@b)); H = Xm.T@(Xm*(p*(1-p))[:,None]); b += np.linalg.solve(H, Xm.T@(y-p))
    se = np.sqrt(np.diag(np.linalg.inv(H))); z = b/se
    from math import erf, sqrt
    pv = [2*(1-0.5*(1+erf(abs(t)/sqrt(2)))) for t in z]
    return b[1:], se[1:], pv[1:]
BT, ST, LG, RB, CAP, FAC = [], [], [], [], [], []
for S in [pd.Timestamp("2022-09-26"), pd.Timestamp("2023-09-26"), pd.Timestamp("2024-09-26")]:
    lab = f"{S.year}.9"
    x = snapshot(S)
    due = x[(x.cs + 3*Y > S) & (x.cs + 3*Y <= S + Y)].copy(); due["fc"] = due.y0 >= due.cs.dt.year
    later = d[d.start > S][["nm","LCNS_NO"]]
    succ = due.apply(lambda r: r.lapse and ((later.nm == r.nm) & (later.LCNS_NO != r.LCNS_NO)).any(), axis=1)
    alive = due.HACCP_APPN_NO.isin(N02) | due.LCNS_NO.isin(L02)
    due["lc"] = due.lapse & ~alive & ~succ; due["out"] = due.y | due.lc; due["raw"] = due.y | due.lapse
    R.setdefault("미갱신보정", []).append((lab, int(due.lapse.sum()), int((due.lapse & alive).sum()), int((due.lapse & ~alive & succ).sum()), int(due.lc.sum())))
    g1, g0 = due[due.fc], due[~due.fc]
    for nm, g in [("첫 연장", g1), ("2회차 이상", g0)]:
        BT.append((lab, nm, len(g), int(g.y.sum()), int(g.lc.sum()), int(g.out.sum()), round(g.out.mean()*100, 1)))
    hr = g1.out.mean()/g0.out.mean()
    # 층화
    for k, m in [("의무 품목", due["의무"]), ("자율 품목", ~due["의무"]), ("수도권", ~due["비수도권"]), ("비수도권", due["비수도권"])]:
        g = due[m]; ST.append((lab, k, round(g[g.fc].out.mean()*100,1), round(g[~g.fc].out.mean()*100,1), round(g[g.fc].out.mean()/g[~g.fc].out.mean(),2)))
    # 로지스틱
    X = np.c_[due.fc, due["비수도권"], due["김치절임"], due["의무"], np.log(due.groupby("LCNS_NO").LCNS_NO.transform("size"))].astype(float)
    b, se, pv = logit(X, due.out.astype(float).values)
    for nm, bb, s_, p_ in zip(["첫 연장","비수도권","김치·절임","의무 품목","업체 품목 수(로그)"], b, se, pv):
        LG.append((lab, nm, round(np.exp(bb),2), round(np.exp(bb-1.96*s_),2), round(np.exp(bb+1.96*s_),2), round(p_,4)))
    # 강건성
    comp = due.groupby("LCNS_NO").agg(fc=("fc","max"), lost=("out","all"))
    RB.append((lab, round(g1.y.mean()/g0.y.mean(),2), round(g1.raw.mean()/g0.raw.mean(),2), round(hr,2), round(comp[comp.fc].lost.mean()/comp[~comp.fc].lost.mean(),2)))
    # 포착 효율
    CAP.append((lab, len(due), int(due.fc.sum()), round(due.fc.mean()*100,1), int(due.out.sum()), int(g1.out.sum()), round(g1.out.sum()/due.out.sum()*100,1),
                round((g1.out.sum()/due.out.sum())/due.fc.mean(),2)))
    # 기각 가설(모든 유효 인증 대상, 주기 중 이탈)
    x["n_items"] = x.groupby("LCNS_NO").LCNS_NO.transform("size"); x["cy"] = (S - x.cs).dt.days/365.25
    for k, m in [("인증 주기 2~3년차", x.cy >= 1.5), ("비수도권", x["비수도권"]), ("단일품목 업체", x.n_items == 1), ("의무 품목", x["의무"]), ("김치·절임", x["김치절임"]), ("첫 인증 주기", x.y0 >= x.cs.dt.year)]:
        FAC.append((lab, k, round(x[m].y.mean()/x[~m].y.mean(), 2)))
R["사후검증"] = BT; R["층화"] = ST; R["로지스틱"] = LG; R["강건성"] = RB; R["포착"] = CAP; R["요인"] = FAC

# ---- 향후 연장 물량(I0580 유효·영업 중, 업체×만료일)
v = d[act].copy(); v["fc"] = v.y0 >= v.start.dt.year
u = v.sort_values("fc", ascending=False).drop_duplicates(["LCNS_NO","CRTFC_ENDDT"])
R["연장연도별"] = [(int(y), int(len(g)), int(g.fc.sum()), round(g.fc.mean()*100,1)) for y, g in u.groupby(u.end.dt.year) if 2026 <= y <= 2029]
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
u["지원"] = u.SITE_ADDR.map(br); w = u[(u.end.dt.year >= 2027) & (u.end.dt.year <= 2028)]
R["지원연도"] = [(b, int(((g.end.dt.year==2027)).sum()), int(((g.end.dt.year==2027)&g.fc).sum()), int(((g.end.dt.year==2028)).sum()), int(((g.end.dt.year==2028)&g.fc).sum())) for b, g in w.groupby("지원") if b != "기타"]
mon = w.groupby(w.end.dt.strftime("%Y-%m")).size()
R["월별"] = {"min": int(mon.min()), "max": int(mon.max()), "mean": round(mon.mean(),1), "argmax": mon.idxmax(), "argmin": mon.idxmin(), "평균초과월수": int((mon > mon.mean()).sum()), "상위3월": mon.sort_values(ascending=False).head(3).to_dict()}
fc27 = v[(v.end.dt.year == 2027) & v.fc]
R["첫연장품목"] = fc27.PRDLST_NM.str.replace(r"\(.*\)", "", regex=True).value_counts().head(8).to_dict()
json.dump(R, open("4_분석/결과/report_tables.json","w",encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(R, ensure_ascii=False, default=str)[:6000])

# ---- 차트용 내보내기
mm = w.groupby([w.end.dt.strftime("%Y-%m"), "fc"]).size().unstack(fill_value=0); mm.columns = ["2회차 이상","첫 연장"]; mm.index.name = "ym"
mm.to_csv("4_분석/결과/chart_data/c2_월별_연장물량.csv", encoding="utf-8-sig")
bb = w[w.지원 != "기타"].groupby(["지원","fc"]).size().unstack(fill_value=0); bb.columns = ["2회차 이상","첫 연장"]; bb["합계"] = bb.sum(axis=1); bb["첫연장비중"] = (bb["첫 연장"]/bb["합계"]*100).round(1)
bb.to_csv("4_분석/결과/chart_data/c3_지원별_연장물량.csv", encoding="utf-8-sig")
pd.Series(R["지정연도별"]).rename_axis("연도").rename("건수").to_csv("4_분석/결과/chart_data/c5_지정연도별.csv", encoding="utf-8-sig")
print("exported", mm.sum().to_dict(), bb.합계.sum())
