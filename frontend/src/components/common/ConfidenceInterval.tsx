import { formatPct } from '../../utils/formatters';
import type { ConfidenceInterval as CI } from '../../types';

interface Props {
  ci: CI;
  label?: string;
}

const ConfidenceIntervalDisplay = ({ ci, label }: Props) => (
  <div style={{ fontSize: 14, color: '#444' }}>
    {label && <span style={{ marginRight: 6, color: '#666' }}>{label}</span>}
    <span className="mono">
      {formatPct(ci.lower)} → {formatPct(ci.upper)}
    </span>
    <span style={{ color: '#999', marginLeft: 6 }}>
      ({ci.confidence_level}% CI)
    </span>
  </div>
);

export default ConfidenceIntervalDisplay;
