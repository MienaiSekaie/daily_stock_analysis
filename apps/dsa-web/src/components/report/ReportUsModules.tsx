import type React from 'react';
import type { UsModules } from '../../types/analysis';
import { Card } from '../common';

interface ReportUsModulesProps {
  usModules?: UsModules;
}

const MODULE_LABELS: Record<string, string> = {
  macro: 'Macro',
  sector: 'Sector',
  fundamental: 'Fundamental',
  technical: 'Technical',
  events: 'Events',
  sentiment: 'Sentiment',
};

const getScoreColor = (score: number): string => {
  if (score >= 70) return '#00ff88';
  if (score >= 60) return '#00d4ff';
  if (score >= 40) return '#eab308';
  return '#ff4466';
};

const getSignalColor = (signal: string): string => {
  const s = signal.toLowerCase();
  if (s.includes('bullish') || s.includes('positive') || s.includes('strong')) return '#00ff88';
  if (s.includes('bearish') || s.includes('negative') || s.includes('weak')) return '#ff4466';
  if (s.includes('neutral') || s.includes('mixed')) return '#eab308';
  return '#00d4ff';
};

interface ModuleBarProps {
  name: string;
  score: number;
  signal: string;
  weight: number;
}

const ModuleBar: React.FC<ModuleBarProps> = ({ name, score, signal, weight }) => {
  const color = getScoreColor(score);
  return (
    <div className="relative overflow-hidden rounded-lg bg-elevated border border-white/5 p-3">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-semibold text-white uppercase tracking-wider">{name}</span>
        <span className="text-xs text-muted font-mono">{weight}%</span>
      </div>
      {/* Score bar */}
      <div className="h-1.5 rounded-full bg-white/5 mb-1.5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(100, Math.max(0, score))}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono font-bold" style={{ color }}>{score}</span>
        <span className="text-xs" style={{ color: getSignalColor(signal) }}>{signal}</span>
      </div>
    </div>
  );
};

/**
 * US Stock 6-Module Scoring Dashboard
 */
export const ReportUsModules: React.FC<ReportUsModulesProps> = ({ usModules }) => {
  if (!usModules) return null;

  const modules = Object.entries(MODULE_LABELS)
    .map(([key, label]) => {
      const mod = usModules[key as keyof UsModules];
      if (!mod || typeof mod !== 'object') return null;
      return { key, label, ...mod };
    })
    .filter(Boolean) as (ModuleBarProps & { key: string; label: string })[];

  if (modules.length === 0) return null;

  const weightedTotal = usModules.weightedTotal;

  return (
    <Card variant="bordered" padding="md">
      <div className="mb-3 flex items-baseline gap-2">
        <span className="label-uppercase">US MODULES</span>
        <h3 className="text-base font-semibold text-white">6-Module Analysis</h3>
        {weightedTotal != null && (
          <span
            className="ml-auto text-xl font-bold font-mono"
            style={{ color: getScoreColor(weightedTotal) }}
          >
            {weightedTotal}
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {modules.map((mod) => (
          <ModuleBar
            key={mod.key}
            name={mod.label}
            score={mod.score}
            signal={mod.signal}
            weight={mod.weight}
          />
        ))}
      </div>
    </Card>
  );
};
