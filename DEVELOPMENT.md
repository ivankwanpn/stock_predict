# Stock Predict — 開發文檔

## 項目概述

Stock Predict 是一個港股/美股雙軌分析平台，結合**技術指標分析**與 **DeepSeek LLM 分析**，提供買賣信號、關鍵價位、風險評估等資訊。前端使用 React + Lightweight Charts 構建交互式圖表，後端使用 FastAPI 提供 REST API。

---

## 技術棧

### 後端

| 技術 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 運行環境 |
| FastAPI | 0.104+ | Web 框架 |
| Uvicorn | 0.24+ | ASGI 服務器 |
| yfinance | 0.2.30+ | 股票數據獲取 |
| pandas | 2.0+ | 數據處理 |
| numpy | 1.24+ | 數值計算 |
| OpenAI SDK | 1.0+ | DeepSeek API 調用（OpenAI 兼容接口） |
| pydantic-settings | 2.1+ | 環境變量管理 |
| pytest | 7.4+ | 測試框架 |
| httpx | 0.25+ | 異步 HTTP 客戶端（測試用） |

### 前端

| 技術 | 版本 | 用途 |
|------|------|------|
| React | 19.2+ | UI 框架 |
| TypeScript | 6.0+ | 類型安全 |
| Vite | 8.0+ | 構建工具 |
| Tailwind CSS | 4.2+ | 樣式框架 |
| Lightweight Charts | 5.2+ | K線圖/技術指標圖表 |
| react-hot-toast | 2.6+ | 提示通知 |
| Vitest | 3.1+ | 單元測試 |
| Playwright | 1.52+ | E2E 測試 |

---

## 項目結構

```
stock_predict/
├── AGENTS.md                   # AI 代理指南
├── DEVELOPMENT.md              # 本文件
├── USER_GUIDE.md               # 用戶指南
│
├── backend/
│   ├── .env                        # 環境變量（DEEPSEEK_API_KEY 必填）
│   ├── .env.example                # 環境變量模板
│   ├── app/
│   │   ├── main.py             # FastAPI 入口，CORS 配置，路由註冊
│   │   ├── config.py            # pydantic-settings 讀取 backend/.env，驗證 DEEPSEEK_API_KEY
│   │   ├── cli.py               # CLI：python -m app.cli 0700.HK --timeframe short
│   │   ├── alert.py            # 郵件提醒：python -m app.alert [--test]
│   │   ├── core/               # 業務邏輯（無 FastAPI 依賴）
│   │   │   ├── data_fetcher.py  # yfinance 封裝 + 雙層緩存
│   │   │   ├── cache.py         # SQLite OHLCV 緩存（TTL 可配置）
│   │   │   ├── indicators.py    # ~20 個技術指標計算
│   │   │   ├── signals.py        # 加權評分 → 看多/看空/中性信號
│   │   │   ├── llm_client.py    # OpenAI 兼容客戶端調用 DeepSeek
│   │   │   ├── llm_prompts.py    # System/User prompt 構造
│   │   │   ├── llm_parser.py     # JSON 響應解析 → LLMSignal 數據類
│   │   │   ├── comparison.py    # 技術 + LLM 信號合併
│   │   │   └── watchlist_store.py # JSON 文件自選股持久化
│   │   ├── models/
│   │   │   └── schemas.py       # 所有 Pydantic 請求/響應模型
│   │   ├── routers/             # FastAPI 路由處理器
│   │   │   ├── stock.py          # GET /api/stock/{ticker}, /history, /indicators, /chart-data
│   │   │   ├── technical.py      # POST /api/technical/analyze
│   │   │   ├── llm.py            # POST /api/llm/analyze
│   │   │   ├── comparison.py     # POST /api/comparison/analyze
│   │   │   └── watchlist.py      # GET/POST /api/watchlist (add/remove/search)
│   │   └── services/            # 薄封裝層，調用 core/ 函數
│   ├── tests/                   # pytest 測試
│   ├── watchlist.json           # 默認自選股列表
│   ├── requirements.txt         # Python 依賴
│   └── .cache/                 # SQLite 緩存（自動創建）
│
└── frontend/
    ├── src/
    │   ├── api/client.ts         # Fetch 封裝，所有 API 調用，默認 30s 超時
    │   ├── App.tsx               # 主應用 — 分析流程狀態機
    │   ├── components/
    │   │   ├── StockPicker.tsx   # 股票選擇器（搜索 + 下拉）
    │   │   ├── StockChart.tsx     # K線圖 + 技術指標（Lightweight Charts v5）
    │   │   ├── WatchlistTable.tsx # 自選股表格（搜索/添加/刪除）
    │   │   ├── TechnicalCard.tsx  # 技術分析結果展示
    │   │   ├── LLMCard.tsx       # LLM 分析結果展示
    │   │   └── ComparisonView.tsx # 技術 vs LLM 對比視圖
    │   ├── i18n/
    │   │   ├── LanguageContext.tsx # 語言上下文（zh-HK / en）
    │   │   └── translations.ts   # 雙語翻譯
    │   ├── lib/
    │   │   ├── timeframeConfig.ts # 7 個時間框架配置
    │   │   ├── resample.ts        # OHLCV 重採樣（日→周/月/季/年）
    │   │   └── chartUtils.ts      # 圖表主題、指標配置、類型定義
    │   ├── types/
    │   │   └── index.ts          # TypeScript 接口（與後端 schemas 對應）
    │   └── test-setup.ts         # Vitest 測試配置
    ├── e2e/                      # Playwright E2E 測試
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts             # Vite 配置，/api 代理到 localhost:8000
    └── index.html
```

---

## 快速開始

### 1. 環境準備

```bash
# 後端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 2. 配置環境變量

```bash
# 在 backend 目錄創建 .env
cp backend/.env.example backend/.env
# 編輯 backend/.env，填入 DEEPSEEK_API_KEY（必填，否則後端無法啟動）
```

### 3. 啟動服務

```bash
# 後端（端口 8000）
cd backend
uvicorn app.main:app --reload

# 前端（端口 5173，代理 /api → localhost:8000）
cd frontend
npm run dev
```

打開 http://localhost:5173 即可使用。

### 4. 運行測試

```bash
# 後端測試
cd backend
pytest

# 前端單元測試
cd frontend
npm test

# 前端 E2E 測試（需要開發服務器運行）
cd frontend
npm run test:e2e
```

---

## API 端點

| 方法 | 路徑 | 說明 | 超時 |
|------|------|------|------|
| GET | `/api/stock/{ticker}` | 獲取股票摘要和最近30天數據 | 30s |
| GET | `/api/stock/{ticker}/history` | 獲取歷史 OHLCV 數據 | 30s |
| GET | `/api/stock/{ticker}/indicators` | 獲取所有技術指標（帶描述） | 30s |
| GET | `/api/stock/{ticker}/chart-data` | 獲取統一圖表數據（OHLCV + 指標） | 60s |
| POST | `/api/technical/analyze` | 技術指標分析 | 60s |
| POST | `/api/llm/analyze` | DeepSeek LLM 分析 | 300s |
| POST | `/api/comparison/analyze` | 技術 + LLM 對比分析 | 300s |
| GET | `/api/watchlist` | 獲取自選股列表 | 30s |
| POST | `/api/watchlist/add` | 添加自選股 | 30s |
| POST | `/api/watchlist/remove` | 移除自選股 | 30s |
| GET | `/api/watchlist/search?q=` | 搜索股票 | 30s |
| GET | `/api/health` | 健康檢查 | - |

---

## 架構設計

### 雙軌分析流程

```
用戶選擇股票 + 分析週期
        │
        ├──→ 技術指標分析 (POST /api/technical/analyze)
        │      yfinance 獲取數據 → 計算20+指標 → 加權評分 → 信號
        │
        └──→ LLM 分析 (POST /api/llm/analyze)
               yfinance 獲取數據 → 構造 prompt → DeepSeek API → 解析 JSON
                      │
                      └──→ 對比分析 (POST /api/comparison/analyze)
                             技術信號 + LLM 信號 → 共識/分歧判斷
```

### 圖表數據流

```
用戶選擇時間框架
        │
        ▼
前端計算 startDate/endDate/granularity
        │
        ▼
GET /api/stock/{ticker}/chart-data?start_date=...&end_date=...&granularity=...
        │
        ▼
後端：yfinance 獲取原始數據 → 計算指標 → 返回 { ohlcv, indicators }
        │
        ▼
前端處理：
  - 分時/5日：直接使用（分時僅取最近交易日）
  - 日線：直接使用
  - 周線/月線/季K/年K：前端 resampleOHLCV() 重採樣
```

### 分層架構

```
Router → Service → Core
  │        │         │
  │        │         └─ 純業務邏輯，無 FastAPI 依賴
  │        └─ 薄封裝層，組織調用
  └─ HTTP 處理，asyncio.to_thread() 包裝阻塞 I/O
```

### 緩存策略

- **內存緩存**：`data_fetcher.py` 內 dict，TTL 5 分鐘
- **SQLite 緩存**：`cache.py`，TTL 24 小時（可配置）
- 雙層緩存：先查內存 → 再查 SQLite → 最後請求 yfinance

---

## 圖表系統

### 時間框架配置

| 按鈕 | key | 數據範圍 | K線類型 | 粒度 | 主圖疊加 | 前端重採樣 |
|------|-----|---------|---------|------|---------|-----------|
| 分時 | intraday | 5天 | 折線 | 1h | ❌ | 僅取最近交易日 |
| 5日 | 5day | 5天 | 折線 | 1h | ❌ | 無 |
| 日線 | daily | 2年 | K線 | 1d | ✅ | 無 |
| 周線 | weekly | 5年 | K線 | 1d→周 | ✅ | resampleOHLCV |
| 月線 | monthly | 10年 | K線 | 1d→月 | ✅ | resampleOHLCV |
| 季K | quarterly | 10年 | K線 | 1d→季 | ✅ | resampleOHLCV |
| 年K | yearly | 20年 | K線 | 1d→年 | ✅ | resampleOHLCV |

### 技術指標

**主圖疊加（僅日線及以上）**：
- MA（5/10/20/60）
- EMA（5/10/20/60）
- BOLL（上/中/下軌）
- SAR（拋物線轉向）
- KC（肯特納通道）
- 一目均衡表（轉換/基準/先行A/先行B/遲行）
- VWAP（成交量加權均價）

**副圖指標（所有時間框架）**：
- 成交量（Volume）
- MACD（MACD線/信號線/柱狀圖）
- KDJ（K/D/J）
- RSI（相對強弱指數，含70/30參考線）
- ARBR（人氣/意願指標）
- CR（中間意願）
- DMA（趨向移動平均線）
- EMV（簡易波動指標）

### 圖表交互

- **十字線工具提示**：鼠標懸停顯示 OHLCV + 日期 + 漲跌幅（主圖）或指標值（副圖）
- **時間軸同步**：所有圖表（主圖 + 副圖）的時間軸聯動縮放
- **溢出安全定位**：工具提示使用 `position: fixed`，不會被父容器 `overflow: hidden` 裁剪
- **副圖獨立卡片**：每個副圖指標在獨立的深色卡片中顯示，帶標題頭

---

## 國際化

前端支持 `zh-HK`（繁體中文，默認）和 `en`（英文）。

翻譯文件：`frontend/src/i18n/translations.ts`

使用方式：`const { t } = useLang(); t('key')`

---

## 常見問題

### DEEPSEEK_API_KEY 未設置

後端啟動時會立即報錯。在 `backend/.env` 文件中設置：

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### yfinance 數據延遲

yfinance 獲取的是延遲數據，非實時行情。緩存 TTL 為 24 小時。

### 前端代理配置

Vite 開發服務器將 `/api` 請求代理到 `localhost:8000`（見 `vite.config.ts`）。生產部署需配置反向代理。

### LLM 分析超時

LLM 分析默認超時 300 秒（5 分鐘）。前端 `api/client.ts` 中 `analyzeLLM` 設置了 `timeoutMs = 300000`。