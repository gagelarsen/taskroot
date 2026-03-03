import { useState, useEffect } from 'react';
import { Card, CardContent, Typography, CircularProgress, Alert, Box } from '@mui/material';
import { LineChart } from '@mui/x-charts/LineChart';
import type { AxiosResponse } from 'axios';
import { apiClient } from '../api/client';
import type { Contract } from '../types/api';
import { toIsoDateOnly } from '../utils/dateHelpers';

interface TimeEntry {
  id: number;
  deliverable: number;
  entry_date: string;
  hours: string;
  note: string;
  created_at: string;
  updated_at: string;
}

interface PaginatedTimeEntriesResponse {
  results: TimeEntry[];
  next: string | null;
}

interface BurnDownChartProps {
  contract: Contract;
}

export function BurnDownChart({ contract }: BurnDownChartProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [chartData, setChartData] = useState<{
    dates: Date[];
    budgetLine: number[];
    spentLine: number[];
    remainingLine: number[];
    trendLine: (number | null)[];
  }>({ dates: [], budgetLine: [], spentLine: [], remainingLine: [], trendLine: [] });

  useEffect(() => {
    const loadTimeEntries = async () => {
      setLoading(true);
      setError('');
      try {
        // Fetch all time entries for this contract
        // Loop through all pages to get ALL entries (in case pagination limit is enforced)
        let allTimeEntries: TimeEntry[] = [];
        let nextUrl: string | null = '/deliverable-time-entries/';
        let pageNum = 1;

        while (nextUrl) {
          const response: AxiosResponse<PaginatedTimeEntriesResponse | TimeEntry[]> = await apiClient.get(nextUrl, {
            params: nextUrl === '/deliverable-time-entries/' ? {
              contract_id: contract.id,
              order_by: 'entry_date',
              order_dir: 'asc',
              page_size: 10000, // Try to get all in one request
            } : undefined, // For subsequent pages, use the next URL as-is
          });

          // Handle paginated response - DRF returns { results: [...], count, next, previous }
          const pageEntries: TimeEntry[] = Array.isArray(response.data)
            ? response.data
            : response.data.results;
          allTimeEntries = [...allTimeEntries, ...pageEntries];

          console.log(`BurnDownChart: Loaded page ${pageNum} - ${pageEntries.length} entries (total so far: ${allTimeEntries.length})`);

          // Check if there's a next page
          nextUrl = Array.isArray(response.data) ? null : response.data.next || null;
          pageNum++;

          // Safety check to prevent infinite loops
          if (pageNum > 100) {
            console.error('BurnDownChart: Too many pages, stopping at 100 pages');
            break;
          }
        }

        const timeEntries = allTimeEntries;

        console.log('BurnDownChart: Loaded time entries for contract', contract.id, ':', timeEntries.length, 'entries');
        console.log('BurnDownChart: Total hours from entries:', timeEntries.reduce((sum, e) => sum + parseFloat(e.hours), 0));
        console.log('BurnDownChart: Contract budget_hours:', contract.budget_hours);
        console.log('BurnDownChart: Contract spent_hours:', contract.spent_hours);

        if (!timeEntries || timeEntries.length === 0) {
          setChartData({ dates: [], budgetLine: [], spentLine: [], remainingLine: [], trendLine: [] });
          setLoading(false);
          return;
        }

        // Group time entries by date and calculate cumulative hours
        const entriesByDate = new Map<string, number>();
        timeEntries.forEach((entry) => {
          const date = entry.entry_date;
          const hours = parseFloat(entry.hours);
          entriesByDate.set(date, (entriesByDate.get(date) || 0) + hours);
        });

        console.log('BurnDownChart: Entries grouped by date:', Array.from(entriesByDate.entries()));

        // Sort dates and calculate cumulative values
        const sortedDates = Array.from(entriesByDate.keys()).sort();
        const dates: Date[] = [];
        const spentLine: number[] = [];
        const budgetLine: number[] = [];
        const remainingLine: number[] = [];

        let cumulativeSpent = 0;
        const budgetHours = parseFloat(contract.budget_hours);

        // Add contract start date as the first point
        if (contract.start_date) {
          dates.push(new Date(contract.start_date));
          spentLine.push(0);
          budgetLine.push(budgetHours);
          remainingLine.push(budgetHours);
        }

        // Add data points for each date with time entries
        sortedDates.forEach((dateStr) => {
          const hours = entriesByDate.get(dateStr) || 0;
          cumulativeSpent += hours;

          dates.push(new Date(dateStr));
          spentLine.push(cumulativeSpent);
          budgetLine.push(budgetHours);
          remainingLine.push(Math.max(0, budgetHours - cumulativeSpent));
        });

        // Calculate trend line (linear regression from spent hours)
        const trendLine: (number | null)[] = new Array(dates.length).fill(null);

        if (spentLine.length >= 2) {
          // Use only the actual time entry dates (not start/end dates) for trend calculation
          const dataPoints: { x: number; y: number }[] = [];

          sortedDates.forEach((dateStr) => {
            const dateIndex = dates.findIndex((date) => toIsoDateOnly(date) === dateStr);
            if (dateIndex >= 0) {
              dataPoints.push({
                x: dates[dateIndex].getTime(),
                y: spentLine[dateIndex],
              });
            }
          });

          if (dataPoints.length >= 2) {
            // Calculate linear regression (y = mx + b)
            const n = dataPoints.length;
            const sumX = dataPoints.reduce((sum, p) => sum + p.x, 0);
            const sumY = dataPoints.reduce((sum, p) => sum + p.y, 0);
            const sumXY = dataPoints.reduce((sum, p) => sum + p.x * p.y, 0);
            const sumX2 = dataPoints.reduce((sum, p) => sum + p.x * p.x, 0);

            const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
            const intercept = (sumY - slope * sumX) / n;

            // Start trend line from the last actual data point
            const lastDataPointIndex = dates.findIndex(
              (date) => toIsoDateOnly(date) === sortedDates[sortedDates.length - 1]
            );

            if (lastDataPointIndex >= 0) {
              // Fill trend line with the actual value at the last data point
              trendLine[lastDataPointIndex] = spentLine[lastDataPointIndex];

              // Project trend forward from the last data point
              const lastDataDate = dates[lastDataPointIndex];
              const lastDataHours = spentLine[lastDataPointIndex];

              // Calculate how many more hours we need to reach the budget
              const remainingHours = budgetHours - lastDataHours;

              if (remainingHours > 0 && slope > 0) {
                // Calculate when we'll reach the budget based on the trend
                const hoursPerMs = slope;
                const msToCompletion = remainingHours / hoursPerMs;
                const projectedCompletionDate = new Date(lastDataDate.getTime() + msToCompletion);

                // Add intermediate points and the completion point
                for (let i = lastDataPointIndex + 1; i < dates.length; i++) {
                  const projectedHours = slope * dates[i].getTime() + intercept;
                  trendLine[i] = Math.min(projectedHours, budgetHours); // Cap at budget
                }

                // Add the projected completion date if it's beyond our current range
                const lastDate = dates[dates.length - 1];
                if (projectedCompletionDate > lastDate) {
                  dates.push(projectedCompletionDate);
                  spentLine.push(lastDataHours); // Keep actual spent flat
                  budgetLine.push(budgetHours);
                  remainingLine.push(Math.max(0, budgetHours - lastDataHours));
                  trendLine.push(budgetHours); // Trend reaches budget
                }
              } else if (remainingHours <= 0) {
                // Already over budget, just extend the trend line to show the trajectory
                for (let i = lastDataPointIndex + 1; i < dates.length; i++) {
                  const projectedHours = slope * dates[i].getTime() + intercept;
                  trendLine[i] = projectedHours;
                }
              }
            }
          }
        }

        // Add contract end date as the last point (if it exists and is after the last entry)
        if (contract.end_date) {
          const endDate = new Date(contract.end_date);
          const lastEntryDate = dates[dates.length - 1];
          if (!lastEntryDate || endDate > lastEntryDate) {
            dates.push(endDate);
            spentLine.push(cumulativeSpent);
            budgetLine.push(budgetHours);
            remainingLine.push(Math.max(0, budgetHours - cumulativeSpent));
            trendLine.push(null); // No trend at contract end date
          }
        }

        setChartData({ dates, budgetLine, spentLine, remainingLine, trendLine });
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } };
        setError(error.response?.data?.detail || 'Failed to load time entries');
      } finally {
        setLoading(false);
      }
    };

    loadTimeEntries();
  }, [contract]);

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error">{error}</Alert>
        </CardContent>
      </Card>
    );
  }

  if (chartData.dates.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Burn Down Chart
          </Typography>
          <Alert severity="info">No time entries found for this contract</Alert>
        </CardContent>
      </Card>
    );
  }

  const totalSpent = chartData.spentLine.length > 0 ? chartData.spentLine[chartData.spentLine.length - 1] : 0;
  const budgetHours = parseFloat(contract.budget_hours);
  const remaining = budgetHours - totalSpent;

  // Find the projected completion date (where trend line reaches budget)
  let projectedCompletionDate: Date | null = null;
  for (let i = 0; i < chartData.trendLine.length; i++) {
    const trendValue = chartData.trendLine[i];
    if (trendValue !== null && trendValue >= budgetHours) {
      projectedCompletionDate = chartData.dates[i];
      break;
    }
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Burn Down Chart
        </Typography>
        <LineChart
          xAxis={[
            {
              data: chartData.dates,
              scaleType: 'time',
              valueFormatter: (date) => date.toLocaleDateString(),
            },
          ]}
          yAxis={[
            {
              label: 'Hours',
            },
          ]}
          series={[
            {
              data: chartData.budgetLine,
              label: 'Budget Hours',
              color: '#90caf9',
              curve: 'linear',
              showMark: false,
            },
            {
              data: chartData.spentLine,
              label: 'Cumulative Spent Hours',
              color: '#f44336',
              curve: 'linear',
              showMark: true,
            },
            {
              data: chartData.remainingLine,
              label: 'Remaining Budget',
              color: '#66bb6a',
              curve: 'linear',
              showMark: false,
            },
            {
              data: chartData.trendLine,
              label: 'Projected Trend',
              color: '#ff9800',
              curve: 'linear',
              showMark: false,
            },
          ]}
          height={400}
          margin={{ top: 10, right: 10, bottom: 50, left: 80 }}
          slotProps={{
            legend: {
              direction: 'horizontal',
              position: { vertical: 'top', horizontal: 'center' },
            },
          }}
        />
        <Box sx={{ mt: 2, display: 'flex', gap: 3, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Typography variant="body2" color="text.secondary">
            Budget: <strong>{budgetHours.toFixed(1)}h</strong>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Spent: <strong>{totalSpent.toFixed(1)}h</strong>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Remaining: <strong>{remaining.toFixed(1)}h</strong>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Time Entries: <strong>{chartData.dates.length - (contract.start_date ? 1 : 0) - (contract.end_date ? 1 : 0)}</strong> dates
          </Typography>
          {projectedCompletionDate && remaining > 0 && (
            <Typography variant="body2" color="warning.main">
              Projected Completion: <strong>{projectedCompletionDate.toLocaleDateString()}</strong>
            </Typography>
          )}
          {remaining < 0 && (
            <Typography variant="body2" color="error.main">
              Over Budget: <strong>{Math.abs(remaining).toFixed(1)}h</strong>
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

