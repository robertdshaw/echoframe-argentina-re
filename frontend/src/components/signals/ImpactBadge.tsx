import type { ImpactDirection } from '../../types';

interface Props {
  direction: ImpactDirection;
  magnitude: number;
}

const ImpactBadge = ({ direction, magnitude }: Props) => {
  const isPositive = direction === 'positive';
  const isNeutral = direction === 'neutral';
  const arrow = isPositive ? '↑' : isNeutral ? '→' : '↓';
  const className = isPositive
    ? 'signal-impact impact-positive'
    : isNeutral
      ? 'signal-impact'
      : 'signal-impact impact-negative';
  return (
    <span className={className}>
      {arrow} <span className="mono">{magnitude.toFixed(2)}</span>
    </span>
  );
};

export default ImpactBadge;
