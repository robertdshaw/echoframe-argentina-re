interface Props {
  label?: string;
}

const LoadingSpinner = ({ label = 'Loading…' }: Props) => (
  <div className="loading">
    <div
      style={{
        width: 32,
        height: 32,
        margin: '0 auto 12px',
        border: '3px solid #E5E7EB',
        borderTopColor: '#E85D26',
        borderRadius: '50%',
        animation: 'spin 0.9s linear infinite',
      }}
    />
    <div>{label}</div>
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </div>
);

export default LoadingSpinner;
