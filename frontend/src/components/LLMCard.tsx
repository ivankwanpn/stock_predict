import { useLang } from '../i18n/LanguageContext';
import type { LLMSignal, KeyLevel, RiskFactor, Scenario, ScoreBreakdown } from '../types';
import DirectionBadge from './DirectionBadge';
import ConfidenceBar from './ConfidenceBar';

interface LLMCardProps {
  signal: LLMSignal;
}

function KeyLevelsList({ levels }: { levels: KeyLevel[] }) {
  const { t } = useLang();
  if (!levels || levels.length === 0) return null;

  const strengthColors: Record<string, string> = {
    strong: 'text-green-400',
    moderate: 'text-yellow-400',
    weak: 'text-gray-400',
  };

  const typeIcons: Record<string, string> = {
    support: '↑',
    resistance: '↓',
    pivot: '◆',
  };

  return (
    <div>
      <span className="text-xs text-gray-500 font-medium block mb-2">{t('keyLevels')}</span>
      <div className="space-y-1.5">
        {levels.map((level, i) => (
          <div key={i} className="flex items-center justify-between bg-gray-800/30 rounded-lg px-3 py-2">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <span className="text-xs text-gray-500 shrink-0">{typeIcons[level.type] || '•'}</span>
              <span className="text-xs text-gray-300 truncate">{level.rationale}</span>
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-2">
              <span className={`text-xs ${strengthColors[level.strength] || 'text-gray-400'}`}>
                {level.strength}
              </span>
              <span className="text-xs font-mono text-gray-200 font-medium">
                {typeof level.price === 'number' ? level.price.toFixed(2) : '—'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RiskFactorsList({ factors }: { factors: RiskFactor[] }) {
  if (!factors || factors.length === 0) return null;

  const severityColors: Record<string, string> = {
    high: 'bg-red-900/30 text-red-400 border-red-700/40',
    medium: 'bg-yellow-900/30 text-yellow-400 border-yellow-700/40',
    low: 'bg-blue-900/30 text-blue-400 border-blue-700/40',
  };

  const severityIcons: Record<string, string> = {
    high: '⚠',
    medium: '⚠',
    low: 'ℹ',
  };

  return (
    <div>
      <span className="text-xs text-gray-500 font-medium block mb-2">Risk Factors</span>
      <div className="flex flex-wrap gap-2">
        {factors.map((risk, i) => {
          const sev = typeof risk === 'string' ? 'medium' : risk.severity;
          const text = typeof risk === 'string' ? risk : risk.factor;
          return (
            <span
              key={i}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border ${severityColors[sev] || severityColors.medium}`}
            >
              {severityIcons[sev] || ''} {text}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function ScenarioBlock({ scenario, type }: { scenario: Scenario | null; type: 'bullish' | 'bearish' }) {
  if (!scenario) return null;

  const colors = type === 'bullish'
    ? { bg: 'bg-green-900/20', border: 'border-green-700/30', text: 'text-green-400', muted: 'text-green-300' }
    : { bg: 'bg-red-900/20', border: 'border-red-700/30', text: 'text-red-400', muted: 'text-red-300' };

  const label = type === 'bullish' ? 'Bullish Scenario' : 'Bearish Scenario';

  return (
    <div className={`${colors.bg} border ${colors.border} rounded-lg p-3`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs font-semibold ${colors.text}`}>{label}</span>
        <span className="text-xs font-mono text-gray-400">
          Probability: {typeof scenario.probability === 'number' ? scenario.probability.toFixed(0) : '—'}%
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 mb-2">
        <div>
          <span className="text-xs text-gray-500 block">Trigger</span>
          <span className={`text-sm font-mono font-semibold ${colors.text}`}>
            {typeof scenario.trigger_price === 'number' ? scenario.trigger_price.toFixed(2) : '—'}
          </span>
        </div>
        <div>
          <span className="text-xs text-gray-500 block">Target</span>
          <span className={`text-sm font-mono font-semibold ${colors.text}`}>
            {typeof scenario.target_price === 'number' ? scenario.target_price.toFixed(2) : '—'}
          </span>
        </div>
      </div>
      <p className="text-xs text-gray-300 leading-relaxed">{scenario.narrative}</p>
    </div>
  );
}

function ScoreBreakdownChart({ breakdown }: { breakdown: ScoreBreakdown | null }) {
  if (!breakdown) return null;

  const items = Object.entries(breakdown)
    .filter(([, v]) => typeof v === 'number')
    .map(([key, val]) => ({
      label: key.charAt(0).toUpperCase() + key.slice(1),
      value: val as number,
    }));
  const total = items.reduce((s, i) => s + i.value, 0);

  const categoryColors: Record<string, string> = {
    trend: 'bg-blue-500',
    momentum: 'bg-purple-500',
    volume: 'bg-orange-500',
    oscillators: 'bg-pink-500',
    ichimoku: 'bg-teal-500',
    sar: 'bg-cyan-500',
  };

  return (
    <div>
      <span className="text-xs text-gray-500 font-medium block mb-2">Score Breakdown</span>
      <div className="bg-gray-800/30 rounded-lg p-3">
        <div className="flex h-4 rounded-full overflow-hidden mb-3">
          {items.map((item) => (
            <div
              key={item.label}
              className={`${categoryColors[item.label.toLowerCase()] || 'bg-gray-500'}`}
              style={{ width: `${total > 0 ? (item.value / total) * 100 : 0}%` }}
              title={`${item.label}: ${item.value}`}
            />
          ))}
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {items.map((item) => (
            <div key={item.label} className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${categoryColors[item.label.toLowerCase()] || 'bg-gray-500'}`} />
                <span className="text-xs text-gray-400">{item.label}</span>
              </div>
              <span className="text-xs font-mono text-gray-300">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AnalysisSection({ title, content }: { title: string; content: string }) {
  if (!content) return null;
  return (
    <div>
      <span className="text-xs text-gray-500 font-medium block mb-1">{title}</span>
      <p className="text-sm text-gray-300 leading-relaxed">{content}</p>
    </div>
  );
}

export default function LLMCard({ signal }: LLMCardProps) {
  const { t } = useLang();

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          {t('llmAnalysis')}
        </h2>
        <DirectionBadge direction={signal.direction} />
      </div>

      <div className="p-5 space-y-5">
        {/* Confidence & Technical Score */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-gray-400 font-medium">{t('confidence')}</span>
            </div>
            <ConfidenceBar value={signal.confidence} color="bg-purple-500" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-gray-400 font-medium">{t('technicalScore')}</span>
              <span className="text-xs font-mono text-gray-500">
                {(signal.technical_score || 0).toFixed(0)}/100
              </span>
            </div>
            <ConfidenceBar value={signal.technical_score} color="bg-indigo-500" />
          </div>
        </div>

        {/* Price Targets */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-800/50 rounded-lg p-3">
            <span className="text-xs text-gray-500 block mb-0.5">{t('targetLow')}</span>
            <span className="text-lg font-mono font-semibold text-orange-400">
              {signal.price_target_low?.toFixed(2)}
            </span>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <span className="text-xs text-gray-500 block mb-0.5">{t('targetHigh')}</span>
            <span className="text-lg font-mono font-semibold text-emerald-400">
              {signal.price_target_high?.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Key Levels */}
        <KeyLevelsList levels={signal.key_levels} />

        {/* Trend Analysis */}
        {signal.trend_analysis && (
          <AnalysisSection title="Trend Analysis" content={signal.trend_analysis} />
        )}

        {/* Momentum Analysis */}
        {signal.momentum_analysis && (
          <AnalysisSection title="Momentum Analysis" content={signal.momentum_analysis} />
        )}

        {/* Volume Analysis */}
        {signal.volume_analysis && (
          <AnalysisSection title="Volume Analysis" content={signal.volume_analysis} />
        )}

        {/* Oscillator Composite */}
        {signal.oscillator_composite && (
          <AnalysisSection title="Oscillator Composite" content={signal.oscillator_composite} />
        )}

        {/* Scenarios */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <ScenarioBlock scenario={signal.scenario_bullish} type="bullish" />
          <ScenarioBlock scenario={signal.scenario_bearish} type="bearish" />
        </div>

        {/* Score Breakdown */}
        <ScoreBreakdownChart breakdown={signal.score_breakdown} />

        {/* Risk Factors */}
        <RiskFactorsList factors={signal.risk_factors} />

        {/* Reasoning */}
        {signal.reasoning && (
          <div>
            <span className="text-xs text-gray-500 font-medium block mb-1">{t('reasoning')}</span>
            <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-line">{signal.reasoning}</p>
          </div>
        )}
      </div>
    </div>
  );
}
