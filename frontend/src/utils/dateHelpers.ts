/**
 * Utility functions for date handling and comparison
 */

export type TargetDateStatus = 'past_due' | 'this_month' | 'next_month' | 'future' | 'none';

/**
 * Determines the status of a target completion date relative to today
 */
export function getTargetDateStatus(targetDate: string | null | undefined): TargetDateStatus {
  if (!targetDate) return 'none';

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const target = new Date(targetDate);
  target.setHours(0, 0, 0, 0);

  // Past due
  if (target < today) {
    return 'past_due';
  }

  const currentMonth = today.getMonth();
  const currentYear = today.getFullYear();
  const targetMonth = target.getMonth();
  const targetYear = target.getFullYear();

  // This month
  if (targetYear === currentYear && targetMonth === currentMonth) {
    return 'this_month';
  }

  // Next month
  const nextMonth = currentMonth === 11 ? 0 : currentMonth + 1;
  const nextMonthYear = currentMonth === 11 ? currentYear + 1 : currentYear;

  if (targetYear === nextMonthYear && targetMonth === nextMonth) {
    return 'next_month';
  }

  // Future (beyond next month)
  return 'future';
}

/**
 * Gets a human-readable label for the target date status
 */
export function getTargetDateLabel(status: TargetDateStatus): string {
  switch (status) {
    case 'past_due':
      return 'Past Due';
    case 'this_month':
      return 'Due This Month';
    case 'next_month':
      return 'Due Next Month';
    case 'future':
      return 'Future';
    case 'none':
      return 'No Target Date';
  }
}

/**
 * Gets the color for the target date status badge
 */
export function getTargetDateColor(status: TargetDateStatus): 'error' | 'warning' | 'info' | 'default' {
  switch (status) {
    case 'past_due':
      return 'error';
    case 'this_month':
      return 'warning';
    case 'next_month':
      return 'info';
    default:
      return 'default';
  }
}

