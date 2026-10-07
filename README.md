# 🥇 黄金价格实时查询

一个基于 **Python + Streamlit + SQLite** 的实时国际/国内金价查询应用，提供 K 线图、趋势图、多品种对比、国内外价差等多种图表，适配电脑、鸿蒙、安卓手机浏览器随时查看。

## ✨ 功能特性

- **实时价格卡片**：伦敦金（XAU/USD）、纽约金（COMEX）、现货白银、沪金连续（Au）、美元指数
- **K 线图**：candlestick + MA5/10/20/60 均线 + 成交量副图，支持日/周/月周期切换
- **趋势与对比**：折线图、面积图、多品种累计涨跌幅对比
- **国内外价差**：国内金价换算成美元/盎司后与国际金价的价差及升贴水
- **自动刷新**：可配置刷新间隔（15s ~ 5min），数据持久化到 SQLite

## 🗂 项目结构

```
├── app.py             # Streamlit 主入口
├── config.py          # 品种配置、颜色、刷新间隔、默认汇率
├── data_fetcher.py    # 新浪财经数据抓取（实时 + 日K）
├── database.py        # SQLite 存储层
├── indicators.py      # 均线计算 + 周期聚合
├── charts.py          # Plotly 图表
├── requirements.txt   # 依赖
├── Dockerfile         # VPS/Docker 部署
└── .streamlit/        # Streamlit 主题配置
```

## 🔌 数据源

数据来自**新浪财经免费公开接口**（无需鉴权，返回 GBK 编码）：

| 品种 | 实时 symbol | 日K接口 |
|------|-------------|---------|
| 伦敦金 XAU/USD | `hf_XAU` | GlobalFuturesService |
| 纽约金 COMEX | `hf_GC` | GlobalFuturesService |
| 现货白银 XAG | `hf_XAG` | GlobalFuturesService |
| 沪金连续 Au | `nf_AU0` | IndexService |
| 美元指数 DXY | `DINIW` | 仅实时（无历史日K，降级为实时卡片+快照趋势） |

> ⚠️ 免费接口约 1 分钟延迟，仅供学习参考，不构成投资建议。

## 🚀 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动
streamlit run app.py
```

启动后浏览器自动打开 `http://localhost:8501`。

**手机/鸿蒙访问**：确保手机与电脑在同一局域网，用电脑局域网 IP 访问，例如 `http://192.168.1.100:8501`。

## ☁️ 云端部署（手机随时访问）

### 方式一：Streamlit Community Cloud（免费，推荐）

1. 把本项目推送到 GitHub 仓库
2. 访问 [share.streamlit.io](https://share.streamlit.io) 用 GitHub 登录
3. 新建 App，选择该仓库，主文件选 `app.py`，点击 Deploy
4. 部署完成后获得公网 URL，手机/鸿蒙浏览器直接访问

### 方式二：VPS + Docker

```bash
docker build -t gold-price .
docker run -d -p 8501:8501 --restart unless-stopped \
  -v gold_data:/app gold-price
```

### 方式三：VPS 直接运行

```bash
pip install -r requirements.txt
nohup streamlit run app.py --server.port=8501 --server.address=0.0.0.0 &
```

## ⚙️ 自定义

在 `config.py` 中可调整：
- `DEFAULT_USD_CNY`：汇率接口失败时的兜底汇率
- `MA_PERIODS`：默认均线周期
- `DEFAULT_REFRESH_SECONDS`：默认刷新间隔
- `UP_COLOR` / `DOWN_COLOR`：涨跌颜色（默认红涨绿跌，符合 A 股习惯）
