/**
 * 股票分析相关类型定义
 * 与 API 规范 (api_spec.json) 对齐
 */

// ============ 请求类型 ============

export interface AnalysisRequest {
  stockCode: string;
  reportType?: 'simple' | 'detailed';
  forceRefresh?: boolean;
  asyncMode?: boolean;
}

// ============ 报告类型 ============

/** 报告元信息 */
export interface ReportMeta {
  queryId: string;
  stockCode: string;
  stockName: string;
  reportType: 'simple' | 'detailed';
  createdAt: string;
  currentPrice?: number;
  changePct?: number;
  openPrice?: number;
  highPrice?: number;
  lowPrice?: number;
  prevClose?: number;
  volume?: number;
  amount?: number;
  turnoverRate?: number;
  volumeRatio?: number;
  amplitude?: number;
}

/** 情绪标签 */
export type SentimentLabel = 'Strong Bearish' | 'Bearish' | 'Neutral' | 'Bullish' | 'Strong Bullish';

/** 报告概览区 */
export interface ReportSummary {
  analysisSummary: string;
  operationAdvice: string;
  trendPrediction: string;
  sentimentScore: number;
  sentimentLabel?: SentimentLabel;
}

/** 策略点位区 */
export interface ReportStrategy {
  idealBuy?: string;
  secondaryBuy?: string;
  stopLoss?: string;
  takeProfit?: string;
}

/** US 模块评分 */
export interface UsModuleScore {
  score: number;
  signal: string;
  weight: number;
}

/** US 6-模块汇总 */
export interface UsModules {
  macro?: UsModuleScore;
  sector?: UsModuleScore;
  fundamental?: UsModuleScore;
  technical?: UsModuleScore;
  events?: UsModuleScore;
  sentiment?: UsModuleScore;
  weightedTotal?: number;
}

/** US 模块 LLM 分析洞察 */
export interface UsModuleInsight {
  moduleName: string;
  displayName: string;
  score: number;
  analysis: string;
  keyFindings: string[];
  riskFactors: string[];
  signal: string;
  outlook: string;
  success: boolean;
  fallbackUsed: boolean;
}

/** US 6-模块 LLM 分析洞察汇总 */
export interface UsModuleInsights {
  macro?: UsModuleInsight;
  sector?: UsModuleInsight;
  fundamental?: UsModuleInsight;
  technical?: UsModuleInsight;
  events?: UsModuleInsight;
  sentiment?: UsModuleInsight;
}

/** 交易场景 */
export interface TradeScenario {
  name: string;
  trigger?: string;
  entry?: number | string;
  stopLoss?: number | string;
  target?: number | string;
  positionPct?: number | string;
  riskReward?: string;
  action?: string;
}

/** 作战计划 */
export interface BattlePlan {
  scenarios?: TradeScenario[];
  actionChecklist?: string[];
  riskWarnings?: string[];
}

/** 决策仪表盘 */
export interface Dashboard {
  coreConclusion?: Record<string, unknown>;
  intelligence?: {
    riskAlerts?: string[];
    positiveCatalysts?: string[];
    sentimentSummary?: string;
  };
  battlePlan?: BattlePlan;
  usModules?: UsModules;
  usModuleInsights?: UsModuleInsights;
}

/** 详情区（可折叠） */
export interface ReportDetails {
  newsContent?: string;
  rawResult?: Record<string, unknown>;
  contextSnapshot?: Record<string, unknown>;
  technicalAnalysis?: string;
  fundamentalAnalysis?: string;
  riskWarning?: string;
  dashboard?: Dashboard;
}

/** 完整分析报告 */
export interface AnalysisReport {
  meta: ReportMeta;
  summary: ReportSummary;
  strategy?: ReportStrategy;
  details?: ReportDetails;
}

// ============ 分析结果类型 ============

/** 同步分析返回结果 */
export interface AnalysisResult {
  queryId: string;
  stockCode: string;
  stockName: string;
  report: AnalysisReport;
  createdAt: string;
}

/** 异步任务接受响应 */
export interface TaskAccepted {
  taskId: string;
  status: 'pending' | 'processing';
  message?: string;
}

/** 任务状态 */
export interface TaskStatus {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  result?: AnalysisResult;
  error?: string;
}

/** 任务详情（用于任务列表和 SSE 事件） */
export interface TaskInfo {
  taskId: string;
  stockCode: string;
  stockName?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  reportType: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

/** 任务列表响应 */
export interface TaskListResponse {
  total: number;
  pending: number;
  processing: number;
  tasks: TaskInfo[];
}

/** 重复任务错误响应 */
export interface DuplicateTaskError {
  error: 'duplicate_task';
  message: string;
  stockCode: string;
  existingTaskId: string;
}

// ============ 历史记录类型 ============

/** 历史记录摘要（列表展示用） */
export interface HistoryItem {
  queryId: string;
  stockCode: string;
  stockName?: string;
  reportType?: string;
  sentimentScore?: number;
  operationAdvice?: string;
  createdAt: string;
}

/** 历史记录列表响应 */
export interface HistoryListResponse {
  total: number;
  page: number;
  limit: number;
  items: HistoryItem[];
}

/** 新闻情报条目 */
export interface NewsIntelItem {
  title: string;
  snippet: string;
  url: string;
}

/** 新闻情报响应 */
export interface NewsIntelResponse {
  total: number;
  items: NewsIntelItem[];
}

/** 历史列表筛选参数 */
export interface HistoryFilters {
  stockCode?: string;
  startDate?: string;
  endDate?: string;
}

/** 历史列表分页参数 */
export interface HistoryPagination {
  page: number;
  limit: number;
}

// ============ 错误类型 ============

export interface ApiError {
  error: string;
  message: string;
  detail?: Record<string, unknown>;
}

// ============ 辅助函数 ============

/** 根据情绪评分获取情绪标签 */
export const getSentimentLabel = (score: number): SentimentLabel => {
  if (score <= 20) return 'Strong Bearish';
  if (score <= 40) return 'Bearish';
  if (score <= 60) return 'Neutral';
  if (score <= 80) return 'Bullish';
  return 'Strong Bullish';
};

/** 根据情绪评分获取颜色 */
export const getSentimentColor = (score: number): string => {
  if (score <= 20) return '#ef4444'; // red-500
  if (score <= 40) return '#f97316'; // orange-500
  if (score <= 60) return '#eab308'; // yellow-500
  if (score <= 80) return '#22c55e'; // green-500
  return '#10b981'; // emerald-500
};
