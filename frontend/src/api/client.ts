const BASE = '/api';

async function request<T>(url: string, options?: RequestInit, timeoutMs = 30000, externalSignal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  if (externalSignal) {
    if (externalSignal.aborted) {
      clearTimeout(timeoutId);
      throw new DOMException('The operation was aborted', 'AbortError');
    }
    externalSignal.addEventListener('abort', () => controller.abort(), { once: true });
  }

  try {
    const res = await fetch(`${BASE}${url}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...options,
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || `HTTP ${res.status}`);
    }
    return res.json() as Promise<T>;
  } catch (e: any) {
    clearTimeout(timeoutId);
    if (e.name === 'AbortError') {
      if (externalSignal?.aborted) throw e;
      throw new Error('Request timed out');
    }

    if (e.message?.includes('Failed to fetch')) {
      throw new Error('無法連接分析服務，請確認後端已啟動');
    }

    if (e.message?.startsWith('HTTP 404') || e.message?.includes('404')) {
      throw new Error('股票代碼不存在');
    }
    if (e.message?.startsWith('HTTP 429') || e.message?.includes('429')) {
      throw new Error('請求過於頻繁，請稍後再試');
    }
    if (e.message?.startsWith('HTTP 500') || e.message?.includes('500')) {
      throw new Error('伺服器錯誤，請稍後再試');
    }
    if (e.message?.startsWith('HTTP 503') || e.message?.includes('503')) {
      throw new Error('服務暫時不可用，請稍後再試');
    }

    throw e;
  }
}

export const api = {
  analyzeTechnical: (ticker: string, timeframe = 'short') =>
    request('/technical/analyze', {
      method: 'POST',
      body: JSON.stringify({ ticker, timeframe }),
    }, 60000),

  analyzeLLM: (ticker: string, timeframe = 'short', signal?: AbortSignal) =>
    request('/llm/analyze', {
      method: 'POST',
      body: JSON.stringify({ ticker, timeframe }),
    }, 300000, signal),

  analyzeCombined: (ticker: string, timeframe = 'short') =>
    request('/comparison/analyze', {
      method: 'POST',
      body: JSON.stringify({ ticker, timeframe }),
    }, 300000),

  getWatchlist: () => request('/watchlist'),

  addWatchlist: (ticker: string) =>
    request('/watchlist/add', {
      method: 'POST',
      body: JSON.stringify({ ticker }),
    }),

  removeWatchlist: (ticker: string) =>
    request('/watchlist/remove', {
      method: 'POST',
      body: JSON.stringify({ ticker }),
    }),

  searchStocks: (q: string) =>
    request(`/watchlist/search?q=${encodeURIComponent(q)}`),

  getChartData: (ticker: string, startDate: string, endDate: string, granularity: '1h' | '1d') =>
    request(`/stock/${ticker}/chart-data?start_date=${startDate}&end_date=${endDate}&granularity=${granularity}`, undefined, 60000),
};
