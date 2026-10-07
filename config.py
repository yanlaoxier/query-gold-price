"""全局配置：品种定义、单位、颜色、刷新间隔、默认汇率等。"""

# SQLite 数据库文件路径
DB_PATH = "gold.db"

# ---------------------------------------------------------------------------
# 品种清单（新浪财经数据源，免费、无需鉴权）
# market 取值：
#   "hf"   外盘现货/期货（伦敦金、纽约金、白银）
#   "nf"   内盘期货（沪金连续）
#   "idx"  指数（美元指数，字段格式特殊）
#   "fx"   汇率（美元兑人民币，用于价差换算）
# ---------------------------------------------------------------------------
INSTRUMENTS = {
    "XAU": {
        "symbol": "hf_XAU",
        "name": "伦敦金",
        "full_name": "伦敦金现货 XAU/USD",
        "market": "hf",
        "unit": "美元/盎司",
        "kline_symbol": "XAU",          # 日K接口所用的 symbol
        "kline_service": "global",       # global=国际品种  inner=国内期货
        "color": "#C8A24B",
        "is_gold": True,
    },
    "GC": {
        "symbol": "hf_GC",
        "name": "纽约金",
        "full_name": "纽约金 COMEX",
        "market": "hf",
        "unit": "美元/盎司",
        "kline_symbol": "GC",
        "kline_service": "global",
        "color": "#B8860B",
        "is_gold": True,
    },
    "XAG": {
        "symbol": "hf_XAG",
        "name": "现货白银",
        "full_name": "现货白银 XAG/USD",
        "market": "hf",
        "unit": "美元/盎司",
        "kline_symbol": "XAG",
        "kline_service": "global",
        "color": "#8A99B5",
        "is_gold": False,
    },
    "AU0": {
        "symbol": "nf_AU0",
        "name": "沪金连续",
        "full_name": "沪金连续 Au（上期所）",
        "market": "nf",
        "unit": "人民币/克",
        "kline_symbol": "AU0",
        "kline_service": "inner",
        "color": "#C0392B",
        "is_gold": True,
    },
    "DINIW": {
        "symbol": "DINIW",
        "name": "美元指数",
        "full_name": "美元指数 DXY",
        "market": "idx",
        "unit": "点",
        "kline_symbol": None,            # 无可用日K端点，降级为实时卡片+快照趋势
        "kline_service": None,
        "color": "#2C5F8A",
        "is_gold": False,
    },
}

# 汇率 symbol（用于国内外价差换算）
FX_SYMBOL = "fx_susdcny"
FX_NAME = "美元兑人民币"

# 1 金衡盎司 = 31.1034768 克（用于国内金价换算成美元/盎司）
TROY_OUNCE_GRAMS = 31.1034768

# 汇率接口失败时的兜底默认汇率（可自行修改）
DEFAULT_USD_CNY = 6.70

# MA 均线周期
MA_PERIODS = [5, 10, 20, 60]

# 默认自动刷新间隔（秒）
DEFAULT_REFRESH_SECONDS = 60

# 涨跌颜色（中国习惯：红涨绿跌）
UP_COLOR = "#E03131"
DOWN_COLOR = "#0CA678"
