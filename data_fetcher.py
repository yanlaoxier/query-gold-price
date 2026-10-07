"""新浪财经数据抓取：实时行情 + 日K线。

接口免费、无需鉴权，返回 GBK 编码，需带 Referer 请求头。
"""
import json
import re
import time

import requests

from config import FX_NAME, FX_SYMBOL, INSTRUMENTS

HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

RT_URL = "https://hq.sinajs.cn/list={}"
GLOBAL_KLINE_URL = (
    "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/"
    "var%20_t=/GlobalFuturesService.getGlobalFuturesDailyKLine?symbol={}"
)
INNER_KLINE_URL = (
    "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/"
    "var%20_t=/InnerFuturesNewService.getDailyKLine?symbol={}"
)


def _get(url, retries=3, timeout=10):
    """GET 请求，GBK 解码，带指数退避重试。失败抛异常。"""
    last_err = None
    for i in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = "gbk"
            return resp.text
        except Exception as e:  # noqa: BLE001
            last_err = e
            if i < retries - 1:
                time.sleep(1 * (2 ** i))
    raise RuntimeError(f"请求失败: {url} — {last_err}")


def _to_float(s, default=None):
    """安全转 float，空串/None/异常返回 default。"""
    try:
        if s is None or s == "":
            return default
        return float(s)
    except (TypeError, ValueError):
        return default


def _parse_hf(fields):
    """外盘 hf_ 品种字段：最新,昨收,今开,?,最高,最低,时间,买价,卖价,..."""
    price = _to_float(fields[0])
    prev_close = _to_float(fields[1]) if len(fields) > 1 else None
    open_ = _to_float(fields[2]) if len(fields) > 2 else None
    high = _to_float(fields[4]) if len(fields) > 4 else None
    low = _to_float(fields[5]) if len(fields) > 5 else None
    return price, open_, high, low, prev_close


def _parse_nf(fields):
    """内盘期货 nf_ 字段：名称,时间,开盘,最高,最低,最新,买价,卖价,昨结,昨收,持仓,..."""
    price = _to_float(fields[5]) if len(fields) > 5 else None
    open_ = _to_float(fields[2]) if len(fields) > 2 else None
    high = _to_float(fields[3]) if len(fields) > 3 else None
    low = _to_float(fields[4]) if len(fields) > 4 else None
    prev_close = _to_float(fields[9]) if len(fields) > 9 else None
    return price, open_, high, low, prev_close


def _parse_idx(fields):
    """美元指数字段：时间,最新,今开,前收,量,?,最高,最低,?,名称,日期。"""
    price = _to_float(fields[1]) if len(fields) > 1 else None
    open_ = _to_float(fields[2]) if len(fields) > 2 else None
    prev_close = _to_float(fields[3]) if len(fields) > 3 else None
    high = _to_float(fields[6]) if len(fields) > 6 else None
    low = _to_float(fields[7]) if len(fields) > 7 else None
    return price, open_, high, low, prev_close


def _parse_fx(fields):
    """汇率 fx_susdcny 字段：时间,最新,?,... —— 取最新价。"""
    return _to_float(fields[1]) if len(fields) > 1 else None, None, None, None, None


def _build_quote(symbol_key, inst, price, open_, high, low, prev_close):
    """组装统一的实时报价结构。"""
    change = None
    change_pct = None
    if price is not None and prev_close:
        change = price - prev_close
        change_pct = change / prev_close * 100
    return {
        "key": symbol_key,
        "symbol": inst["symbol"],
        "name": inst["name"],
        "full_name": inst["full_name"],
        "unit": inst["unit"],
        "color": inst["color"],
        "is_gold": inst["is_gold"],
        "market": inst["market"],
        "price": price,
        "open": open_,
        "high": high,
        "low": low,
        "prev_close": prev_close,
        "change": change,
        "change_pct": change_pct,
    }


def fetch_realtime():
    """抓取所有品种 + 汇率实时行情。

    返回 (quotes: dict[key->dict], fx_rate: float|None)
    """
    symbols = [inst["symbol"] for inst in INSTRUMENTS.values()] + [FX_SYMBOL]
    text = _get(RT_URL.format(",".join(symbols)))

    # 解析出每个 var hq_str_XXX="...";
    raw = {}
    for m in re.finditer(r'hq_str_(\w+)="([^"]*)"', text):
        raw[m.group(1)] = m.group(2)

    quotes = {}
    for key, inst in INSTRUMENTS.items():
        value = raw.get(inst["symbol"], "")
        fields = value.split(",") if value else []
        market = inst["market"]
        if market == "hf":
            price, open_, high, low, prev_close = _parse_hf(fields)
        elif market == "nf":
            price, open_, high, low, prev_close = _parse_nf(fields)
        elif market == "idx":
            price, open_, high, low, prev_close = _parse_idx(fields)
        else:
            price, open_, high, low, prev_close = None, None, None, None, None
        quotes[key] = _build_quote(key, inst, price, open_, high, low, prev_close)

    # 汇率
    fx_value = raw.get(FX_SYMBOL, "")
    fx_fields = fx_value.split(",") if fx_value else []
    fx_rate = _parse_fx(fx_fields)[0] if fx_fields else None

    return quotes, fx_rate


def _strip_jsonp(text):
    """从 JSONP 文本中剥离出括号内的 JSON 字符串，返回解析后的对象。"""
    start = text.find("(")
    end = text.rfind(")")
    if start == -1 or end == -1 or end <= start:
        return None
    payload = text[start + 1 : end].strip()
    if payload in ("", "null"):
        return None
    return json.loads(payload)


def _normalize_global(data):
    """GlobalFuturesService 返回 [{date,open,high,low,close,volume,position,s}]。"""
    rows = []
    for item in data or []:
        rows.append(
            {
                "date": item["date"],
                "open": _to_float(item.get("open")),
                "high": _to_float(item.get("high")),
                "low": _to_float(item.get("low")),
                "close": _to_float(item.get("close")),
                "volume": _to_float(item.get("volume"), 0.0),
            }
        )
    return rows


def _normalize_inner(data):
    """InnerFuturesNewService 返回 [{d,o,h,l,c,v,p,s}, ...]。"""
    rows = []
    for item in data or []:
        rows.append(
            {
                "date": item["d"],
                "open": _to_float(item.get("o")),
                "high": _to_float(item.get("h")),
                "low": _to_float(item.get("l")),
                "close": _to_float(item.get("c")),
                "volume": _to_float(item.get("v"), 0.0),
            }
        )
    return rows


def fetch_kline(key):
    """抓取某品种全量日K，返回 list[dict]（含 symbol 字段，可直接入库）。"""
    inst = INSTRUMENTS[key]
    if not inst["kline_symbol"] or not inst["kline_service"]:
        return []

    if inst["kline_service"] == "global":
        url = GLOBAL_KLINE_URL.format(inst["kline_symbol"])
        text = _get(url)
        data = _strip_jsonp(text)
        rows = _normalize_global(data)
    else:
        url = INNER_KLINE_URL.format(inst["kline_symbol"])
        text = _get(url)
        data = _strip_jsonp(text)
        rows = _normalize_inner(data)

    for r in rows:
        r["symbol"] = key
    return rows
