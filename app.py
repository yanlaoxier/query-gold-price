"""黄金价格实时查询 · Streamlit 主入口。

运行：streamlit run app.py
"""
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import charts
import config
import database as db
import data_fetcher as fetcher
import indicators
from config import (
    DEFAULT_USD_CNY,
    INSTRUMENTS,
    MA_PERIODS,
    TROY_OUNCE_GRAMS,
)

st.set_page_config(page_title="黄金价格实时查询", page_icon="🥇", layout="wide")

# ---------------- 数据库初始化 ----------------
db.init_db()

# ---------------- 侧边栏 ----------------
with st.sidebar:
    st.title("⚙️ 设置")
    period_label = st.radio("K线周期", ["日", "周", "月"], index=0, horizontal=True)
    refresh_sec = st.select_slider(
        "自动刷新间隔(秒)",
        options=[15, 30, 60, 120, 300],
        value=config.DEFAULT_REFRESH_SECONDS,
    )
    days = st.slider("显示时间范围(天)", 30, 1825, 365, step=30)
    show_ma = st.multiselect("均线", [5, 10, 20, 60], default=MA_PERIODS)
    st.divider()
    st.caption("数据来源：新浪财经（免费接口，约 1 分钟延迟）")
    st.caption("红涨绿跌 · 仅供参考，不构成投资建议")

PERIOD_MAP = {"日": "D", "周": "W", "月": "M"}

# 自动刷新（单位：毫秒）
st_autorefresh(interval=refresh_sec * 1000, key="gold_refresh")

# ---------------- 实时行情抓取 ----------------
ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

quotes, fx_rate = {}, None
try:
    quotes, fx_rate = fetcher.fetch_realtime()
    if quotes:
        db.append_realtime(
            [
                {
                    "symbol": q["symbol"],
                    "name": q["name"],
                    "price": q["price"],
                    "open": q["open"],
                    "high": q["high"],
                    "low": q["low"],
                    "prev_close": q["prev_close"],
                    "change": q["change"],
                    "change_pct": q["change_pct"],
                    "ts": ts_now,
                }
                for q in quotes.values()
            ]
        )
except Exception as e:  # noqa: BLE001
    st.error(f"实时行情获取失败：{e}")

if fx_rate is None:
    fx_rate = DEFAULT_USD_CNY


# ---------------- K线增量缓存 ----------------
@st.cache_data(ttl=300, show_spinner=False)
def _cached_kline(key):
    return fetcher.fetch_kline(key)


def ensure_kline(key):
    """增量更新某品种日K（仅写入最新一段，降低被限流风险）。"""
    try:
        krows = _cached_kline(key)
        if not krows:
            return
        latest = db.get_latest_kline_date(key)
        if latest:
            krows = [r for r in krows if r["date"] >= latest]
        db.upsert_kline(krows)
    except Exception as e:  # noqa: BLE001
        st.warning(f"{INSTRUMENTS[key]['name']} K线更新失败：{e}")


with st.spinner("加载数据中…"):
    for key in INSTRUMENTS:
        if INSTRUMENTS[key]["kline_service"]:
            ensure_kline(key)

kline_keys = [k for k in INSTRUMENTS if INSTRUMENTS[k]["kline_service"]]
start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def load_kline(key, period="D"):
    """从 SQLite 读取并加工为指定周期的 DataFrame（含 MA）。"""
    rows = db.get_kline(key, start=start_date)
    if not rows:
        return pd.DataFrame()
    pdf = pd.DataFrame(rows)
    pdf = indicators.resample_period(pdf, period)
    pdf = indicators.add_ma(pdf, show_ma if show_ma else [])
    return pdf


def _fmt_price(v, nd=2):
    return f"{v:,.{nd}f}" if v is not None else "—"


# ---------------- 顶部指标卡 ----------------
st.title("🥇 黄金价格实时查询")
st.caption(f"最后更新：{ts_now} · 每 {refresh_sec} 秒自动刷新")

if quotes:
    cols = st.columns(len(quotes))
    for col, (key, q) in zip(cols, quotes.items()):
        with col:
            delta = None
            if q["change"] is not None and q["change_pct"] is not None:
                delta = f"{q['change']:+.2f} ({q['change_pct']:+.2f}%)"
            st.metric(
                label=f"{q['name']}（{q['unit']}）",
                value=_fmt_price(q["price"]),
                delta=delta,
                delta_color="inverse",  # 红涨绿跌
            )

st.divider()

# ---------------- 标签页 ----------------
tab1, tab2, tab3, tab4 = st.tabs(["📈 K线图", "📉 趋势与对比", "💱 国内外价差", "📋 历史数据"])

# --- Tab1: K线图 ---
with tab1:
    c1, _ = st.columns([1, 3])
    with c1:
        sel_key = st.radio(
            "选择品种",
            kline_keys,
            format_func=lambda k: INSTRUMENTS[k]["full_name"],
            horizontal=True,
        )
    pdf = load_kline(sel_key, PERIOD_MAP[period_label])
    if pdf.empty:
        st.info("暂无 K 线数据，请稍候刷新。")
    else:
        fig = charts.kline_chart(
            pdf,
            f"{INSTRUMENTS[sel_key]['full_name']} · {period_label}K",
            ma_periods=show_ma,
        )
        st.plotly_chart(fig, width="stretch")

# --- Tab2: 趋势与对比 ---
with tab2:
    c2, c3 = st.columns([1, 3])
    with c2:
        sel2 = st.selectbox(
            "选择品种",
            kline_keys,
            format_func=lambda k: INSTRUMENTS[k]["full_name"],
            key="sel_trend",
        )
    pdf2 = load_kline(sel2, PERIOD_MAP[period_label])
    if pdf2.empty:
        st.info("暂无数据。")
    else:
        chart_type = st.radio("图表类型", ["折线图", "面积图"], horizontal=True)
        if chart_type == "折线图":
            fig2 = charts.line_chart(
                pdf2, f"{INSTRUMENTS[sel2]['full_name']} · 收盘价", INSTRUMENTS[sel2]["color"]
            )
        else:
            fig2 = charts.area_chart(
                pdf2, f"{INSTRUMENTS[sel2]['full_name']} · 收盘价", INSTRUMENTS[sel2]["color"]
            )
        st.plotly_chart(fig2, width="stretch")

    st.subheader("多品种累计涨跌幅对比")
    series = {}
    for k in kline_keys:
        d = load_kline(k, PERIOD_MAP[period_label])
        if not d.empty:
            series[INSTRUMENTS[k]["name"]] = d
    if series:
        st.plotly_chart(charts.compare_chart(series), width="stretch")

    st.subheader("美元指数 · 实时快照趋势")
    diniw_records = db.get_realtime_history("DINIW", n=500)
    if len(diniw_records) > 1:
        st.plotly_chart(
            charts.snapshot_trend_chart(
                diniw_records, "美元指数 · 实时快照趋势（随运行累积）"
            ),
            width="stretch",
        )
    else:
        st.caption("美元指数无历史日K接口，趋势需运行一段时间、累积快照后显示。")

# --- Tab3: 国内外价差 ---
with tab3:
    st.caption(
        "价差 = 国内金价换算成美元/盎司 − 国际伦敦金。"
        f"换算：沪金(元/克) × {TROY_OUNCE_GRAMS:.4f} 克/盎司 ÷ 汇率 {fx_rate:.4f}。"
    )

    if "XAU" in kline_keys and "AU0" in kline_keys:
        xau = pd.DataFrame(db.get_kline("XAU", start=start_date))
        au = pd.DataFrame(db.get_kline("AU0", start=start_date))
        if not xau.empty and not au.empty:
            merged = pd.merge(
                xau[["date", "close"]],
                au[["date", "close"]],
                on="date",
                suffixes=("_xau", "_au"),
            )
            merged["au_usd"] = merged["close_au"] * TROY_OUNCE_GRAMS / fx_rate
            merged["spread"] = merged["au_usd"] - merged["close_xau"]
            merged["premium_pct"] = merged["spread"] / merged["close_xau"] * 100

            # 当前实时价差
            if "XAU" in quotes and "AU0" in quotes and quotes["XAU"]["price"] and quotes["AU0"]["price"]:
                cur_au_usd = quotes["AU0"]["price"] * TROY_OUNCE_GRAMS / fx_rate
                cur_spread = cur_au_usd - quotes["XAU"]["price"]
                cur_pct = cur_spread / quotes["XAU"]["price"] * 100
                m1, m2, m3 = st.columns(3)
                m1.metric("国内换算价", f"{cur_au_usd:,.2f} 美元/盎司")
                m2.metric("国际伦敦金", f"{quotes['XAU']['price']:,.2f} 美元/盎司")
                m3.metric("实时价差", f"{cur_spread:+.2f} 美元/盎司", f"{cur_pct:+.2f}%")

            st.plotly_chart(charts.spread_chart(merged), width="stretch")
        else:
            st.info("价差数据不足，请稍候刷新。")
    else:
        st.info("需要伦敦金与沪金数据方可计算价差。")

# --- Tab4: 历史数据 ---
with tab4:
    sel4 = st.selectbox(
        "选择品种", kline_keys, format_func=lambda k: INSTRUMENTS[k]["full_name"], key="sel_data"
    )
    rows4 = db.get_kline(sel4, start=start_date)
    if rows4:
        df4 = pd.DataFrame(rows4).sort_values("date", ascending=False)
        st.dataframe(df4, width="stretch", height=480)
    else:
        st.info("暂无数据。")

st.caption(
    "⚠️ 数据来自公开免费接口，可能存在延迟或缺失，仅供学习参考，不构成任何投资建议。"
)
