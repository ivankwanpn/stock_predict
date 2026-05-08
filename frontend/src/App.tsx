import { useRef, useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import StockPicker from './components/StockPicker';
import StockChart from './components/StockChart';
import WatchlistTable from './components/WatchlistTable';
import TechnicalCard from './components/TechnicalCard';
import LLMCard from './components/LLMCard';
import ComparisonView from './components/ComparisonView';
import { api } from './api/client';
import { useLang } from './i18n/LanguageContext';
import { getPeriodDates } from './lib/timeframeConfig';
import type { TechnicalSignal, LLMSignal, CombinedSignal, ChartDataResponse, OHLCVItem, IndicatorSet } from './types';
import type { TimeframeKey } from './lib/timeframeConfig';

type Step = 'initial' | 'technical_done' | 'llm_done';

function mapError(raw: string): string {
  if (/[\u4e00-\u9fff]/.test(raw)) return raw;
  if (raw.includes('Failed to fetch') || raw.includes('NetworkError')) {
    return '無法連接分析服務，請確認後端已啟動';
  }
  if (raw.includes('timed out') || raw.includes('Timeout') || raw.includes('AbortError')) {
    return '分析逾時，請稍後再試';
  }
  if (raw.includes('404') || raw.includes('Not Found')) return '股票代碼不存在';
  if (raw.includes('429') || raw.includes('Too Many')) return '請求過於頻繁，請稍後再試';
  if (raw.includes('500') || raw.includes('Internal Server')) return '伺服器錯誤，請稍後再試';
  if (raw.includes('503') || raw.includes('Service Unavailable')) return '服務暫時不可用，請稍後再試';
  return raw;
}

export default function App() {
  const { t, lang, setLang } = useLang();
  const [ticker, setTicker] = useState('0700.HK');
  const [timeframe, setTimeframe] = useState<'short' | 'mid' | 'long'>('short');
  const [chartTimeframe, setChartTimeframe] = useState<TimeframeKey>('daily');
  const [step, setStep] = useState<Step>('initial');
  const [techLoading, setTechLoading] = useState(false);
  const [llmLoading, setLlmLoading] = useState(false);
  const [technicalResult, setTechnicalResult] = useState<TechnicalSignal | null>(null);
  const [llmResult, setLlmResult] = useState<LLMSignal | null>(null);
  const [combinedResult, setCombinedResult] = useState<CombinedSignal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<{ ohlcv: OHLCVItem[]; indicators: IndicatorSet } | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);
  const llmAbortRef = useRef<AbortController | null>(null);

  // Fetch chart data when ticker or chart timeframe changes
  useEffect(() => {
    if (!ticker) return;
    const isHourly = chartTimeframe === 'intraday' || chartTimeframe === '5day';
    const granularity: '1h' | '1d' = isHourly ? '1h' : '1d';
    const { startDate, endDate } = getPeriodDates(chartTimeframe);
    setChartLoading(true);
    setChartError(null);
    api.getChartData(ticker, startDate, endDate, granularity)
      .then((data) => {
        const resp = data as ChartDataResponse;
        setChartData({ ohlcv: resp.ohlcv, indicators: resp.indicators });
      })
      .catch((e: Error) => {
        setChartError(e.message || 'Failed to load chart data');
      })
      .finally(() => setChartLoading(false));
  }, [ticker, chartTimeframe]);

  const runTechnicalAnalysis = async () => {
    if (llmAbortRef.current) {
      llmAbortRef.current.abort();
      llmAbortRef.current = null;
    }
    setTechLoading(true);
    setLlmLoading(false);
    setError(null);
    setStep('initial');
    setTechnicalResult(null);
    setLlmResult(null);
    setCombinedResult(null);
    try {
      const data = await api.analyzeTechnical(ticker, timeframe);
      setTechnicalResult(data as TechnicalSignal);
      setStep('technical_done');
    } catch (e: any) {
      setError(mapError(e.message));
      setTechLoading(false);
      return;
    }
    setTechLoading(false);
  };

  const runLLMAnalysis = async () => {
    if (llmAbortRef.current) {
      llmAbortRef.current.abort();
    }
    const controller = new AbortController();
    llmAbortRef.current = controller;

    setLlmLoading(true);
    setError(null);
    try {
      const data = await api.analyzeLLM(ticker, timeframe, controller.signal);
      setLlmResult(data as LLMSignal);
      const llmData = data as LLMSignal;
      if (technicalResult) {
        const agreement = technicalResult.direction === llmData.direction ? 'agree' 
          : (technicalResult.direction === 'neutral' || llmData.direction === 'neutral') ? 'partial' 
          : 'diverge';
        
        const combinedConf = agreement === 'agree'
          ? Math.min(Math.max(technicalResult.confidence, llmData.confidence) * 1.2, 100)
          : agreement === 'diverge'
            ? (technicalResult.confidence + llmData.confidence) / 2 * 0.6
            : Math.max(technicalResult.confidence, llmData.confidence);

        setCombinedResult({
          ...technicalResult,
          technical_direction: technicalResult.direction,
          llm_direction: llmData.direction,
          llm_confidence: llmData.confidence,
          llm_reasoning: llmData.reasoning || '',
          llm_risk_factors: llmData.risk_factors || [],
          agreement: agreement as 'agree' | 'diverge' | 'partial',
          combined_confidence: Math.round(combinedConf * 10) / 10,
          price_target_low: llmData.price_target_low || 0,
          price_target_high: llmData.price_target_high || 0,
          technical_score: llmData.technical_score || 0,
        } as CombinedSignal);
      }
      setStep('llm_done');
    } catch (e: any) {
      if (controller.signal.aborted) return;
      setError(mapError(e.message));
    } finally {
      if (llmAbortRef.current === controller) {
        llmAbortRef.current = null;
      }
      setLlmLoading(false);
    }
  };

  const isAnalyzing = techLoading || llmLoading;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Toaster position="top-right" />
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">{t('appTitle')}</h1>
          <p className="text-sm text-gray-400">{t('appSubtitle')}</p>
        </div>
        <button
          onClick={() => setLang(lang === 'zh-HK' ? 'en' : 'zh-HK')}
          className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-700 bg-gray-800 hover:bg-gray-700 transition-colors"
        >
          {lang === 'zh-HK' ? 'EN' : 'zh-HK'}
        </button>
      </header>

      <main className="max-w-7xl mx-auto p-6 space-y-6">
        <div className="flex gap-4 items-end flex-wrap">
          <StockPicker value={ticker} onChange={setTicker} />
          <div>
            <label className="block text-xs text-gray-400 mb-1 font-medium uppercase tracking-wider">
              {t('timeframe')}
            </label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value as 'short' | 'mid' | 'long')}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value="short">{t('short')}</option>
              <option value="mid">{t('mid')}</option>
              <option value="long">{t('long')}</option>
            </select>
          </div>
          <button
            onClick={runTechnicalAnalysis}
            disabled={techLoading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-2.5 rounded-lg font-medium text-sm transition-colors"
          >
            {techLoading ? (
              <span className="flex items-center gap-2">
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                {t('analyzing')}
              </span>
            ) : (
              t('analyze')
            )}
          </button>
          {step !== 'initial' && !techLoading && (
            <button
              onClick={runLLMAnalysis}
              disabled={llmLoading}
              className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-2.5 rounded-lg font-medium text-sm transition-colors"
            >
              {llmLoading ? (
                <span className="flex items-center gap-2">
                  <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  {t('analyzing')}
                </span>
              ) : (
                t('aiAnalysis')
              )}
            </button>
          )}
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-4 text-red-300 text-sm flex items-start gap-3">
            <svg className="w-5 h-5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 0 0 1-18 0 9 0 0 1 18 0z" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <WatchlistTable onSelect={setTicker} />

        <StockChart
          ticker={ticker}
          ohlcv={chartData?.ohlcv ?? []}
          indicators={chartData?.indicators ?? { ma: {}, ema: {}, bb: {}, sar: [], kc: {}, ichimoku: {}, vwap: [], macd: {}, kdj: {}, arbr: {}, cr: [], dma: {}, emv: [], rsi: [] } as IndicatorSet}
          timeframe={chartTimeframe}
          loading={chartLoading}
          error={chartError}
          onTimeframeChange={setChartTimeframe}
        />

        {technicalResult && (
          <TechnicalCard signal={technicalResult} />
        )}

        {(techLoading && !technicalResult) && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden animate-pulse">
            <div className="px-5 py-3 border-b border-gray-800">
              <div className="h-4 w-24 bg-gray-800 rounded" />
            </div>
            <div className="p-5 space-y-4">
              <div className="h-2 bg-gray-800 rounded-full w-full" />
              <div className="grid grid-cols-2 gap-4">
                <div className="h-16 bg-gray-800 rounded-lg" />
                <div className="h-16 bg-gray-800 rounded-lg" />
              </div>
              <div className="space-y-2">
                <div className="h-3 bg-gray-800 rounded w-3/4" />
                <div className="h-3 bg-gray-800 rounded w-1/2" />
              </div>
            </div>
          </div>
        )}

        {technicalResult && (
          <>
            {(llmLoading && !llmResult) && (
              <div className="w-full">
                <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden animate-pulse">
                  <div className="px-5 py-3 border-b border-gray-800">
                    <div className="h-4 w-20 bg-gray-800 rounded" />
                  </div>
                  <div className="p-5 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="h-20 bg-gray-800 rounded-lg" />
                      <div className="h-20 bg-gray-800 rounded-lg" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="h-16 bg-gray-800 rounded-lg" />
                      <div className="h-16 bg-gray-800 rounded-lg" />
                    </div>
                    <div className="space-y-2">
                      <div className="h-3 bg-gray-800 rounded w-full" />
                      <div className="h-3 bg-gray-800 rounded w-5/6" />
                      <div className="h-3 bg-gray-800 rounded w-4/6" />
                    </div>
                  </div>
                </div>
              </div>
            )}
            {llmResult && (
              <div className="w-full">
                <LLMCard signal={llmResult} />
              </div>
            )}
          </>
        )}

        {combinedResult && (
          <ComparisonView result={combinedResult} />
        )}

        {!technicalResult && !error && !isAnalyzing && (
          <div className="flex flex-col items-center justify-center py-20 text-gray-600">
            <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <p className="text-lg font-medium mb-1">{t('selectStock')}</p>
            <p className="text-sm">{t('selectStockHint')}</p>
          </div>
        )}
      </main>
    </div>
  );
}
