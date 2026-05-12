import type { HmmDiagnostics } from '../../types';
import { formatProb } from '../../utils/formatters';

interface Props {
  hmm: HmmDiagnostics;
}

const REGIME_COLOR: Record<string, string> = {
  crisis: '#D93025',
  recovery: '#0F9D58',
  boom: '#B26A00',
};

const REGIME_LABEL: Record<string, string> = {
  crisis: 'Crisis',
  recovery: 'Recovery',
  boom: 'Boom',
};

const REGIMES = ['crisis', 'recovery', 'boom'] as const;

/**
 * Renders a 3×3 transition heatmap. Each cell:
 *  - background = regime tint at opacity scaled by probability mass
 *  - foreground = % value
 * The diagonal "persistence" cells use the from-regime's tint; off-diagonal
 * cells use the destination regime's tint so the eye reads "where does it
 * go" naturally.
 */
const HeatmapMatrix = ({ T }: { T: number[][] }) => {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'auto repeat(3, 1fr)',
        gap: 4,
        marginTop: 4,
      }}
    >
      {/* Header row */}
      <div />
      {REGIMES.map((r) => (
        <div
          key={r}
          style={{
            textAlign: 'center',
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: 0.12,
            textTransform: 'uppercase',
            color: REGIME_COLOR[r],
            paddingBottom: 4,
          }}
        >
          → {REGIME_LABEL[r]}
        </div>
      ))}

      {/* Body rows */}
      {REGIMES.map((from, i) => (
        <>
          <div
            key={`label-${from}`}
            style={{
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: 0.12,
              textTransform: 'uppercase',
              color: REGIME_COLOR[from],
              display: 'flex',
              alignItems: 'center',
              paddingRight: 8,
            }}
          >
            {REGIME_LABEL[from]} →
          </div>
          {REGIMES.map((to, j) => {
            const v = T[i]?.[j] ?? 0;
            const tint = REGIME_COLOR[i === j ? from : to];
            // Map probability → alpha in [0.05, 0.85]
            const alpha = 0.05 + Math.min(1, v) * 0.8;
            const textColor = v > 0.6 ? '#FFFFFF' : '#0F1B3D';
            return (
              <div
                key={`${from}-${to}`}
                title={`P(${REGIME_LABEL[from]} → ${REGIME_LABEL[to]}) = ${(v * 100).toFixed(1)}%`}
                style={{
                  position: 'relative',
                  borderRadius: 6,
                  background: `${tint}${Math.round(alpha * 255)
                    .toString(16)
                    .padStart(2, '0')}`,
                  padding: '14px 10px',
                  minHeight: 56,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: i === j ? `2px solid ${tint}` : '1px solid transparent',
                  transition: 'transform 120ms ease-out',
                }}
              >
                <span
                  className="mono"
                  style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: textColor,
                    letterSpacing: '-0.02em',
                  }}
                >
                  {(v * 100).toFixed(1)}%
                </span>
              </div>
            );
          })}
        </>
      ))}
    </div>
  );
};

/**
 * State-sequence ribbon: shows the actual fitted regime label at each
 * quarter, as a horizontal colored strip. Lets the user verify the HMM's
 * own segmentation visually.
 */
const StateRibbon = ({ seq }: { seq: HmmDiagnostics['state_sequence'] }) => (
  <div>
    <div className="eyebrow" style={{ marginBottom: 6 }}>
      Fitted state sequence
    </div>
    <div
      style={{
        display: 'flex',
        gap: 1,
        borderRadius: 4,
        overflow: 'hidden',
        border: '1px solid var(--border-2)',
        height: 24,
      }}
    >
      {seq.map((s) => (
        <div
          key={s.quarter}
          title={`${s.quarter} · ${REGIME_LABEL[s.regime]}`}
          style={{
            flex: 1,
            background: REGIME_COLOR[s.regime],
            opacity: 0.9,
          }}
        />
      ))}
    </div>
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        marginTop: 4,
        fontSize: 10,
        color: 'var(--text-3)',
      }}
      className="mono"
    >
      <span>{seq[0]?.quarter}</span>
      <span>{seq[Math.floor(seq.length / 2)]?.quarter}</span>
      <span>{seq[seq.length - 1]?.quarter}</span>
    </div>
  </div>
);

const HmmPanel = ({ hmm }: Props) => {
  const isHmm = hmm.training_method === 'hmm_unsupervised';

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="eyebrow">Regime detection — Hidden Markov Model</div>
          <h3 className="title-2" style={{ marginTop: 2 }}>
            What the data says · what humans labelled
          </h3>
          <div className="body-sm" style={{ marginTop: 4, maxWidth: 540 }}>
            Three-state Gaussian HMM trained <strong>unsupervised</strong> on
            real features (price-change z, volume YoY z, macro stress z).
            States are mapped to Crisis/Recovery/Boom <em>post-hoc</em> via
            Hungarian assignment — labels never enter the likelihood.
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="eyebrow" style={{ fontSize: 9 }}>
            Training method
          </div>
          <div
            className="mono"
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: isHmm ? 'var(--green-500)' : 'var(--amber-500)',
              marginTop: 2,
            }}
          >
            {isHmm ? 'GaussianHMM' : 'KMeans fallback'}
          </div>
          {hmm.log_likelihood !== null && (
            <div className="caption" style={{ marginTop: 2 }}>
              log-likelihood {hmm.log_likelihood.toFixed(2)}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-4" style={{ marginBottom: 18 }}>
        <div className="metric">
          <div className="metric-eyebrow">Observations</div>
          <div className="metric-value">{hmm.n_observations}</div>
          <div className="metric-sub">quarters fed to the fit</div>
        </div>
        <div className="metric">
          <div className="metric-eyebrow">States</div>
          <div className="metric-value">{hmm.n_states}</div>
          <div className="metric-sub">aligned to Crisis · Recovery · Boom</div>
        </div>
        <div className="metric">
          <div className="metric-eyebrow">Agreement vs hand labels</div>
          <div
            className="metric-value"
            style={{
              color:
                hmm.label_agreement_rate >= 0.7
                  ? 'var(--green-500)'
                  : hmm.label_agreement_rate >= 0.5
                    ? 'var(--amber-500)'
                    : 'var(--red-500)',
            }}
          >
            {formatProb(hmm.label_agreement_rate)}
          </div>
          <div className="metric-sub">used for naming only</div>
        </div>
        <div className="metric">
          <div className="metric-eyebrow">Feature space</div>
          <div
            className="mono"
            style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.45, marginTop: 4 }}
          >
            price Δ z · vol YoY z · macro stress z
          </div>
          <div className="metric-sub">all observable, no synthetic proxies</div>
        </div>
      </div>

      <div className="grid grid-2" style={{ gap: 32 }}>
        <div>
          <div className="card-title" style={{ marginBottom: 4 }}>
            Learned transition matrix
          </div>
          <HeatmapMatrix T={hmm.transition_matrix} />
          <div
            className="caption"
            style={{ marginTop: 10, lineHeight: 1.55 }}
          >
            Color intensity = transition probability. Diagonal = persistence
            (sticky each regime is). All values <strong>learned from the
            data</strong>, not configured.
          </div>
        </div>

        <div>
          <div className="card-title" style={{ marginBottom: 4 }}>
            State centroids · z-scored feature means
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {REGIMES.map((r) => {
              const centroid = hmm.state_means_aligned[r] ?? [];
              return (
                <div
                  key={r}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '110px 1fr 1fr 1fr',
                    alignItems: 'center',
                    gap: 8,
                    padding: '8px 10px',
                    background: 'var(--surface-sunken)',
                    borderRadius: 6,
                    borderLeft: `3px solid ${REGIME_COLOR[r]}`,
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: REGIME_COLOR[r],
                    }}
                  >
                    {REGIME_LABEL[r]}
                  </div>
                  {hmm.feature_names.map((f, i) => {
                    const v = centroid[i] ?? 0;
                    const pos = v >= 0;
                    return (
                      <div key={f} style={{ minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: 9,
                            color: 'var(--text-3)',
                            letterSpacing: 0.06,
                            textTransform: 'uppercase',
                          }}
                        >
                          {f.replace(/_/g, ' ').replace(' z', '')}
                        </div>
                        <div
                          className="mono"
                          style={{
                            fontSize: 13,
                            fontWeight: 600,
                            color: pos ? 'var(--green-500)' : 'var(--red-500)',
                          }}
                        >
                          {pos ? '+' : ''}
                          {v.toFixed(2)}σ
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
          <div className="caption" style={{ marginTop: 10, lineHeight: 1.55 }}>
            Each value is how many standard deviations from the long-run mean
            that regime's average looks like. Larger magnitude = more distinct
            regime signature.
          </div>
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <StateRibbon seq={hmm.state_sequence} />
      </div>

      <div
        style={{
          marginTop: 16,
          padding: 12,
          background: 'var(--surface-sunken)',
          borderRadius: 6,
          fontSize: 12,
          color: 'var(--text-2)',
          lineHeight: 1.6,
        }}
      >
        <strong style={{ color: 'var(--text-1)' }}>Methodology.</strong> Three-state
        Gaussian HMM (diagonal covariance), 5 random initialisations, best by
        log-likelihood retained. State IDs are mapped to <em>Crisis / Recovery /
        Boom</em> via Hungarian linear assignment against hand-annotated labels
        — used only for naming. Agreement rate is reported as a diagnostic,
        not a training target.
      </div>
    </div>
  );
};

export default HmmPanel;
