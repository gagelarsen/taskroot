import type { ChipProps } from '@mui/material';
import type { Task } from '../types/api';

export type TaskStatus = Task['status'];

export const TASK_STATUS_OPTIONS: Array<{ value: TaskStatus; label: string }> = [
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'done', label: 'Done' },
  { value: 'blocked', label: 'Blocked' },
];

export function formatTaskStatusLabel(status: TaskStatus): string {
  if (status === 'todo') return 'To Do';
  if (status === 'in_progress') return 'In Progress';
  if (status === 'done') return 'Done';
  return 'Blocked';
}

export function getTaskStatusChipColor(status: TaskStatus): ChipProps['color'] {
  if (status === 'done') return 'success';
  if (status === 'in_progress') return 'info';
  if (status === 'blocked') return 'error';
  return 'default';
}
