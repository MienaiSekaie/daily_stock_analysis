import React, { useState } from 'react';
import type { UsModules, UsModuleInsights, UsModuleInsight } from '../../types/analysis';
import { Card } from '../common';

interface ReportUsModulesProps {
  usModules?: UsModules;
  moduleInsights?: UsModuleInsights;
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

const getOutlookColor = (outlook: string): string => {
  const o = outlook.toLowerCase();
  if (o === 'bullish') return '#00ff88';
  if (o === 'bearish') return '#ff4466';
  return '#eab308';
};

interface ModuleBarProps {
  name: string;
  score: number;
  signal: string;
  weight: number;
  insight?: UsModuleInsight;
}

const ModuleBar: React.FC<ModuleBarProps> = ({ name, score, signal, weight, insight }) => {
  const [expanded, setExpanded] = useState(false);
  const color = getScoreColor(score);
  const hasInsight = insight && insight.analysis && insight.success;

  return (
    <div
      className={`relative overflow-hidden rounded-lg bg-elevated border border-white/5 transition-all duration-300 ${
        hasInsight ? 'cursor-pointer hover:border-white/15' : ''
      }`}
      onClick={() => hasInsight && setExpanded(!expanded)}
    >
      <div className="p-3">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-white uppercase tracking-wider">{name}</span>
            {hasInsight && (
              <svg
                className={`w-3 h-3 text-muted transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            )}
          </div>
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

      {/* Expanded insight panel */}
      {expanded && hasInsight && (
        <div className="border-t border-white/5 p-3 space-y-2 animate-fade-in">
          {/* Outlook badge */}
          {insight.outlook && (
            <div className="flex items-center gap-1.5 mb-1">
              <span className="text-xs text-muted">Outlook:</span>
              <span
                className="text-xs font-semibold uppercase"
                style={{ color: getOutlookColor(insight.outlook) }}
              >
                {insight.outlook}
              </span>
            </div>
          )}

          {/* Analysis text */}
          <p className="text-xs text-white/80 leading-relaxed whitespace-pre-wrap">
            {insight.analysis}
          </p>

          {/* Key findings */}
          {insight.keyFindings && insight.keyFindings.length > 0 && (
            <div>
              <span className="text-xs font-semibold text-cyan">Key Findings</span>
              <ul className="mt-1 space-y-0.5">
                {insight.keyFindings.map((finding, i) => (
                  <li key={i} className="text-xs text-white/70 flex gap-1.5">
                    <span className="text-success flex-shrink-0">+</span>
                    <span>{finding}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Risk factors */}
          {insight.riskFactors && insight.riskFactors.length > 0 && (
            <div>
              <span className="text-xs font-semibold text-warning">Risk Factors</span>
              <ul className="mt-1 space-y-0.5">
                {insight.riskFactors.map((risk, i) => (
                  <li key={i} className="text-xs text-white/70 flex gap-1.5">
                    <span className="text-danger flex-shrink-0">!</span>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * US Stock 6-Module Scoring Dashboard
 * Displays score bars + expandable AI analysis for each module
 */
export const ReportUsModules: React.FC<ReportUsModulesProps> = ({ usModules, moduleInsights }) => {
  if (!usModules) return null;

  const modules = Object.entries(MODULE_LABELS)
    .map(([key, label]) => {
      const mod = usModules[key as keyof UsModules];
      if (!mod || typeof mod !== 'object') return null;
      const insight = moduleInsights?.[key as keyof UsModuleInsights];
      return { key, label, ...mod, insight };
    })
    .filter(Boolean) as (ModuleBarProps & { key: string; label: string })[];

  if (modules.length === 0) return null;

  const weightedTotal = usModules.weightedTotal;
  const hasAnyInsights = moduleInsights && Object.values(moduleInsights).some(v => v?.analysis);

  return (
    <Card variant="bordered" padding="md">
      <div className="mb-3 flex items-baseline gap-2">
        <span className="label-uppercase">US MODULES</span>
        <h3 className="text-base font-semibold text-white">6-Module Analysis</h3>
        {hasAnyInsights && (
          <span className="text-xs text-muted">(click to expand)</span>
        )}
        {weightedTotal != null && (
          <span
            className="ml-auto text-xl font-bold font-mono"
            style={{ color: getScoreColor(weightedTotal) }}
          >
            {weightedTotal}
          </span>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {modules.map((mod) => (
          <ModuleBar
            key={mod.key}
            name={mod.label}
            score={mod.score}
            signal={mod.signal}
            weight={mod.weight}
            insight={mod.insight}
          />
        ))}
      </div>
    </Card>
  );
};
