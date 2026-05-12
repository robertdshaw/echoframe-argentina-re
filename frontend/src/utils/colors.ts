export const colors = {
  navy: '#1B2A4A',
  orange: '#E85D26',
  purple: '#4A3B8F',
  bgLight: '#F8F9FB',
  white: '#FFFFFF',
  green: '#10B981',
  red: '#EF4444',
  amber: '#F59E0B',
  muted: '#666666',
  border: '#E5E7EB',
} as const;

export const regimeColor = (regime: 'crisis' | 'recovery' | 'boom'): string => {
  switch (regime) {
    case 'crisis':
      return colors.red;
    case 'recovery':
      return colors.green;
    case 'boom':
      return colors.amber;
  }
};
