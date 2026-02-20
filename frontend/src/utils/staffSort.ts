import type { Staff } from '../types/api';

export function getStaffDisplayName(staff: Pick<Staff, 'first_name' | 'last_name'>): string {
  return `${staff.first_name} ${staff.last_name}`.trim();
}

export function sortStaffByName<T extends Pick<Staff, 'first_name' | 'last_name'>>(staff: T[]): T[] {
  return [...staff].sort((left, right) =>
    getStaffDisplayName(left).localeCompare(getStaffDisplayName(right), undefined, {
      sensitivity: 'base',
    })
  );
}
