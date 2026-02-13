import type { ChipProps } from '@mui/material';
import type { Deliverable } from '../types/api';

export type DeliverableLifecycleStatus = Deliverable['status'];

export function formatDeliverableLifecycleStatusLabel(status: DeliverableLifecycleStatus): string {
  if (status === 'not_started' || status === 'planned') return 'Planned';
  if (status === 'in_progress') return 'In Progress';
  if (status === 'complete' || status === 'completed') return 'Complete';
  if (status === 'on_hold') return 'On Hold';
  return 'Blocked';
}

export function getDeliverableLifecycleStatusChipColor(
  status: DeliverableLifecycleStatus
): ChipProps['color'] {
  if (status === 'complete' || status === 'completed') return 'success';
  if (status === 'in_progress') return 'info';
  if (status === 'on_hold') return 'warning';
  if (status === 'blocked') return 'error';
  return 'default';
}
