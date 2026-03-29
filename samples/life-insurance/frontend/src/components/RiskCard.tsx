import type { RiskData } from '../types/a2a';

const LEVEL_COLOR: Record<string, string> = {
  excellent: 'bg-success',
  low: 'bg-green-400',
  standard: 'bg-primary',
  medium: 'bg-yellow-500',
  substandard: 'bg-orange-500',
  high: 'bg-error',
};

export function RiskCard({ data }: { data: RiskData }) {
  return (
    <div className="bg-bg-card rounded-lg p-4 border border-border space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-text font-semibold">風險預評估</h3>
        <span className="text-2xl font-bold text-primary">{data.score} 分</span>
      </div>
      <div className="text-sm text-text-muted">
        等級：<span className="text-primary font-medium">{data.risk_class.replace('_', ' ').toUpperCase()}</span>
        {' · '}BMI {data.bmi}{' · '}保費影響 {data.premium_impact}
      </div>
      <div className="space-y-2">
        {data.factors.map((f) => (
          <div key={f.name} className="flex items-center gap-2 text-sm">
            <span className="w-20 text-text-muted shrink-0">{f.name}</span>
            <div className="flex-1 h-2 bg-bg rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${LEVEL_COLOR[f.level] || 'bg-primary'}`} style={{ width: `${f.score}%` }} />
            </div>
            <span className="w-8 text-right text-text-muted">{f.score}</span>
          </div>
        ))}
      </div>
      <p className="text-sm text-text-muted">{data.prediction}</p>
    </div>
  );
}
