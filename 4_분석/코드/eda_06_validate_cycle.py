"""핵심 주장 검증: 인증 주기 2~3년차(연장심사 직전) 이탈 위험 상승"""
import os, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
T = pd.Timestamp("2026-09-26"); Y = pd.Timedelta(days=365.25)
d = pd.read_csv("1_원천데이터/10_식품안전나라_I0580_HACCP지정현황.csv", dtype=str).fillna("")
d = d[d.INDUTY_CD_NM == "식품제조가공업"].copy()
f = lambda s: pd.to_datetime(s, format="%Y%m%d", errors="coerce")
for a,b in [("start","HACCP_APPN_DT"),("end","CRTFC_ENDDT"),("retn","CRTFC_RETN_DT"),("canc","ASGN_CANCL_DT"),("clos","CLSBIZ_DT")]: d[a]=f(d[b])
d = d[d.start.notna() & d.end.notna() & (d.end > d.start) & ~(d.clos.notna() & (d.clos < d.start))].copy()
ev = (d.retn.notna() & (d.clos.isna() | (d.clos > d.retn))) | (d.retn.isna() & (d.canc < d.end) & (d.canc <= T))
d["ev"] = ev; d["et"] = pd.to_datetime(np.where(ev, d.retn.fillna(d.canc), pd.NaT))
cens = pd.concat([d.end, d.clos.fillna(pd.Timestamp.max), pd.Series(T,index=d.index)],axis=1).min(axis=1)
d["stop"] = pd.to_datetime(np.where(ev, d.et, cens))
d["y0"] = d.HACCP_APPN_NO.str[:4].astype(int)
d["first"] = d.y0 >= d.start.dt.year
d["비수도권"] = ~d.SITE_ADDR.str[:2].isin(["서울","경기","인천"])
d["김치절임"] = d.PRDLST_NM.str.contains("김치|절임")
MAND = "어묵|어육|냉동|빙과|아이스|비가열|레토르트|배추김치|순대|과자|캔디|빵|떡|초콜릿|음료|즉석섭취|국수|유탕면|특수용도|탄산|과ㆍ채|과채|두유|주스"
d["의무"] = d.PRDLST_NM.str.contains(MAND)

def hazard(sub, cuts=((0,.5),(.5,1),(1,1.5),(1.5,2),(2,2.5),(2.5,3))):
    """현재 주기 시작 기준 반년 구간별 연간 이탈률(%)"""
    dur = (sub.stop - sub.start).dt.days/365.25; out=[]
    for lo,hi in cuts:
        expo = (dur.clip(upper=hi)-lo).clip(lower=0).sum()
        e = ((dur>lo)&(dur<=hi)&sub.ev).sum()
        out.append(round(e/expo*100,2) if expo>0 else np.nan)
    return out
cols = ["0-0.5","0.5-1","1-1.5","1.5-2","2-2.5","2.5-3"]
res = {"전체": hazard(d), "첫 주기": hazard(d[d["first"]]), "갱신 주기": hazard(d[~d["first"]])}
print("[1] 현재 주기 내 반년 구간별 연간 이탈률(%) — 추정 없이 관측 구간만"); print(pd.DataFrame(res, index=cols).T.to_string())

# [2] 반납 시점: 만료까지 남은 기간
r = d[d.ev & d.retn.notna()]; left = (r.end - r.retn).dt.days
print("\n[2] 반납 시점 = 만료 몇 개월 전:", pd.cut(left/30.44,[-1,1,3,6,12,24,36,99]).value_counts().sort_index().to_dict())
print("    만료 1개월 이내 반납 비율:", round((left<=31).mean(),3), "/ 중앙값(일):", int(left.median()))

# [3] 시기 효과 통제: 주기 시작연도 코호트별, 달력연도별
print("\n[3a] 주기 시작연도 코호트별 패턴")
for lo,hi in [(2014,2016),(2017,2019),(2020,2021),(2022,2023)]:
    s = d[(d.start.dt.year>=lo)&(d.start.dt.year<=hi)]
    print(f"   {lo}-{hi} (n={len(s):,}):", hazard(s))
print("[3b] 이탈 발생 달력연도별 — 1.5~3년차 비중 vs 노출 비중")
for yr in range(2018, 2026):
    a, b = pd.Timestamp(f"{yr}-01-01"), pd.Timestamp(f"{yr+1}-01-01")
    s = d[(d.start < b) & (d.stop > a)]
    lo_ = pd.concat([s.start, pd.Series(a,index=s.index)],axis=1).max(axis=1); hi_ = pd.concat([s.stop, pd.Series(b,index=s.index)],axis=1).min(axis=1)
    # 노출 중 1.5~3년차 비중
    w0 = s.start + 1.5*Y; w1 = s.start + 3*Y
    inwin = (pd.concat([hi_, w1],axis=1).min(axis=1) - pd.concat([lo_, w0],axis=1).max(axis=1)).dt.days.clip(lower=0)
    tot = (hi_-lo_).dt.days.clip(lower=0)
    e = s[s.ev & (s.et>=a) & (s.et<b)]; ew = ((e.et - e.start).dt.days/365.25 >= 1.5).mean()
    print(f"   {yr}: 이탈 {len(e):4d}건 중 1.5~3년차 {ew:.0%} / 노출 중 1.5~3년차 {inwin.sum()/tot.sum():.0%}")
print("[3c] 의무·자율 품목별:", {k: hazard(d[d["의무"]==k]) for k in [True, False]})

# [4] 사후 검증: 과거 시점 S에 경보 규칙 적용 → 이후 1년 이탈
def snapshot(S):
    x = d[(d.y0 <= S.year)].copy()
    k = np.ceil(((x.start - S).dt.days/1095.75).clip(lower=0))
    x["cs"] = x.start - pd.to_timedelta(k*1095.75, unit="D")          # S 시점의 주기 시작
    x = x[(x.cs <= S) & (x.cs.dt.year >= x.y0 - 0)]
    x = x[~(x.ev & (x.et <= S)) & ~(x.clos.notna() & (x.clos <= S + Y))]  # S 이전 이탈·창 내 폐업 제외
    x = x[(k > 0) | (x.end > S)]
    x["cy"] = (S - x.cs).dt.days/365.25
    x["y"] = x.ev & (x.et > S) & (x.et <= S + Y)
    x["lapse"] = (k == 0) & ~x.ev & (x.end > S) & (x.end <= S + Y) & x.clos.isna()   # 미갱신
    return x
print("\n[4] 사후 검증(과거 시점에서 경보 → 다음 1년 이탈)")
for S in [pd.Timestamp("2023-09-26"), pd.Timestamp("2024-09-26")]:
    x = snapshot(S); base = x.y.mean()
    rules = {"A: 주기 1.5~3년차": x.cy >= 1.5,
             "B: A + (비수도권 또는 김치·절임)": (x.cy >= 1.5) & (x["비수도권"] | x["김치절임"]),
             "C: A + 비수도권 + 김치·절임": (x.cy >= 1.5) & x["비수도권"] & x["김치절임"]}
    print(f" 기준 {S.date()}: 대상 {len(x):,}건, 1년 내 이탈 {int(x.y.sum())}건({base:.2%}), 미갱신 {int(x.lapse.sum())}건")
    for nm, m in rules.items():
        p = x[m].y.mean(); q = x[~m].y.mean()
        print(f"   {nm}: 경보 {m.mean():.0%} → 이탈률 {p:.2%} vs 비경보 {q:.2%} (위험비 {p/q:.2f}배), 전체 이탈 중 포착 {x[m].y.sum()/x.y.sum():.0%}")
