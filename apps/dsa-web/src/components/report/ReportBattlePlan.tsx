import type React from 'react';
import type { BattlePlan, TradeScenario } from '../../types/analysis';
import { Card } from '../common';

interface ReportBattlePlanProps {
  battlePlan?: BattlePlan;
}

const ScenarioCard: React.FC<{ scenario: TradeScenario; index: number }> = ({ scenario, index }) => {
  const items: { label: string; value: string; color: string }[] = [];

  if (scenario.entry != null) items.push({ label: 'Entry', value: String(scenario.entry), color: '#00ff88' });
  if (scenario.stopLoss != null) items.push({ label: 'Stop', value: String(scenario.stopLoss), color: '#ff4466' });
  if (scenario.target != null) items.push({ label: 'Target', value: String(scenario.target), color: '#00d4ff' });
  if (scenario.positionPct != null) items.push({ label: 'Position', value: `${scenario.positionPct}%`, color: '#eab308' });
  if (scenario.riskReward) items.push({ label: 'R:R', value: scenario.riskReward, color: '#c084fc' });

  return (
    <div className="rounded-lg bg-elevated border border-white/5 p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-mono text-muted">#{index + 1}</span>
        <span className="text-sm font-semibold text-white">{scenario.name}</span>
      </div>
      {scenario.trigger && (
        <p className="text-xs text-secondary mb-2">{scenario.trigger}</p>
      )}
      {items.length > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {items.map((item) => (
            <div key={item.label} className="flex items-center gap-1">
              <span className="text-xs text-muted">{item.label}:</span>
              <span className="text-xs font-mono font-bold" style={{ color: item.color }}>
                {item.value}
              </span>
            </div>
          ))}
        </div>
      )}
      {scenario.action && (
        <p className="text-xs text-cyan mt-2">{scenario.action}</p>
      )}
    </div>
  );
};

const getChecklistIcon = (item: string): string => {
  const lower = item.toLowerCase();
  if (lower.startsWith('[x]') || lower.startsWith('v ') || lower.includes('done')) return '\u2705';
  if (lower.startsWith('[ ]') || lower.includes('pending')) return '\u2b1c';
  if (lower.includes('warning') || lower.includes('caution')) return '\u26a0\ufe0f';
  return '\u25b8';
};

/**
 * Battle Plan component - Trade scenarios, action checklist, risk warnings
 */
export const ReportBattlePlan: React.FC<ReportBattlePlanProps> = ({ battlePlan }) => {
  if (!battlePlan) return null;

  const { scenarios, actionChecklist, riskWarnings } = battlePlan;
  const hasContent = (scenarios && scenarios.length > 0) ||
    (actionChecklist && actionChecklist.length > 0) ||
    (riskWarnings && riskWarnings.length > 0);

  if (!hasContent) return null;

  return (
    <Card variant="bordered" padding="md">
      <div className="mb-3 flex items-baseline gap-2">
        <span className="label-uppercase">BATTLE PLAN</span>
        <h3 className="text-base font-semibold text-white">Action Plan</h3>
      </div>

      <div className="space-y-4">
        {/* Trade Scenarios */}
        {scenarios && scenarios.length > 0 && (
          <div>
            <h4 className="text-xs text-muted uppercase tracking-wider mb-2">Trade Scenarios</h4>
            <div className="space-y-2">
              {scenarios.map((s, i) => (
                <ScenarioCard key={`scenario-${i}`} scenario={s} index={i} />
              ))}
            </div>
          </div>
        )}

        {/* Action Checklist */}
        {actionChecklist && actionChecklist.length > 0 && (
          <div>
            <h4 className="text-xs text-muted uppercase tracking-wider mb-2">Action Checklist</h4>
            <ul className="space-y-1">
              {actionChecklist.map((item, i) => (
                <li key={`check-${i}`} className="flex items-start gap-2 text-xs text-secondary">
                  <span className="flex-shrink-0 mt-0.5">{getChecklistIcon(item)}</span>
                  <span>{item.replace(/^\[[ x]\]\s*/, '')}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Risk Warnings */}
        {riskWarnings && riskWarnings.length > 0 && (
          <div>
            <h4 className="text-xs text-muted uppercase tracking-wider mb-2">Risk Warnings</h4>
            <div className="rounded-lg bg-[#ff4466]/5 border border-[#ff4466]/20 p-3">
              <ul className="space-y-1">
                {riskWarnings.map((warning, i) => (
                  <li key={`warn-${i}`} className="flex items-start gap-2 text-xs text-[#ff4466]">
                    <span className="flex-shrink-0 mt-0.5">{'\u26a0'}</span>
                    <span>{warning}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
