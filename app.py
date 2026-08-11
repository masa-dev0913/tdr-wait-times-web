import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from common.db import DB_PATH, init_db

st.set_page_config(page_title="TDR待ち時間トラッカー", layout="wide")

PARK_LABELS = {"land": "東京ディズニーランド", "sea": "東京ディズニーシー"}


@st.cache_data(ttl=60)
def load_data(table: str) -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql(f"SELECT * FROM {table}", conn, parse_dates=["timestamp_jst"])


st.title("東京ディズニーランド・シー 待ち時間トラッカー")
st.caption("非公式サイト tokyodisneyresort.info の公開データを15分おきに記録しています。")

category = st.sidebar.radio("カテゴリ", ["アトラクション", "レストラン"])
table = "attractions" if category == "アトラクション" else "restaurants"
df = load_data(table)

if df.empty:
    st.info("まだデータがありません。スクレイパーの実行を待ってください。")
    st.stop()

park = st.sidebar.selectbox("パーク", options=["land", "sea"], format_func=lambda p: PARK_LABELS[p])
df_park = df[df["park"] == park]

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

df_period = df_park[(df_park["timestamp_jst"] >= start) & (df_park["timestamp_jst"] <= end)]

if df_period.empty:
    st.warning("選択した期間のデータがありません。期間を変えてお試しください。")
    st.stop()

facility_names = sorted(df_period["name"].unique())
selected = st.sidebar.multiselect("施設", facility_names, default=facility_names[:5])

if not selected:
    st.warning("施設を選択してください。")
    st.stop()

df_selected = df_period[df_period["name"].isin(selected)].copy()

st.subheader("待ち時間の推移")
if table == "attractions":
    fig = px.line(
        df_selected.sort_values("timestamp_jst"),
        x="timestamp_jst", y="wait_minutes", color="name", markers=True,
    )
    fig.update_layout(yaxis_title="待ち時間（分）", xaxis_title="時刻", legend_title="施設")
else:
    df_selected["wait_mid"] = (df_selected["wait_min"] + df_selected["wait_max"]) / 2
    fig = px.line(
        df_selected.sort_values("timestamp_jst"),
        x="timestamp_jst", y="wait_mid", color="name", markers=True,
    )
    fig.update_layout(yaxis_title="待ち時間の目安（分）", xaxis_title="時刻", legend_title="施設")
st.plotly_chart(fig, use_container_width=True)

st.subheader("直近のスナップショット")
latest_ts = df_period["timestamp_jst"].max()
latest = df_period[df_period["timestamp_jst"] == latest_ts]
st.caption(f"最終更新: {latest_ts:%Y-%m-%d %H:%M}")
if table == "attractions":
    st.dataframe(
        latest[["name", "status", "wait_minutes"]].sort_values("wait_minutes", ascending=False),
        use_container_width=True, hide_index=True,
    )
else:
    st.dataframe(
        latest[["name", "status", "wait_min", "wait_max"]],
        use_container_width=True, hide_index=True,
    )

st.subheader("日別サマリー（平均・最大 待ち時間）")
df_selected["date"] = df_selected["timestamp_jst"].dt.date
if table == "attractions":
    summary = (
        df_selected.groupby(["date", "name"])["wait_minutes"]
        .agg(平均="mean", 最大="max").round(1).reset_index()
    )
else:
    summary = (
        df_selected.groupby(["date", "name"])["wait_mid"]
        .agg(平均="mean", 最大="max").round(1).reset_index()
    )
st.dataframe(summary, use_container_width=True, hide_index=True)
