import type { ChipProps } from '@mui/material';
import type { Contract } from '../types/api';

export type ContractStatus = Contract['status'];

export const CONTRACT_STATUS_OPTIONS: Array<{ value: ContractStatus; label: string }> = [
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'closed', label: 'Closed' },
];

export function formatContractStatusLabel(status: ContractStatus): string {
  if (status === 'draft') return 'Draft';
  if (status === 'active') return 'Active';
  return 'Closed';
}

export function getContractStatusChipColor(status: ContractStatus): ChipProps['color'] {
  if (status === 'draft') return 'default';
  if (status === 'active') return 'success';
  return 'info';
}
