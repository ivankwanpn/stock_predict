interface ConfidenceBarProps {
  value: number;
  color?: string;
  size?: 'sm' | 'md';
}

export default function ConfidenceBar({ value, color, size = 'md' }: ConfidenceBarProps) {
  const pct = Math.min(100, Math.max(0, value || 0));
  const barColor = color || (pct < 40 ? 'bg-red-500' : pct < 70 ? 'bg-yellow-500' : 'bg-green-500');
  const height = size === 'sm' ? 'h-1.5' : 'h-2';
  return (
    <div className="flex items-center gap-3">
      <div className={`flex-1 ${height} bg-gray-700 rounded-full overflow-hidden`}>
        <div className={`h-full ${barColor} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-400 w-10 text-right">{pct.toFixed(0)}%</span>
    </div>
  );
}
