"""Plotly 图表构建：K线、折线、面积、对比、价差、快照趋势。"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import DOWN_COLOR, UP_COLOR

# 通用布局：隐藏多余空白，移动端友好
BASE_LAYOUT = dict(
    template="plotly_white",
    margin=dict(l=40, r=20, t=40, b=30),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)


def _to_dt(df):
    return pd.to_datetime(df["date"])


def kline_chart(df, title, ma_periods=(5, 10, 20, 60), show_volume=True):
    """K线图：主图 candlestick + MA 均线，副图成交量。"""
    df = df.reset_index(drop=True)
    x = _to_dt(df)

    if show_volume:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            row_heights=[0.72, 0.28],
            vertical_spacing=0.03,
        )
    else:
        fig = make_subplots(rows=1, cols=1)

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K线",
            increasing_line_color=UP_COLOR,
            increasing_fillcolor=UP_COLOR,
            decreasing_line_color=DOWN_COLOR,
            decreasing_fillcolor=DOWN_COLOR,
        ),
        row=1,
        col=1,
    )

    ma_colors = {5: "#F5A623", 10: "#2C5F8A", 20: "#9B59B6", 60: "#16A085"}
    for p in ma_periods:
        col = f"MA{p}"
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=df[col],
                    name=f"MA{p}",
                    mode="lines",
                    line=dict(width=1.2, color=ma_colors.get(p, "#888")),
                ),
                row=1,
                col=1,
            )

    if show_volume:
        vol_colors = [
            UP_COLOR if c >= o else DOWN_COLOR for c, o in zip(df["close"], df["open"])
        ]
        fig.add_trace(
            go.Bar(
                x=x,
                y=df["volume"],
                name="成交量",
                marker_color=vol_colors,
                opacity=0.6,
            ),
            row=2,
            col=1,
        )
        fig.update_yaxes(title_text="成交量", row=2, col=1)

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_rangeslider_visible=False,
        **BASE_LAYOUT,
    )
    fig.update_yaxes(title_text="价格", row=1, col=1)
    return fig


def line_chart(df, title, color=None):
    """收盘价折线图。"""
    fig = go.Figure(
        go.Scatter(
            x=_to_dt(df),
            y=df["close"],
            mode="lines",
            name="收盘价",
            line=dict(width=2, color=color or "#C8A24B"),
        )
    )
    fig.update_layout(title=dict(text=title, font=dict(size=16)), **BASE_LAYOUT)
    return fig


def area_chart(df, title, color=None):
    """收盘价面积图。"""
    fig = go.Figure(
        go.Scatter(
            x=_to_dt(df),
            y=df["close"],
            mode="lines",
            name="收盘价",
            line=dict(width=2, color=color or "#C8A24B"),
            fill="tozeroy",
            fillcolor="rgba(200,162,75,0.15)",
        )
    )
    fig.update_layout(title=dict(text=title, font=dict(size=16)), **BASE_LAYOUT)
    return fig


def compare_chart(series_map):
    """多品种收盘价归一化对比（相对首日涨幅%）。series_map: {名称: df}。"""
    fig = go.Figure()
    for name, df in series_map.items():
        if df is None or df.empty:
            continue
        closes = df["close"].astype(float)
        base = closes.iloc[0]
        if not base:
            continue
        norm = (closes / base - 1) * 100
        fig.add_trace(
            go.Scatter(
                x=_to_dt(df),
                y=norm,
                mode="lines",
                name=name,
                line=dict(width=1.8),
            )
        )
    fig.update_layout(
        title=dict(text="多品种累计涨跌幅对比（%）", font=dict(size=16)),
        yaxis_title="累计涨跌幅（%）",
        **BASE_LAYOUT,
    )
    return fig


def spread_chart(df):
    """国内外价差图：左轴价差（美元/盎司），右轴升贴水（%）。"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    x = _to_dt(df)
    fig.add_trace(
        go.Scatter(x=x, y=df["spread"], name="价差(美元/盎司)",
                   mode="lines", line=dict(width=1.8, color="#C0392B")),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=x, y=df["premium_pct"], name="升贴水(%)",
                   mode="lines", line=dict(width=1.2, color="#2C5F8A", dash="dot")),
        secondary_y=True,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#999", opacity=0.5)
    fig.update_layout(
        title=dict(text="国内外金价价差（国内换算价 − 国际伦敦金）", font=dict(size=16)),
        **BASE_LAYOUT,
    )
    fig.update_yaxes(title_text="价差(美元/盎司)", secondary_y=False)
    fig.update_yaxes(title_text="升贴水(%)", secondary_y=True)
    return fig


def snapshot_trend_chart(records, title):
    """实时快照趋势（用于无日K的品种，如美元指数）。records: list[{price,ts}]。"""
    if not records:
        return None
    df = pd.DataFrame(records)
    fig = go.Figure(
        go.Scatter(
            x=pd.to_datetime(df["ts"]),
            y=df["price"],
            mode="lines+markers",
            name="实时价",
            line=dict(width=2, color="#2C5F8A"),
        )
    )
    fig.update_layout(title=dict(text=title, font=dict(size=16)), **BASE_LAYOUT)
    return fig
