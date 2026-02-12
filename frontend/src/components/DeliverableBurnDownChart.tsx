import { useState, useEffect } from 'react';
import { Card, CardContent, Typography, CircularProgress, Alert, Box } from '@mui/material';
import { LineChart } from '@mui/x-charts/LineChart';
import type { AxiosResponse } from 'axios';
import { apiClient } from '../api/client';
import type { Deliverable } from '../types/api';

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

interface DeliverableBurnDownChartProps {
  deliverable: Deliverable;
}

export function DeliverableBurnDownChart({ deliverable }: DeliverableBurnDownChartProps) {
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
        // Fetch all time entries for this deliverable
        // Loop through all pages to get ALL entries
        let allTimeEntries: TimeEntry[] = [];
        let nextUrl: string | null = '/deliverable-time-entries/';
        let pageNum = 1;

        while (nextUrl) {
          const response: AxiosResponse<PaginatedTimeEntriesResponse | TimeEntry[]> = await apiClient.get(nextUrl, {
            params: nextUrl === '/deliverable-time-entries/' ? {
              deliverable_id: deliverable.id,
              order_by: 'entry_date',
              order_dir: 'asc',
              page_size: 10000,
            } : undefined,
          });

          const pageEntries: TimeEntry[] = Array.isArray(response.data)
            ? response.data
            : response.data.results;
          allTimeEntries = [...allTimeEntries, ...pageEntries];

          nextUrl = Array.isArray(response.data) ? null : response.data.next || null;
          pageNum++;

          if (pageNum > 100) {
            console.error('DeliverableBurnDownChart: Too many pages, stopping at 100 pages');
            break;
          }
        }

        const timeEntries = allTimeEntries;

        console.log('DeliverableBurnDownChart: Loaded time entries for deliverable', deliverable.id, ':', timeEntries.length, 'entries');

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

        // Sort dates and calculate cumulative values
        const sortedDates = Array.from(entriesByDate.keys()).sort();
        const dates: Date[] = [];
        const spentLine: number[] = [];
        const budgetLine: number[] = [];
        const remainingLine: number[] = [];

        let cumulativeSpent = 0;
        const budgetHours = parseFloat(deliverable.budget_hours);

        // Add first entry date as starting point
        if (sortedDates.length > 0) {
          const firstDate = new Date(sortedDates[0]);
          dates.push(firstDate);
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
          // Use only the actual time entry dates for trend calculation
          const dataPoints: { x: number; y: number }[] = [];
          
          sortedDates.forEach((dateStr) => {
            const dateIndex = dates.findIndex(d => d.toISOString().split('T')[0] === dateStr);
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
              d => d.toISOString().split('T')[0] === sortedDates[sortedDates.length - 1]
            );

            if (lastDataPointIndex >= 0) {
              trendLine[lastDataPointIndex] = spentLine[lastDataPointIndex];

              const lastDataDate = dates[lastDataPointIndex];
              const lastDataHours = spentLine[lastDataPointIndex];

              const remainingHours = budgetHours - lastDataHours;

              if (remainingHours > 0 && slope > 0) {
                const hoursPerMs = slope;
                const msToCompletion = remainingHours / hoursPerMs;
                const projectedCompletionDate = new Date(lastDataDate.getTime() + msToCompletion);

                for (let i = lastDataPointIndex + 1; i < dates.length; i++) {
                  const projectedHours = slope * dates[i].getTime() + intercept;
                  trendLine[i] = Math.min(projectedHours, budgetHours);
                }

                const lastDate = dates[dates.length - 1];
                if (projectedCompletionDate > lastDate) {
                  dates.push(projectedCompletionDate);
                  spentLine.push(lastDataHours);
                  budgetLine.push(budgetHours);
                  remainingLine.push(Math.max(0, budgetHours - lastDataHours));
                  trendLine.push(budgetHours);
                }
              } else if (remainingHours <= 0) {
                for (let i = lastDataPointIndex + 1; i < dates.length; i++) {
                  const projectedHours = slope * dates[i].getTime() + intercept;
                  trendLine[i] = projectedHours;
                }
              }
            }
          }
        }

        // Add target completion date if it exists and is after the last entry
        if (deliverable.target_completion_date) {
          const targetDate = new Date(deliverable.target_completion_date);
          const lastEntryDate = dates[dates.length - 1];
          if (!lastEntryDate || targetDate > lastEntryDate) {
            dates.push(targetDate);
            spentLine.push(cumulativeSpent);
            budgetLine.push(budgetHours);
            remainingLine.push(Math.max(0, budgetHours - cumulativeSpent));
            trendLine.push(null);
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
  }, [deliverable]);

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
          <Alert severity="info">No time entries found for this deliverable</Alert>
        </CardContent>
      </Card>
    );
  }

  const totalSpent = chartData.spentLine.length > 0 ? chartData.spentLine[chartData.spentLine.length - 1] : 0;
  const budgetHours = parseFloat(deliverable.budget_hours);
  const remaining = budgetHours - totalSpent;

  // Find the projected completion date
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


