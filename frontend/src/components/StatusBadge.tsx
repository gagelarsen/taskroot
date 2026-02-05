import { Chip } from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

interface StatusBadgeProps {
  type: 'over_budget' | 'over_expected' | 'missing_lead' | 'missing_estimate' | 'unassigned' | 'on_track' | 'at_risk' | 'blocked' | 'completed';
  label?: string;
  size?: 'small' | 'medium';
}

export function StatusBadge({ type, label, size = 'small' }: StatusBadgeProps) {
  const configs = {
    over_budget: {
      label: label || 'Over Budget',
      color: 'error' as const,
      icon: <ErrorIcon />,
    },
    over_expected: {
      label: label || 'Over Expected',
      color: 'warning' as const,
      icon: <WarningIcon />,
    },
    missing_lead: {
      label: label || 'Missing Lead',
      color: 'warning' as const,
      icon: <WarningIcon />,
    },
    missing_estimate: {
      label: label || 'Missing Estimate',
      color: 'warning' as const,
      icon: <WarningIcon />,
    },
    unassigned: {
      label: label || 'Unassigned',
      color: 'default' as const,
      icon: <InfoIcon />,
    },
    on_track: {
      label: label || 'On Track',
      color: 'success' as const,
      icon: <CheckCircleIcon />,
    },
    at_risk: {
      label: label || 'At Risk',
      color: 'warning' as const,
      icon: <WarningIcon />,
    },
    blocked: {
      label: label || 'Blocked',
      color: 'error' as const,
      icon: <ErrorIcon />,
    },
    completed: {
      label: label || 'Completed',
      color: 'success' as const,
      icon: <CheckCircleIcon />,
    },
  };

  const config = configs[type];

  return (
    <Chip
      label={config.label}
      color={config.color}
      size={size}
      icon={config.icon}
      sx={{ fontWeight: 500 }}
    />
  );
}

