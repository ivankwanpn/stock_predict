import { useLang } from '../i18n/LanguageContext';
import type { CombinedSignal } from '../types';

interface ComparisonViewProps {
  result: CombinedSignal;
}

function AgreementBadge({ agreement }: { agreement: string }) {
  const { t } = useLang();
  switch (agreement) {
    case 'agree':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold bg-green-900/40 text-green-400 border border-green-700/50">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
          {t('agree')}
        </span>
      );
    case 'diverge':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold bg-red-900/40 text-red-400 border border-red-700/50">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
          </svg>
          {t('diverge')}
        </span>
      );
    case 'partial':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold bg-yellow-900/40 text-yellow-400 border border-yellow-700/50">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M7 17l5-5-5-5m7 10l5-5-5-5" />
          </svg>
          {t('partial')}
        </span>
      );
    default:
      return null;
  }
}

function Gauge({ value, label }: { value: number; label: string }) {
  const pct = value == null ? 0 : Math.min(100, Math.max(0, value));
  const circumference = 2 * Math.PI * 36;
  const offset = circumference - (pct / 100) * circumference;

  let strokeColor = '#22c55e';
  if (pct < 40) strokeColor = '#ef4444';
  else if (pct < 70) strokeColor = '#eab308';

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-24 h-24">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="36" fill="none" stroke="#1f2937" strokeWidth="6" />
          <circle
            cx="40"
            cy="40"
            r="36"
            fill="none"
            stroke={strokeColor}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold font-mono text-gray-100">{pct.toFixed(0)}%</span>
        </div>
      </div>
      <span className="text-xs text-gray-500 mt-1">{label}</span>
    </div>
  );
}

export default function ComparisonView({ result }: ComparisonViewProps) {
  const { t } = useLang();

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          {t('comparison')}
        </h2>
        <AgreementBadge agreement={result.agreement} />
      </div>

      <div className="p-5">
        <div className="flex items-start justify-between flex-wrap gap-6">
          {/* Gauges */}
          <div className="flex gap-10">
            <Gauge value={result.confidence} label={t('technicalConfidence')} />
            <Gauge value={result.llm_confidence} label={t('llmConfidence')} />
            <Gauge value={result.combined_confidence} label={t('combinedConfidence')} />
          </div>

          {/* Price Target Range */}
          <div className="bg-gray-800/50 rounded-lg p-4 min-w-48">
            <span className="text-xs text-gray-500 block mb-2 font-medium uppercase tracking-wider">
              {t('priceTargetRange')}
            </span>
            <div className="flex items-center gap-3">
              <div className="text-center">
                <span className="text-xs text-gray-500 block">{t('low')}</span>
                <span className="text-lg font-mono font-bold text-orange-400">
                  {result.price_target_low?.toFixed(2)}
                </span>
              </div>
              <div className="flex-1 h-1 bg-gray-700 rounded-full relative mx-1 mt-3">
                <div
                  className="absolute h-2 w-2 bg-blue-400 rounded-full -translate-y-1/2 top-1/2"
                  style={{
                    left: (() => {
                      const fallbackPrice = (result.key_support + result.key_resistance) / 2;
                      const range = result.price_target_high - result.price_target_low;
                      const pos = range > 0 ? ((fallbackPrice - result.price_target_low) / range) * 100 : 50;
                      return `${Math.min(90, Math.max(10, pos))}%`;
                    })(),
                  }}
                  title={t('current')}
                />
              </div>
              <div className="text-center">
                <span className="text-xs text-gray-500 block">{t('high')}</span>
                <span className="text-lg font-mono font-bold text-emerald-400">
                  {result.price_target_high?.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Direction comparison */}
        <div className="mt-6 grid grid-cols-2 gap-6">
          <div className="bg-gray-800/30 rounded-lg p-4">
            <span className="text-xs text-gray-500 font-medium block mb-2">{t('technicalDirection')}</span>
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${
                  result.technical_direction === 'bullish'
                    ? 'bg-green-900/40 text-green-400 border-green-700/50'
                    : result.technical_direction === 'bearish'
                      ? 'bg-red-900/40 text-red-400 border-red-700/50'
                      : 'bg-gray-800 text-gray-400 border-gray-600/50'
                }`}
              >
                {result.technical_direction.toUpperCase()}
              </span>
              <span className="text-xs text-gray-500 font-mono">{t('score')}: {(result.technical_score || 0).toFixed(0)}</span>
            </div>
          </div>
          <div className="bg-gray-800/30 rounded-lg p-4">
            <span className="text-xs text-gray-500 font-medium block mb-2">{t('llmDirection')}</span>
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${
                  result.llm_direction === 'bullish'
                    ? 'bg-green-900/40 text-green-400 border-green-700/50'
                    : result.llm_direction === 'bearish'
                      ? 'bg-red-900/40 text-red-400 border-red-700/50'
                      : 'bg-gray-800 text-gray-400 border-gray-600/50'
                }`}
              >
                {result.llm_direction.toUpperCase()}
              </span>
              <span className="text-xs text-gray-500 font-mono">{t('score')}: {(result.llm_confidence || 0).toFixed(0)}</span>
            </div>
          </div>
        </div>

        {/* LLM Risk Factors Summary */}
        {result.llm_risk_factors && result.llm_risk_factors.length > 0 && (
          <div className="mt-5">
            <span className="text-xs text-gray-500 font-medium block mb-2">{t('llmRiskFactors')}</span>
            <div className="flex flex-wrap gap-2">
              {result.llm_risk_factors.map((risk: any, i: number) => {
                const text = typeof risk === 'string' ? risk : (risk?.factor || risk?.description || JSON.stringify(risk));
                const severity = typeof risk === 'object' ? risk?.severity : null;
                const severityColor = severity === 'high' ? 'border-red-700/40 text-red-400 bg-red-900/30' :
                                     severity === 'medium' ? 'border-yellow-700/40 text-yellow-400 bg-yellow-900/30' :
                                     'border-yellow-700/40 text-yellow-400 bg-yellow-900/30';
                return (
                <span
                  key={i}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs ${severityColor}`}
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  {severity && <span className="font-semibold">{severity.toUpperCase()}</span>}
                  {text}
                </span>
                );
              })}
            </div>
          </div>
        )}

        {/* LLM Reasoning */}
        {result.llm_reasoning && (
          <div className="mt-5">
            <span className="text-xs text-gray-500 font-medium block mb-1">{t('llmReasoning')}</span>
            <p className="text-sm text-gray-300 leading-relaxed bg-gray-800/20 rounded-lg p-3 border border-gray-800">
              {result.llm_reasoning}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
