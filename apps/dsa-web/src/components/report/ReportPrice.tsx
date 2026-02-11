import type React from 'react';
import type { ReportMeta } from '../../types/analysis';
import { Card } from '../common';

interface ReportPriceProps {
  meta: ReportMeta;
}

interface QuoteItemProps {
  label: string;
  value?: number | null;
  format?: (v: number) => string;
  colorBySign?: boolean;
}

const defaultFormat = (v: number): string => v.toFixed(2);

const formatVolume = (v: number): string => {
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(2)}万`;
  return v.toFixed(0);
};

const formatAmount = (v: number): string => {
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(2)}万`;
  return v.toFixed(2);
};

const QuoteItem: React.FC<QuoteItemProps> = ({
  label,
  value,
  format = defaultFormat,
  colorBySign = false,
}) => {
  let textColor = 'text-white';
  if (colorBySign && value != null) {
    if (value > 0) textColor = 'text-[#ff4d4d]';
    else if (value < 0) textColor = 'text-[#00d46a]';
    else textColor = 'text-muted';
  }

  return (
    <div className="rounded-lg bg-elevated border border-white/5 p-2.5">
      <span className="text-xs text-muted block mb-0.5">{label}</span>
      <span className={`text-sm font-bold font-mono ${value != null ? textColor : 'text-muted'}`}>
        {value != null ? format(value) : '—'}
      </span>
    </div>
  );
};

/**
 * Market quote section - displays the stock's latest price and key market data
 * at the time of analysis. Terminal-themed style.
 */
export const ReportPrice: React.FC<ReportPriceProps> = ({ meta }) => {
  if (meta.currentPrice == null) {
    return null;
  }

  // Price change color (A-share convention: red = up, green = down)
  const getPriceColor = (): string => {
    if (meta.changePct == null) return 'text-white';
    if (meta.changePct > 0) return 'text-[#ff4d4d]';
    if (meta.changePct < 0) return 'text-[#00d46a]';
    return 'text-muted';
  };

  const formatChangePct = (): string => {
    if (meta.changePct == null) return '--';
    const sign = meta.changePct > 0 ? '+' : '';
    return `${sign}${meta.changePct.toFixed(2)}%`;
  };

  const priceColor = getPriceColor();

  // Calculate price change amount
  const changeAmount = meta.prevClose != null
    ? meta.currentPrice - meta.prevClose
    : null;

  const quoteItems = [
    { label: '开盘', value: meta.openPrice },
    { label: '最高', value: meta.highPrice },
    { label: '最低', value: meta.lowPrice },
    { label: '昨收', value: meta.prevClose },
    { label: '成交量', value: meta.volume, format: formatVolume },
    { label: '成交额', value: meta.amount, format: formatAmount },
    { label: '换手率', value: meta.turnoverRate, format: (v: number) => `${v.toFixed(2)}%` },
    { label: '量比', value: meta.volumeRatio },
  ];

  // Only show items that have data
  const availableItems = quoteItems.filter(item => item.value != null);

  return (
    <Card variant="bordered" padding="md">
      <div className="mb-3 flex items-baseline gap-2">
        <span className="label-uppercase">MARKET QUOTE</span>
        <h3 className="text-base font-semibold text-white">最新行情</h3>
      </div>

      {/* Price hero area */}
      <div className="flex items-baseline gap-4 mb-4 pb-3 border-b border-white/5">
        <span className={`text-3xl font-bold font-mono ${priceColor}`}>
          {meta.currentPrice.toFixed(2)}
        </span>
        <div className="flex items-baseline gap-2">
          {changeAmount != null && (
            <span className={`text-base font-semibold font-mono ${priceColor}`}>
              {changeAmount > 0 ? '+' : ''}{changeAmount.toFixed(2)}
            </span>
          )}
          <span className={`text-sm font-semibold font-mono px-1.5 py-0.5 rounded ${priceColor} bg-white/5`}>
            {formatChangePct()}
          </span>
        </div>
        {meta.amplitude != null && (
          <span className="text-xs text-muted ml-auto">
            振幅 {meta.amplitude.toFixed(2)}%
          </span>
        )}
      </div>

      {/* Market data grid */}
      {availableItems.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {availableItems.map((item) => (
            <QuoteItem
              key={item.label}
              label={item.label}
              value={item.value}
              format={item.format}
            />
          ))}
        </div>
      )}
    </Card>
  );
};
