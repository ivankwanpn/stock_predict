import { useLang } from '../i18n/LanguageContext';
import type { TechnicalSignal } from '../types';
import DirectionBadge from './DirectionBadge';
import ConfidenceBar from './ConfidenceBar';

interface TechnicalCardProps {
  signal: TechnicalSignal;
}

type IndicatorDetails = Record<string, unknown>;

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-xs text-gray-500 font-medium block mb-2">
      {children}
    </span>
  );
}

function PriceIndicator({ label, value }: { label: string; value: string }) {
  const isAbove = value === 'above';
  return (
    <div className="flex items-center justify-between bg-gray-800/30 rounded-lg px-3 py-1.5">
      <span className="text-xs text-gray-400">{label}</span>
      <span className={`text-xs font-semibold ${isAbove ? 'text-green-400' : 'text-red-400'}`}>
        {isAbove ? '↑ above' : '↓ below'}
      </span>
    </div>
  );
}

function NumericIndicator({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between bg-gray-800/30 rounded-lg px-3 py-1.5">
      <span className="text-xs text-gray-400">{label}</span>
      <span className="text-xs font-mono text-gray-200">{value.toFixed(2)}</span>
    </div>
  );
}

function OscillatorCompositeBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  const color = pct < 40 ? 'bg-red-500' : pct < 70 ? 'bg-yellow-500' : 'bg-green-500';
  return (
    <div className="bg-gray-800/30 rounded-lg px-3 py-2">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-gray-400">Oscillator Composite</span>
        <span className="text-xs font-mono text-gray-200">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function TrendIndicator({ label, value }: { label: string; value: string }) {
  const isBullish = value === 'bullish';
  return (
    <div className="flex items-center justify-between bg-gray-800/30 rounded-lg px-3 py-1.5">
      <span className="text-xs text-gray-400">{label}</span>
      <span className={`text-xs font-semibold ${isBullish ? 'text-green-400' : 'text-red-400'}`}>
        {isBullish ? '↑ bullish' : '↓ bearish'}
      </span>
    </div>
  );
}

function OBVTrendIndicator({ label, value }: { label: string; value: string }) {
  const isRising = value === 'rising';
  return (
    <div className="flex items-center justify-between bg-gray-800/30 rounded-lg px-3 py-1.5">
      <span className="text-xs text-gray-400">{label}</span>
      <span className={`text-xs font-semibold ${isRising ? 'text-green-400' : 'text-red-400'}`}>
        {isRising ? '↑ rising' : '↓ falling'}
      </span>
    </div>
  );
}

export default function TechnicalCard({ signal }: TechnicalCardProps) {
  const { t } = useLang();
  const details = signal.indicator_details as IndicatorDetails;

  const oscillators: Array<[string, unknown]> = [
    ['RSI (14)', details.rsi],
    ['KD %K', details.kd_k],
    ['CCI', details.cci],
    ['Williams %R', details.wr],
    ['Oscillator Composite', details.oscillator_composite],
  ];

  const trend: Array<[string, unknown]> = [
    ['Price vs MA 5', details.price_vs_MA_5],
    ['Price vs MA 10', details.price_vs_MA_10],
    ['Price vs MA 20', details.price_vs_MA_20],
    ['Price vs MA 60', details.price_vs_MA_60],
    ['Price vs EMA 5', details.price_vs_EMA_5],
    ['Price vs EMA 10', details.price_vs_EMA_10],
    ['Price vs EMA 20', details.price_vs_EMA_20],
    ['Price vs EMA 60', details.price_vs_EMA_60],
    ['MACD', details.macd],
  ];

  const momentum: Array<[string, unknown]> = [
    ['ADX', details.adx],
    ['ADX Filter', details.adx_filter],
    ['Ichimoku Tenkan/Kijun', details.ichimoku_tenkan_kijun],
    ['Price vs SAR', details.price_vs_sar],
  ];

  const volatility: Array<[string, unknown]> = [
    ['Bollinger Position', details.bb_position],
    ['Bollinger Bandwidth', details.bb_bandwidth],
  ];

  const volume: Array<[string, unknown]> = [
    ['EMV', details.emv],
    ['OBV Trend', details.obv_trend],
    ['Price vs VWAP', details.price_vs_vwap],
  ];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          {t('technicalAnalysis')}
        </h2>
        <DirectionBadge direction={signal.direction} />
      </div>

      <div className="p-5 space-y-5">
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-gray-400 font-medium">{t('confidence')}</span>
          </div>
          <ConfidenceBar value={signal.confidence} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-gray-800/50 rounded-lg p-3">
            <span className="text-xs text-gray-500 block mb-0.5">{t('support')}</span>
            <span className="text-lg font-mono font-semibold text-green-400">
              {signal.key_support.toFixed(2)}
            </span>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <span className="text-xs text-gray-500 block mb-0.5">{t('resistance')}</span>
            <span className="text-lg font-mono font-semibold text-red-400">
              {signal.key_resistance.toFixed(2)}
            </span>
          </div>
        </div>

        <div>
          <SectionLabel>Oscillators</SectionLabel>
          <div className="space-y-1.5">
            {oscillators.map(([label, value]) => {
              if (label === 'Oscillator Composite' && typeof value === 'number') {
                return <OscillatorCompositeBar key={label} value={value} />;
              }
              if (typeof value === 'number') {
                return <NumericIndicator key={label} label={label} value={value} />;
              }
              return null;
            })}
          </div>
        </div>

        <div>
          <SectionLabel>Trend</SectionLabel>
          <div className="space-y-1.5">
            {trend.map(([label, value]) => {
              if (typeof value === 'string') {
                return <PriceIndicator key={label} label={label} value={value} />;
              }
              return null;
            })}
          </div>
        </div>

        <div>
          <SectionLabel>Momentum</SectionLabel>
          <div className="space-y-1.5">
            {momentum.map(([label, value]) => {
              if (label === 'ADX' && typeof value === 'number') {
                return <NumericIndicator key={label} label={label} value={value} />;
              }
              if (label === 'ADX Filter' && typeof value === 'string') {
                return (
                  <div key={label} className="flex items-center justify-between bg-gray-800/30 rounded-lg px-3 py-1.5">
                    <span className="text-xs text-gray-400">{label}</span>
                    <span className="text-xs text-yellow-400">{value}</span>
                  </div>
                );
              }
              if (label === 'Ichimoku Tenkan/Kijun' && typeof value === 'string') {
                return <TrendIndicator key={label} label={label} value={value} />;
              }
              if (label === 'Price vs SAR' && typeof value === 'string') {
                return <PriceIndicator key={label} label={label} value={value} />;
              }
              return null;
            })}
          </div>
        </div>

        <div>
          <SectionLabel>Volatility</SectionLabel>
          <div className="space-y-1.5">
            {volatility.map(([label, value]) => {
              if (typeof value === 'number') {
                return <NumericIndicator key={label} label={label} value={value} />;
              }
              return null;
            })}
          </div>
        </div>

        <div>
          <SectionLabel>Volume</SectionLabel>
          <div className="space-y-1.5">
            {volume.map(([label, value]) => {
              if (label === 'EMV' && typeof value === 'number') {
                return <NumericIndicator key={label} label={label} value={value} />;
              }
              if (label === 'OBV Trend' && typeof value === 'string') {
                return <OBVTrendIndicator key={label} label={label} value={value} />;
              }
              if (label === 'Price vs VWAP' && typeof value === 'string') {
                return <PriceIndicator key={label} label={label} value={value} />;
              }
              return null;
            })}
          </div>
        </div>

        {signal.summary && (
          <div>
            <span className="text-xs text-gray-500 font-medium block mb-1">{t('summary')}</span>
            <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-line">{signal.summary}</p>
          </div>
        )}
      </div>
    </div>
  );
}