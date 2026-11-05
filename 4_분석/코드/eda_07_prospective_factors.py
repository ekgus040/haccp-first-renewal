"""사후 검증: 과거 시점 기준 요인별 다음 1년 이탈 위험비"""
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

d["n_items"]=d.groupby("LCNS_NO").LCNS_NO.transform("size")
res=[]
for S in [pd.Timestamp("2022-09-26"),pd.Timestamp("2023-09-26"),pd.Timestamp("2024-09-26")]:
    x=snapshot(S); x["y2"]=x.y|x.lapse
    fac={"비수도권":x["비수도권"],"김치·절임":x["김치절임"],"첫 주기":x.y0>=x.cs.dt.year,
         "단일품목 업체":x.n_items==1,"의무품목":x["의무"],"주기 1.5~3년차":x.cy>=1.5,"주기 2.5~3년차":x.cy>=2.5}
    for k,m in fac.items():
        for out in ["y","y2"]:
            p=x[m][out].mean(); q=x[~m][out].mean()
            res.append((S.year,k,out,round(m.mean(),2),round(p*100,2),round(q*100,2),round(p/q,2),int(m.sum())))
r=pd.DataFrame(res,columns=["기준연도","요인","결과","해당비중","해당%","비해당%","위험비","n"])
r["결과"]=r["결과"].map({"y":"주기중 이탈","y2":"이탈+미갱신"})
print(r.pivot_table(index=["요인","결과"],columns="기준연도",values="위험비").round(2).to_string())
print(); print(r[r.기준연도==2024].to_string(index=False))
r.to_csv("4_분석/결과/사후검증_요인별_위험비.csv",index=False,encoding="utf-8-sig")
