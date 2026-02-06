import { Chip } from '@mui/material';
import { getTargetDateStatus, getTargetDateLabel, getTargetDateColor } from '../utils/dateHelpers';

interface TargetDateBadgeProps {
  targetDate: string | null | undefined;
  showIfNone?: boolean;
}

/**
 * Badge component that displays the status of a target completion date
 */
export function TargetDateBadge({ targetDate, showIfNone = false }: TargetDateBadgeProps) {
  const status = getTargetDateStatus(targetDate);

  // Don't show badge if there's no target date and showIfNone is false
  if (status === 'none' && !showIfNone) {
    return null;
  }

  // Don't show badge for future dates (beyond next month)
  if (status === 'future') {
    return null;
  }

  return (
    <Chip
      label={getTargetDateLabel(status)}
      color={getTargetDateColor(status)}
      size="small"
      sx={{ fontWeight: 500 }}
    />
  );
}

