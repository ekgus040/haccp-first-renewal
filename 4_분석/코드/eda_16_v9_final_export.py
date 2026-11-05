"""기획서 v9 최종 수치 동기화: 연장심사 물량(연도별·월별·지원별) 재산출 → 4_분석/결과/v9_최종/
+ v9 본문 수치 assert(PASS/FAIL) + 그림1·3·4 재생성 → 5_기획서/그림/v9/

정의(v9, eda_12_revision_v4.py 운영 모수와 동일)
- 모수: 인증원 「식품 제조가공 HACCP업체 정보」(02) 현행 인증, 종료일 > 2026-09-26
- 회차: (종료일 - 최초지정일)/1095.75일 반올림(최소 1) → 1이면 첫 연장
- 단위: 업체(licenseno) × 만료일(issueenddate), 하나라도 첫 주기면 첫 연장
- 지원: 인증원 연차보고서 2025 관할(경기 북부 10개 시군→서울, 강원→서울, 제주→광주), 미분류는 '기타'
- 그림1: I0580 식품제조가공업, 지정번호 앞 4자리 연도별 건수(eda_09 전처리와 동일)
"""
import os, sys, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")
T = pd.Timestamp("2026-09-26")
OUT = "4_분석/결과/v9_최종"; FIG = "5_기획서/그림/v9"
os.makedirs(OUT, exist_ok=True); os.makedirs(FIG, exist_ok=True)
RES = []
def check(name, got, exp):
    ok = got == exp; RES.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: got={got} v9={exp}")

# ---------------- 운영 모수(02)
A = pd.read_csv("1_원천데이터/02_인증원_식품제조가공_HACCP업체정보.csv", dtype=str).fillna("")
A["start"] = pd.to_datetime(A.issuedate, errors="coerce"); A["end"] = pd.to_datetime(A.issueenddate, errors="coerce")
A = A[A.start.notna() & A.end.notna()].copy()
A["cyc"] = np.maximum(1, np.round((A.end - A.start).dt.days / 1095.75)).astype(int); A["fc"] = A.cyc == 1
A = A[A.end > T]
u = A.sort_values("fc", ascending=False).drop_duplicates(["licenseno", "issueenddate"]).copy()

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
u["지원"] = (u.sido + " " + u.sgg).map(br)
u["연"] = u.end.dt.year; u["월"] = u.end.dt.strftime("%Y-%m")

# 표2 연도별
t2 = u[u.연.between(2026, 2029)].groupby("연").agg(연장심사=("fc", "size"), 첫연장=("fc", "sum"))
t2["첫연장비중(%)"] = (t2.첫연장 / t2.연장심사 * 100).round(1)
t2.index = ["2026(9.26 이후)" if y == 2026 else str(y) for y in t2.index]; t2.index.name = "만료연도"
t2.to_csv(f"{OUT}/연장심사_연도별.csv", encoding="utf-8-sig")

# 월별 2026-2029
m = u[u.연.between(2026, 2029)].groupby("월").agg(연장=("fc", "size"), 첫연장=("fc", "sum"))
m["2회차이상"] = m.연장 - m.첫연장; m["첫연장비중(%)"] = (m.첫연장 / m.연장 * 100).round(1)
m.index.name = "만료연월"; m.to_csv(f"{OUT}/연장심사_월별_2026-2029.csv", encoding="utf-8-sig")

# 표15 지원별 2027-2028
w = u[u.연.between(2027, 2028)]
rows = []
for b in ["경인","대전","서울","광주","부산","대구","기타"]:
    g = w[w.지원 == b]
    r = dict(지원=b + ("지원" if b != "기타" else "(주소 미분류)"),
             연장_2027=int((g.연 == 2027).sum()), 첫연장_2027=int(((g.연 == 2027) & g.fc).sum()),
             연장_2028=int((g.연 == 2028).sum()), 첫연장_2028=int(((g.연 == 2028) & g.fc).sum()))
    r["연장_2년"] = r["연장_2027"] + r["연장_2028"]; r["첫연장_2년"] = r["첫연장_2027"] + r["첫연장_2028"]
    r["2년_첫연장비중(%)"] = round(r["첫연장_2년"] / r["연장_2년"] * 100, 1) if r["연장_2년"] else None
    rows.append(r)
t15 = pd.DataFrame(rows); t15.to_csv(f"{OUT}/연장심사_지원별_2027-2028.csv", index=False, encoding="utf-8-sig")

# 지원×월
bm = u[u.연.between(2026, 2029)].groupby(["지원", "월"]).agg(연장=("fc", "size"), 첫연장=("fc", "sum")).reset_index()
bm["지원"] = bm.지원.map(lambda b: b + "지원" if b != "기타" else "기타(주소 미분류)")
bm.rename(columns={"월": "만료연월"}).to_csv(f"{OUT}/연장심사_지원별월별.csv", index=False, encoding="utf-8-sig")

# ---------------- 그림1 데이터(I0580)
raw = pd.read_csv("1_원천데이터/10_식품안전나라_I0580_HACCP지정현황.csv", dtype=str).fillna("")
f = lambda s: pd.to_datetime(s, format="%Y%m%d", errors="coerce")
d = raw[raw.INDUTY_CD_NM == "식품제조가공업"].copy()
d["start"], d["end"], d["clos"] = f(d.HACCP_APPN_DT), f(d.CRTFC_ENDDT), f(d.CLSBIZ_DT)
d = d[d.start.notna() & d.end.notna()]; d = d[(d.end > d.start) & (d.start <= T)]
d = d[~(d.clos.notna() & (d.clos < d.start))]
yc = d.HACCP_APPN_NO.str[:4].astype(int).value_counts().sort_index(); yc = yc[(yc.index >= 2010) & (yc.index <= 2025)]
yc.rename_axis("지정연도").rename("인증건수").to_csv(f"{OUT}/그림1_지정연도별_인증건수.csv", encoding="utf-8-sig")

# ---------------- v9 대조
print("== 표2")
V2 = {"2026(9.26 이후)": (892, 300, 33.6), "2027": (4072, 1564, 38.4), "2028": (4443, 1631, 36.7), "2029": (4009, 1163, 29.0)}
for k, v in V2.items(): check(f"표2 {k}", (int(t2.loc[k, "연장심사"]), int(t2.loc[k, "첫연장"]), float(t2.loc[k, "첫연장비중(%)"])), v)
check("2027-28 연장 합계", int(len(w)), 8515); check("2027-28 첫연장 합계", int(w.fc.sum()), 3195)
check("2027-28 첫연장 비중(%)", round(w.fc.mean() * 100, 1), 37.5)
print("== 월별(그림3)")
mw = m.loc["2027-01":"2028-12"]
check("월 최소", (int(mw.연장.min()), mw.연장.idxmin()), (228, "2027-02"))
check("월 최대", (int(mw.연장.max()), mw.연장.idxmax()), (624, "2027-11"))
check("월평균 연장(그림3 점선)", round(mw.연장.mean()), 355)
check("첫연장 월평균", round(mw.첫연장.mean()), 133)
check("첫연장 지원당 월평균(6개 지원)", round(mw.첫연장.mean() / 6), 22)
print("== 표15/그림4")
V15 = {"경인지원": (1018, 403, 1164, 422, 37.8), "대전지원": (755, 311, 844, 327, 39.9), "서울지원": (739, 267, 797, 321, 38.3),
       "광주지원": (674, 250, 742, 247, 35.1), "부산지원": (463, 192, 493, 178, 38.7), "대구지원": (422, 141, 400, 134, 33.5)}
T15 = t15.set_index("지원")
for k, v in V15.items():
    r_ = T15.loc[k]; check(f"표15 {k}", tuple(int(r_[c]) for c in ["연장_2027","첫연장_2027","연장_2028","첫연장_2028"]) + (float(r_["2년_첫연장비중(%)"]),), v)
check("경인 2년 최대", (T15.drop(index="기타(주소 미분류)").연장_2년.idxmax(), int(T15.loc["경인지원", "연장_2년"])), ("경인지원", 2182))
check("대구 2년 최소", (T15.drop(index="기타(주소 미분류)").연장_2년.idxmin(), int(T15.loc["대구지원", "연장_2년"])), ("대구지원", 822))
check("주소 미분류 제외 건수", int(T15.loc["기타(주소 미분류)", "연장_2년"]), 4)
print("== 사회적약자(첫 연장 2027-28)")
SV = pd.read_csv("1_원천데이터/한국식품안전관리인증원_HACCP 인증업체 사회적약자기업 현황_20260818.csv", dtype=str, encoding="cp949")
fcert = A[A.end.dt.year.between(2027, 2028) & A.fc]
hit = SV[SV.인증번호.isin(fcert.appointno)]
check("사회적약자 건수/업체수", (len(hit), hit.업체명.nunique()), (26, 17))
print("== 그림1(I0580)")
check("그림1 라벨 2016/2020/2021/2025", tuple(int(yc[y]) for y in (2016, 2020, 2021, 2025)), (1794, 3372, 3987, 2410))
sh = T15.drop(index="기타(주소 미분류)")["2년_첫연장비중(%)"]
print(f"[INFO] 지원별 2년 첫연장 비중 범위 {sh.min()}~{sh.max()}% (본문 137문단 '34~40%'; 그림4 정수 라벨은 대구 33%)")
print(f"[INFO] 주소 미분류 인증: {w[w.지원=='기타'][['licenseno','sido','sgg','issueenddate']].values.tolist()}")

# ---------------- 그림
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fam = next((n for n in ["Noto Sans CJK KR", "NanumGothic", "Noto Sans CJK JP", "Malgun Gothic"] if n in {x.name for x in fm.fontManager.ttflist}), None)
plt.rcParams.update({"font.family": fam, "axes.unicode_minus": False, "font.size": 11})
BLUE, GRAY, TXT, GRID = "#2B78D6", "#B9B6AE", "#555555", "#E3E3E3"
def style(ax, grid_axis="y"):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color("#888888")
    ax.grid(axis=grid_axis, color=GRID, lw=0.8); ax.set_axisbelow(True); ax.tick_params(colors=TXT)

# 그림1
fig, ax = plt.subplots(figsize=(7.6, 3.4))
hl = {2020, 2021}
ax.bar([str(y)[2:] for y in yc.index], yc.values, width=0.72, color=[BLUE if y in hl else GRAY for y in yc.index])
for i, (y, v) in enumerate(yc.items()):
    if y in (2016, 2020, 2021, 2025): ax.text(i, v + 25, f"{v:,}", ha="center", va="bottom", fontsize=10.5)
i21 = list(yc.index).index(2021)
ax.text(i21 - 0.5, yc[2021] + 260, "2020.12 의무적용 기한", ha="center", va="bottom", color=BLUE, fontsize=10.5)
ax.set_ylabel("인증 건수(품목 단위)", color=TXT); ax.set_ylim(0, 4500); ax.set_yticks(range(0, 4001, 1000)); style(ax)
ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=4)
fig.tight_layout(); fig.savefig(f"{FIG}/그림1_연도별_인증건수.png", dpi=200); plt.close(fig)

# 그림3
fig, ax = plt.subplots(figsize=(8.4, 3.5))
x = np.arange(len(mw)); f1 = mw.첫연장.values; f2 = mw["2회차이상"].values
ax.bar(x, f1, width=0.74, color=BLUE, label="첫 연장", edgecolor="white", lw=0.6)
ax.bar(x, f2, width=0.74, bottom=f1, color=GRAY, label="2회차 이상", edgecolor="white", lw=0.6)
avg = mw.연장.mean(); ax.axhline(avg, ls="--", color="#444444", lw=1.1)
ax.text(0, avg + 8, f"월평균 {avg:.0f}건", color=TXT, fontsize=10.5, va="bottom")
for k in (mw.연장.values.argmin(), mw.연장.values.argmax()):
    ax.text(k, mw.연장.values[k] + 6, f"{mw.연장.values[k]:,}", ha="center", va="bottom", fontsize=10.5)
ax.set_xticks(x[::3]); ax.set_xticklabels([s[2:4] + "." + s[5:] for s in mw.index[::3]])
ax.set_ylabel("연장심사 건수(업체×만료일)", color=TXT); ax.set_ylim(0, 680); style(ax)
ax.legend(loc="upper right", ncol=2, frameon=False, fontsize=11.5, handlelength=2.2, columnspacing=2.2)
fig.tight_layout(); fig.savefig(f"{FIG}/그림3_월별_연장물량.png", dpi=200); plt.close(fig)

# 그림4
g4 = T15.drop(index="기타(주소 미분류)").sort_values("연장_2년")
fig, ax = plt.subplots(figsize=(7.6, 3.3))
yy = np.arange(len(g4)); fc_ = g4.첫연장_2년.values; tot = g4.연장_2년.values
ax.barh(yy, fc_, height=0.58, color=BLUE, label="첫 연장", edgecolor="white", lw=0.8)
ax.barh(yy, tot - fc_, left=fc_, height=0.58, color=GRAY, label="2회차 이상", edgecolor="white", lw=0.8)
for i, (t, fcv) in enumerate(zip(tot, fc_)):
    ax.text(t + 30, i, f"{t:,}건 (첫 연장 {fcv / t * 100:.0f}%)", va="center", fontsize=10.5)
ax.set_yticks(yy); ax.set_yticklabels(g4.index, fontsize=11); ax.set_xlim(0, 3050)
ax.set_xlabel("2027~2028년 연장심사 건수", color=TXT); style(ax, "x")
h, l = ax.get_legend_handles_labels(); ax.legend(h, l, loc="lower right", frameon=False, fontsize=11.5, handlelength=2.2)
fig.tight_layout(); fig.savefig(f"{FIG}/그림4_지원별_연장물량.png", dpi=200); plt.close(fig)

print(f"\n{sum(RES)}/{len(RES)} PASS" + ("" if all(RES) else "  <-- FAIL 있음"))
sys.exit(0 if all(RES) else 1)
