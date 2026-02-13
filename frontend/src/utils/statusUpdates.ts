import type { ChipProps } from '@mui/material';
import type { DeliverableStatusUpdate } from '../types/api';

export type DeliverableStatus = DeliverableStatusUpdate['status'];

export function formatDeliverableStatusLabel(status: DeliverableStatus): string {
  if (status === 'on_track') return 'On Track';
  if (status === 'at_risk') return 'At Risk';
  return 'Off Track';
}

export function getDeliverableStatusChipColor(status: DeliverableStatus): ChipProps['color'] {
  if (status === 'on_track') return 'success';
  if (status === 'at_risk') return 'warning';
  return 'error';
}
