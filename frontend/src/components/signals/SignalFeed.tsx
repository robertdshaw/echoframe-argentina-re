import { useState } from 'react';
import type { ProcessedSignal, Segment } from '../../types';
import { useSignals } from '../../hooks/useSignals';
import SignalCard from './SignalCard';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';

interface Props {
  defaultSegment?: Segment;
  limit?: number;
  showFilters?: boolean;
}

type SortKey = 'date' | 'impact';

const SignalFeed = ({ defaultSegment, limit = 20, showFilters = true }: Props) => {
  const [segment, setSegment] = useState<Segment | undefined>(defaultSegment);
  const [sort, setSort] = useState<SortKey>('date');
  const { signals, loading, error } = useSignals(segment, limit);

  if (loading) return <LoadingSpinner label="Loading signals…" />;
  if (error) return <ErrorMessage message={error} />;

  const sorted: ProcessedSignal[] = [...signals].sort((a, b) => {
    if (sort === 'impact') {
      return b.market_impact_score - a.market_impact_score;
    }
    return (
      new Date(b.published_at).getTime() - new Date(a.published_at).getTime()
    );
  });

  return (
    <div>
      {showFilters && (
        <div
          style={{
            display: 'flex',
            gap: 8,
            marginBottom: 16,
            alignItems: 'center',
            flexWrap: 'wrap',
          }}
        >
          <select
            value={segment ?? ''}
            onChange={(e) =>
              setSegment(
                e.target.value === '' ? undefined : (e.target.value as Segment),
              )
            }
            style={{ padding: '6px 10px', borderRadius: 4, border: '1px solid #E5E7EB' }}
          >
            <option value="">All segments</option>
            <option value="departamentos">Departamentos</option>
            <option value="campos">Campos</option>
          </select>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            style={{ padding: '6px 10px', borderRadius: 4, border: '1px solid #E5E7EB' }}
          >
            <option value="date">Sort by date</option>
            <option value="impact">Sort by impact</option>
          </select>
          <span style={{ marginLeft: 'auto', fontSize: 12, color: '#666' }}>
            {sorted.length} signals
          </span>
        </div>
      )}
      {sorted.map((s) => (
        <SignalCard key={s.article_id} signal={s} />
      ))}
      {sorted.length === 0 && (
        <div style={{ color: '#666', padding: 20, textAlign: 'center' }}>
          No signals match the current filter.
        </div>
      )}
    </div>
  );
};

export default SignalFeed;
