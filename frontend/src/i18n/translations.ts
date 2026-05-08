export const translations: Record<string, Record<string, string>> = {
  'zh-HK': {
    // App
    appTitle: 'Stock Predict — 雙軌分析',
    appSubtitle: '技術指標 + DeepSeek LLM · 港股美股',
    analyze: '技術分析',
    aiAnalysis: 'AI 大模型分析',
    analyzing: '分析中...',
    // Controls
    stock: '股票',
    timeframe: '分析週期',
    short: '短線 (1-5日)',
    mid: '中線 (1-4週)',
    long: '長線 (1-3月)',

    // Selection
    selectStock: '選擇股票並執行分析',
    selectStockHint: '在上方選擇股票代碼，點擊「技術分析」查看信號',
    searchStock: '搜尋股票代碼或名稱...',
    pressEnterToUse: '按 Enter 使用:',
    noResults: '無結果',

    // Watchlist
    loadingWatchlist: '正在載入自選股...',
    watchlistUnavailable: '自選股無法使用 — 後端可能離線',
    noWatchlistData: '暫無自選股數據',
    watchlistTitle: '自選股',
    tickerCol: '代碼',
    nameCol: '名稱',
    priceCol: '價格',
    changeCol: '變動',
    addStock: '新增',
    removeStock: '移除',
    searchWatchlist: '搜尋股票代碼或名稱...',
    addStockPlaceholder: '輸入代碼，如 0700.HK',
    stockAdded: '已加入自選股',
    stockRemoved: '已從自選股移除',
    stockAlreadyExists: '此股票已在自選股中',
    stockNotFound: '找不到此股票',
    addStockFailed: '新增失敗，請重試',
    removeStockFailed: '移除失敗，請重試',
    emptyWatchlist: '尚未加入任何自選股',
    emptyWatchlistHint: '在上方搜尋欄輸入股票代碼，點擊「新增」加入自選股',
    retry: '重試',

    // Direction / Agreement badges
    bullish: '看多',
    bearish: '看空',
    neutral: '中性',
    agree: '一致',
    diverge: '分歧',
    partial: '部分一致',

    // Technical Card
    technicalAnalysis: '技術分析',
    confidence: '信心度',
    support: '支持位',
    resistance: '阻力位',
    summary: '總結',
    indicatorDetails: '指標詳情',

    // LLM Card
    llmAnalysis: 'DeepSeek LLM 分析',
    technicalScore: '技術評分',
    targetLow: '目標低位',
    targetHigh: '目標高位',
    keyLevels: '關鍵價位',
    reasoning: '推理分析',

    comparison: '技術 vs LLM 比較',
    technicalConfidence: '技術信心度',
    llmConfidence: 'LLM 信心度',
    combinedConfidence: '綜合信心度',
    priceTargetRange: '目標價格範圍',
    low: '低',
    high: '高',
    current: '現價',
    technicalDirection: '技術方向',
    llmDirection: 'LLM 方向',
    llmRiskFactors: 'LLM 風險因素',
    llmReasoning: 'LLM 推理分析',
    // Chart timeframes
    tfIntraday: '分時',
    tf5day: '5日',
    tfDaily: '日線',
    tfWeekly: '周線',
    tfMonthly: '月線',
    tfQuarterly: '季K',
    tfYearly: '年K',

    // Chart labels
    chartTitle: '走勢圖',
    overlayIndicators: '主圖指標',
    subIndicators: '副圖指標',
    loadingChart: '載入圖表中...',
    chartUnavailable: '圖表無法使用',

    // Indicator labels
    indMA: 'MA',
    indEMA: 'EMA',
    indBOLL: 'BOLL',
    indSAR: 'SAR',
    indKC: 'KC',
    indIchimoku: '一目',
    indVWAP: 'VWAP',
    indVolume: '成交量',
    indMACD: 'MACD',
    indKDJ: 'KDJ',
    indARBR: 'ARBR',
    indCR: 'CR',
    indDMA: 'DMA',
    indEMV: 'EMV',
    indRSI: 'RSI',

    // Tooltip labels
    tooltipDate: '日期',
    tooltipOpen: '開',
    tooltipHigh: '高',
    tooltipLow: '低',
    tooltipClose: '收',
    tooltipVolume: '量',
    tooltipChange: '漲跌',
  },

  'en': {
    // App
    appTitle: 'Stock Predict — Dual-Track Analysis',
    appSubtitle: 'Technical + DeepSeek LLM · HK & US Stocks',
    analyze: 'Technical Analysis',
    aiAnalysis: 'AI LLM Analysis',
    analyzing: 'Analyzing...',

    // Controls
    stock: 'Stock',
    timeframe: 'Analysis Period',
    short: 'Short (1-5d)',
    mid: 'Mid (1-4w)',
    long: 'Long (1-3m)',

    // Selection
    selectStock: 'Select a stock and run analysis',
    selectStockHint: 'Choose a ticker above and click "Technical Analysis" to see signals',
    searchStock: 'Search ticker or name...',
    pressEnterToUse: 'Press Enter to use:',
    noResults: 'No results',

    // Watchlist
    loadingWatchlist: 'Loading watchlist...',
    watchlistUnavailable: 'Watchlist unavailable — backend may be offline',
    noWatchlistData: 'No watchlist data available',
    watchlistTitle: 'Watchlist',
    tickerCol: 'Ticker',
    nameCol: 'Name',
    priceCol: 'Price',
    changeCol: 'Change',
    addStock: 'Add',
    removeStock: 'Remove',
    searchWatchlist: 'Search ticker or name...',
    addStockPlaceholder: 'Enter ticker, e.g. AAPL',
    stockAdded: 'Added to watchlist',
    stockRemoved: 'Removed from watchlist',
    stockAlreadyExists: 'Stock already in watchlist',
    stockNotFound: 'Stock not found',
    addStockFailed: 'Failed to add, please retry',
    removeStockFailed: 'Failed to remove, please retry',
    emptyWatchlist: 'No stocks in your watchlist yet',
    emptyWatchlistHint: 'Search for a stock ticker above and click "Add" to get started',
    retry: 'Retry',

    // Direction / Agreement badges
    bullish: 'Bullish',
    bearish: 'Bearish',
    neutral: 'Neutral',
    agree: 'Agree',
    diverge: 'Diverge',
    partial: 'Partial',

    // Technical Card
    technicalAnalysis: 'Technical Analysis',
    confidence: 'Confidence',
    support: 'Support',
    resistance: 'Resistance',
    summary: 'Summary',
    indicatorDetails: 'Indicator Details',

    // LLM Card
    llmAnalysis: 'DeepSeek LLM Analysis',
    technicalScore: 'Technical Score',
    targetLow: 'Target Low',
    targetHigh: 'Target High',
    keyLevels: 'Key Levels',
    reasoning: 'Reasoning',
    riskFactors: 'Risk Factors',

    // Comparison View
    comparison: 'Technical vs LLM Comparison',
    technicalConfidence: 'Technical Confidence',
    llmConfidence: 'LLM Confidence',
    combinedConfidence: 'Combined Confidence',
    priceTargetRange: 'Price Target Range',
    low: 'Low',
    high: 'High',
    current: 'Current',
    technicalDirection: 'Technical Direction',
    llmDirection: 'LLM Direction',
    llmRiskFactors: 'LLM Risk Factors',
    llmReasoning: 'LLM Reasoning',
    score: 'Score',

    // Chart timeframes
    tfIntraday: 'Intraday',
    tf5day: '5 Day',
    tfDaily: 'Daily',
    tfWeekly: 'Weekly',
    tfMonthly: 'Monthly',
    tfQuarterly: 'Quarterly',
    tfYearly: 'Yearly',

    // Chart labels
    chartTitle: 'Chart',
    overlayIndicators: 'Overlay',
    subIndicators: 'Sub-chart',
    loadingChart: 'Loading chart...',
    chartUnavailable: 'Chart unavailable',

    // Indicator labels
    indMA: 'MA',
    indEMA: 'EMA',
    indBOLL: 'BOLL',
    indSAR: 'SAR',
    indKC: 'KC',
    indIchimoku: 'Ichimoku',
    indVWAP: 'VWAP',
    indVolume: 'Volume',
    indMACD: 'MACD',
    indKDJ: 'KDJ',
    indARBR: 'ARBR',
    indCR: 'CR',
    indDMA: 'DMA',
    indEMV: 'EMV',
    indRSI: 'RSI',

    // Tooltip labels
    tooltipDate: 'Date',
    tooltipOpen: 'Open',
    tooltipHigh: 'High',
    tooltipLow: 'Low',
    tooltipClose: 'Close',
    tooltipVolume: 'Vol',
    tooltipChange: 'Chg',
  },
};

export type Lang = 'zh-HK' | 'en';
