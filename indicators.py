"""技术指标与周期聚合（pandas，无重依赖）。"""
import pandas as pd


def add_ma(df, periods):
    """为含 close 列的 DataFrame 追加 MA{n} 均线列，返回新 DataFrame。"""
    df = df.copy()
    for p in periods:
        df[f"MA{p}"] = df["close"].rolling(window=p).mean()
    return df


def resample_period(df, period):
    """将日K按周期聚合为 OHLCV。

    period: "D"(日) / "W"(周) / "M"(月)。
    """
    if period == "D":
        return df.copy()
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    if period == "W":
        rule = "W-FRI"
    else:
        rule = "ME" if pd.__version__ >= "2.2" else "M"
    agg = (
        df.resample(rule)
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=["open", "close"])
    )
    agg = agg.reset_index()
    agg["date"] = agg["date"].dt.strftime("%Y-%m-%d")
    return agg
