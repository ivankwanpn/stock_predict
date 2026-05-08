import { useLang } from '../i18n/LanguageContext';

interface DirectionBadgeProps {
  direction: string;
}

export default function DirectionBadge({ direction }: DirectionBadgeProps) {
  const { t } = useLang();
  const colors: Record<string, string> = {
    bullish: 'bg-green-900/40 text-green-400 border-green-700/50',
    bearish: 'bg-red-900/40 text-red-400 border-red-700/50',
    neutral: 'bg-gray-800 text-gray-400 border-gray-600/50',
  };
  const icons: Record<string, string> = {
    bullish: '↑',
    bearish: '↓',
    neutral: '→',
  };
  const labels: Record<string, string> = {
    bullish: t('bullish'),
    bearish: t('bearish'),
    neutral: t('neutral'),
  };
  const c = colors[direction] || colors.neutral;
  const label = direction ? (labels[direction] || direction.toUpperCase()) : '';
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${c}`}>
      {icons[direction] || ''} {label}
    </span>
  );
}
