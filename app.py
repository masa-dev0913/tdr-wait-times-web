import html
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from common.db import DB_PATH, init_db

st.set_page_config(page_title="TDR待ち時間トラッカー", page_icon="🏰", layout="wide")

PARK_LABELS = {"land": "東京ディズニーランド", "sea": "東京ディズニーシー"}
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
UNCLASSIFIED_AREA = "その他"

INK = "#1c2430"
MUTED = "#57626c"
LINE = "#dfe1db"
CARD_BG = "#ffffff"
ACCENT = "#3b6ea5"
SEVERITY_COLORS = {
    "green": ("#e4f2e7", "#1f7a3d"),
    "amber": ("#fbeed9", "#a05a12"),
    "red": ("#fbe3e0", "#b3341c"),
    "grey": ("#e8e9e4", "#5c6570"),
}

CSS = f"""
<style>
  .stApp {{
    font-family: -apple-system, "Segoe UI", "Hiragino Kaku Gothic ProN", "Yu Gothic UI",
      "Yu Gothic", "Meiryo", Arial, sans-serif;
  }}
  [data-testid="stSidebar"] {{ background: #eceee8; }}
  h1, h2, h3 {{ letter-spacing: -0.01em; }}
  [data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}

  .wt-updated {{
    display: inline-block;
    font-size: 12.5px;
    font-weight: 700;
    color: {MUTED};
    background: #eceee8;
    border-radius: 999px;
    padding: 4px 12px;
    margin: -4px 0 18px;
  }}

  .wt-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
    gap: 10px;
    margin: 4px 0 6px;
  }}
  .wt-card {{
    background: {CARD_BG};
    border: 1px solid {LINE};
    border-radius: 12px;
    padding: 13px 15px;
  }}
  .wt-card-name {{
    font-weight: 700;
    font-size: 14px;
    color: {INK};
    line-height: 1.35;
    margin-bottom: 2px;
    min-height: 2.7em;
  }}
  .wt-card-area {{
    font-size: 11px;
    color: {MUTED};
    margin-bottom: 10px;
  }}
  .wt-card-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }}
  .wt-pill {{
    font-weight: 700;
    font-size: 12.5px;
    padding: 4px 10px;
    border-radius: 999px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }}
  .wt-card-status {{
    font-size: 11.5px;
    color: {MUTED};
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}

  .wt-rank-list {{
    display: flex;
    flex-direction: column;
    background: {CARD_BG};
    border: 1px solid {LINE};
    border-radius: 12px;
    padding: 4px 14px;
    margin: 4px 0 6px;
  }}
  .wt-rank-row {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid {LINE};
  }}
  .wt-rank-row:last-child {{ border-bottom: none; }}
  .wt-rank-no {{
    font-weight: 800;
    font-size: 14px;
    color: {MUTED};
    width: 1.6em;
    flex: none;
    text-align: center;
  }}
  .wt-rank-name {{ flex: 1; font-weight: 700; font-size: 14px; color: {INK}; }}
  .wt-rank-area {{ font-weight: 400; font-size: 11.5px; color: {MUTED}; margin-left: 6px; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data(table: str, park: str, start: str, end: str) -> pd.DataFrame:
    """期間・パークで絞り込んだ分だけをSQLite側でSELECTする。
    テーブル全件を読んでからpandasで絞ると、データが増えるほど
    メモリ使用量が際限なく伸びてしまうため。"""
    init_db()
    query = (
        f"SELECT * FROM {table} "
        "WHERE park = ? AND timestamp_jst >= ? AND timestamp_jst <= ? "
        "ORDER BY timestamp_jst"
    )
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql(
            query, conn, params=(park, start, end), parse_dates=["timestamp_jst"]
        )
    df["area"] = df["area"].replace("", UNCLASSIFIED_AREA)
    return df


def severity(minutes: float | None) -> str:
    if minutes is None or pd.isna(minutes):
        return "grey"
    if minutes <= 15:
        return "green"
    if minutes <= 40:
        return "amber"
    return "red"


def wait_label(row: pd.Series, table: str) -> tuple[str, float | None]:
    if table == "attractions":
        minutes = row["wait_minutes"]
        if pd.isna(minutes):
            return row["status"], None
        return f"{int(minutes)}分", minutes
    lo, hi = row["wait_min"], row["wait_max"]
    if pd.isna(lo):
        return row["status"], None
    lo, hi = int(lo), int(hi)
    label = f"{lo}分" if lo == hi else f"{lo}〜{hi}分"
    return label, hi


def render_snapshot_cards(latest: pd.DataFrame, table: str) -> None:
    rows_html = []
    for _, row in latest.sort_values(["area", "name"]).iterrows():
        label, minutes = wait_label(row, table)
        bg, fg = SEVERITY_COLORS[severity(minutes)]
        name = html.escape(str(row["name"]))
        area = html.escape(str(row["area"]))
        status = html.escape(str(row["status"]))
        rows_html.append(
            f'<div class="wt-card"><div class="wt-card-name">{name}</div>'
            f'<div class="wt-card-area">{area}</div>'
            f'<div class="wt-card-row">'
            f'<span class="wt-pill" style="background:{bg};color:{fg}">{html.escape(label)}</span>'
            f'<span class="wt-card-status">{status}</span>'
            f"</div></div>"
        )
    st.markdown(f'<div class="wt-grid">{"".join(rows_html)}</div>', unsafe_allow_html=True)


def render_popularity_ranking(df_period: pd.DataFrame, top_n: int = 5) -> None:
    stats = (
        df_period.dropna(subset=["wait_minutes"])
        .groupby(["name", "area"])["wait_minutes"]
        .mean()
        .reset_index()
        .sort_values("wait_minutes", ascending=False)
        .head(top_n)
    )
    if stats.empty:
        st.caption("この期間は待ち時間の記録がありません。")
        return
    rows_html = []
    for rank, (_, row) in enumerate(stats.iterrows(), start=1):
        bg, fg = SEVERITY_COLORS[severity(row["wait_minutes"])]
        name = html.escape(str(row["name"]))
        area = html.escape(str(row["area"]))
        rows_html.append(
            '<div class="wt-rank-row">'
            f'<span class="wt-rank-no">{rank}</span>'
            f'<span class="wt-rank-name">{name}<span class="wt-rank-area">{area}</span></span>'
            f'<span class="wt-pill" style="background:{bg};color:{fg}">平均{row["wait_minutes"]:.0f}分</span>'
            "</div>"
        )
    st.markdown(f'<div class="wt-rank-list">{"".join(rows_html)}</div>', unsafe_allow_html=True)


st.title("東京ディズニーランド・シー 待ち時間トラッカー")
st.caption("非公式サイト tokyodisneyresort.info の公開データを15分おきに記録しています。")

category = st.sidebar.radio("カテゴリ", ["アトラクション", "レストラン"])
table = "attractions" if category == "アトラクション" else "restaurants"

park = st.sidebar.selectbox("パーク", options=["land", "sea"], format_func=lambda p: PARK_LABELS[p])

period = st.sidebar.radio("期間", ["今日", "過去7日間", "カスタム"])
now = datetime.now()
if period == "今日":
    start = datetime.combine(now.date(), datetime.min.time())
    end = now
elif period == "過去7日間":
    start = now - timedelta(days=7)
    end = now
else:
    date_range = st.sidebar.date_input(
        "日付範囲", value=(now.date() - timedelta(days=7), now.date())
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start = datetime.combine(date_range[0], datetime.min.time())
        end = datetime.combine(date_range[1], datetime.max.time())
    else:
        single_date = date_range if not isinstance(date_range, tuple) else date_range[0]
        start = datetime.combine(single_date, datetime.min.time())
        end = datetime.combine(single_date, datetime.max.time())

df_period = load_data(table, park, start.strftime(TIMESTAMP_FORMAT), end.strftime(TIMESTAMP_FORMAT))

if df_period.empty:
    st.info("選択した期間のデータがありません。スクレイパーの実行を待つか、期間を変えてお試しください。")
    st.stop()

# エリア情報を追加する前の古いレコードは area が空になっているため、
# 同じ施設内では最新の分類に統一する（過渡期に同じ施設が2つのエリアに
# 分かれて表示されるのを防ぐ）。
canonical_area = (
    df_period.sort_values("timestamp_jst").drop_duplicates("name", keep="last").set_index("name")["area"]
)
df_period["area"] = df_period["name"].map(canonical_area)

area_options = sorted(df_period["area"].unique())
selected_areas = st.sidebar.multiselect("エリア", area_options, default=area_options)

if not selected_areas:
    st.warning("エリアを選択してください。")
    st.stop()

facility_pool = df_period[df_period["area"].isin(selected_areas)]
facility_lookup = (
    facility_pool[["area", "name"]].drop_duplicates().sort_values(["area", "name"])
)
facility_names = facility_lookup["name"].tolist()
area_by_name = dict(zip(facility_lookup["name"], facility_lookup["area"]))
selected = st.sidebar.multiselect(
    "施設",
    facility_names,
    default=facility_names[:5],
    format_func=lambda n: f"{area_by_name[n]} ・ {n}",
)

if not selected:
    st.warning("施設を選択してください。")
    st.stop()

df_selected = df_period[df_period["name"].isin(selected)].copy()
if table == "restaurants":
    df_selected["wait_mid"] = (df_selected["wait_min"] + df_selected["wait_max"]) / 2

value_col = "wait_minutes" if table == "attractions" else "wait_mid"
latest_ts = df_selected["timestamp_jst"].max()
latest = df_selected[df_selected["timestamp_jst"] == latest_ts]

st.markdown(f'<span class="wt-updated">最終更新 {latest_ts:%Y-%m-%d %H:%M}</span>', unsafe_allow_html=True)

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("表示中の施設", f"{len(selected)}件")
valid = latest[value_col].dropna()
kpi2.metric("平均待ち時間", f"{valid.mean():.0f}分" if len(valid) else "—")
if len(valid):
    top_row = latest.loc[valid.idxmax()]
    kpi3.metric("最大待ち時間", f"{valid.max():.0f}分", help=str(top_row["name"]))
else:
    kpi3.metric("最大待ち時間", "—")

if table == "attractions":
    st.subheader("人気アトラクション")
    st.caption("選択中の期間・パーク全体で、平均待ち時間が長い上位5施設です（左のフィルターには連動しません）。")
    render_popularity_ranking(df_period)

st.subheader("待ち時間の推移")
fig = px.line(
    df_selected.sort_values("timestamp_jst"),
    x="timestamp_jst", y=value_col, color="name", markers=True,
)
fig.update_layout(
    yaxis_title="待ち時間（分）" if table == "attractions" else "待ち時間の目安（分）",
    xaxis_title=None,
    legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5, title=None),
    margin=dict(l=10, r=10, t=10, b=10),
    colorway=["#3b6ea5", "#b5762c", "#1f7a3d", "#8b5fbf", "#b3341c", "#5c6570"],
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=INK, size=12),
)
fig.update_xaxes(gridcolor=LINE)
fig.update_yaxes(gridcolor=LINE)
st.plotly_chart(fig, use_container_width=True)

st.subheader("直近のスナップショット")
render_snapshot_cards(latest, table)

st.subheader("日別サマリー（平均・最大 待ち時間）")
df_selected["date"] = df_selected["timestamp_jst"].dt.date
summary = (
    df_selected.groupby(["date", "name"])[value_col]
    .agg(平均="mean", 最大="max").round(1).reset_index()
)
st.dataframe(summary, use_container_width=True, hide_index=True)
