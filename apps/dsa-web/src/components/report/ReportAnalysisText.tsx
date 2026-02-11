import type React from 'react';
import { useState } from 'react';
import type { Dashboard } from '../../types/analysis';
import { Card } from '../common';

interface ReportAnalysisTextProps {
  technicalAnalysis?: string;
  fundamentalAnalysis?: string;
  riskWarning?: string;
  intelligence?: Dashboard['intelligence'];
}

interface CollapsibleSectionProps {
  title: string;
  content: string;
  defaultOpen?: boolean;
  color?: string;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  content,
  defaultOpen = false,
  color,
}) => {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-2.5 rounded-lg bg-elevated hover:bg-hover transition-colors"
      >
        <span className="text-xs text-white">{title}</span>
        <svg
          className={`w-3.5 h-3.5 text-muted transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="mt-2 animate-fade-in">
          <div
            className="text-xs text-secondary whitespace-pre-wrap p-3 bg-base rounded-lg leading-relaxed"
            style={color ? { borderLeft: `2px solid ${color}` } : undefined}
          >
            {content}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Detailed analysis text sections with intelligence highlights
 */
export const ReportAnalysisText: React.FC<ReportAnalysisTextProps> = ({
  technicalAnalysis,
  fundamentalAnalysis,
  riskWarning,
  intelligence,
}) => {
  const hasText = technicalAnalysis || fundamentalAnalysis || riskWarning;
  const hasIntel = intelligence && (
    (intelligence.riskAlerts && intelligence.riskAlerts.length > 0) ||
    (intelligence.positiveCatalysts && intelligence.positiveCatalysts.length > 0) ||
    intelligence.sentimentSummary
  );

  if (!hasText && !hasIntel) return null;

  return (
    <Card variant="bordered" padding="md">
      <div className="mb-3 flex items-baseline gap-2">
        <span className="label-uppercase">ANALYSIS</span>
        <h3 className="text-base font-semibold text-white">Detailed Analysis</h3>
      </div>

      <div className="space-y-2">
        {/* Intelligence highlights */}
        {hasIntel && (
          <div className="rounded-lg bg-elevated border border-white/5 p-3 mb-3">
            {intelligence!.sentimentSummary && (
              <p className="text-xs text-secondary mb-2">
                <span className="text-cyan font-semibold">Sentiment: </span>
                {intelligence!.sentimentSummary}
              </p>
            )}
            {intelligence!.positiveCatalysts && intelligence!.positiveCatalysts.length > 0 && (
              <div className="mb-2">
                <span className="text-xs text-[#00ff88] font-semibold">Catalysts: </span>
                <ul className="mt-1 space-y-0.5">
                  {intelligence!.positiveCatalysts.map((c, i) => (
                    <li key={`cat-${i}`} className="text-xs text-secondary pl-3">+ {c}</li>
                  ))}
                </ul>
              </div>
            )}
            {intelligence!.riskAlerts && intelligence!.riskAlerts.length > 0 && (
              <div>
                <span className="text-xs text-[#ff4466] font-semibold">Risk Alerts: </span>
                <ul className="mt-1 space-y-0.5">
                  {intelligence!.riskAlerts.map((r, i) => (
                    <li key={`risk-${i}`} className="text-xs text-secondary pl-3">- {r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Collapsible text sections */}
        {technicalAnalysis && (
          <CollapsibleSection
            title="Technical Analysis"
            content={technicalAnalysis}
            defaultOpen={true}
            color="#00d4ff"
          />
        )}
        {fundamentalAnalysis && (
          <CollapsibleSection
            title="Fundamental Analysis"
            content={fundamentalAnalysis}
            color="#00ff88"
          />
        )}
        {riskWarning && (
          <CollapsibleSection
            title="Risk Warning"
            content={riskWarning}
            color="#ff4466"
          />
        )}
      </div>
    </Card>
  );
};
