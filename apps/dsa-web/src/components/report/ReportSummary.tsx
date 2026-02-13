import React from 'react';
import type { AnalysisResult, AnalysisReport } from '../../types/analysis';
import { ReportOverview } from './ReportOverview';
import { ReportPrice } from './ReportPrice';
import { ReportUsModules } from './ReportUsModules';
import { ReportStrategy } from './ReportStrategy';
import { ReportBattlePlan } from './ReportBattlePlan';
import { ReportAnalysisText } from './ReportAnalysisText';
import { ReportNews } from './ReportNews';
import { ReportDetails } from './ReportDetails';

interface ReportSummaryProps {
  data: AnalysisResult | AnalysisReport;
  isHistory?: boolean;
}

/**
 * 完整报告展示组件
 * 整合概览、策略、资讯、详情四个区域
 */
export const ReportSummary: React.FC<ReportSummaryProps> = ({
  data,
  isHistory = false,
}) => {
  // 兼容 AnalysisResult 和 AnalysisReport 两种数据格式
  const report: AnalysisReport = 'report' in data ? data.report : data;
  const queryId = 'queryId' in data ? data.queryId : report.meta.queryId;

  const { meta, summary, strategy, details } = report;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* 概览区（首屏） */}
      <ReportOverview
        meta={meta}
        summary={summary}
        isHistory={isHistory}
      />

      {/* 最新行情区 */}
      <ReportPrice meta={meta} />

      {/* US 6-Module Scoring */}
      <ReportUsModules
        usModules={details?.dashboard?.usModules}
        moduleInsights={details?.dashboard?.usModuleInsights}
      />

      {/* 策略点位区 */}
      <ReportStrategy strategy={strategy} />

      {/* Battle Plan */}
      <ReportBattlePlan battlePlan={details?.dashboard?.battlePlan} />

      {/* Detailed Analysis Text */}
      <ReportAnalysisText
        technicalAnalysis={details?.technicalAnalysis}
        fundamentalAnalysis={details?.fundamentalAnalysis}
        riskWarning={details?.riskWarning}
        intelligence={details?.dashboard?.intelligence}
      />

      {/* 资讯区 */}
      <ReportNews queryId={queryId} />

      {/* 透明度与追溯区 */}
      <ReportDetails details={details} queryId={queryId} />
    </div>
  );
};
