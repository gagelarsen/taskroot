import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { Delete } from '@mui/icons-material';
import { LineChart } from '@mui/x-charts/LineChart';
import { AxiosError } from 'axios';
import { contractInvoiceUpdatesApi, reportsApi } from '../api/client';
import type { Contract, ContractInvoiceUpdate, ContractTMBurnReport } from '../types/api';

interface TimeMaterialsBurnChartsProps {
  contract: Contract;
}

const usdFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function TimeMaterialsBurnCharts({ contract }: TimeMaterialsBurnChartsProps) {
  const [report, setReport] = useState<ContractTMBurnReport | null>(null);
  const [invoiceUpdates, setInvoiceUpdates] = useState<ContractInvoiceUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [invoiceDate, setInvoiceDate] = useState('');
  const [invoiceAmount, setInvoiceAmount] = useState('');
  const [invoiceNote, setInvoiceNote] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [reportData, updateData] = await Promise.all([
        reportsApi.getContractTMBurn(contract.id),
        contractInvoiceUpdatesApi.list({
          contract_id: contract.id,
          order_by: 'invoice_date',
          order_dir: 'asc',
        }),
      ]);
      setReport(reportData);
      setInvoiceUpdates(updateData);
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.error || err.response?.data?.detail || 'Failed to load T&M report data');
      } else {
        setError('Failed to load T&M report data');
      }
    } finally {
      setLoading(false);
    }
  }, [contract.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAddInvoiceUpdate = async () => {
    if (!invoiceDate || !invoiceAmount) {
      setError('Invoice date and amount are required');
      return;
    }

    setSaving(true);
    setError('');
    try {
      await contractInvoiceUpdatesApi.create({
        contract: contract.id,
        invoice_date: invoiceDate,
        amount: invoiceAmount,
        note: invoiceNote,
      });

      setInvoiceDate('');
      setInvoiceAmount('');
      setInvoiceNote('');
      await loadData();
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to save invoice update');
      } else {
        setError('Failed to save invoice update');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteInvoiceUpdate = async (id: number) => {
    setSaving(true);
    setError('');
    try {
      await contractInvoiceUpdatesApi.delete(id);
      await loadData();
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to delete invoice update');
      } else {
        setError('Failed to delete invoice update');
      }
    } finally {
      setSaving(false);
    }
  };

  const chartSeries = useMemo(() => {
    if (!report) {
      return {
        dates: [] as Date[],
        cumulativeInvoiced: [] as number[],
        remainingContractAmount: [] as number[],
        cumulativeHours: [] as number[],
        weeklyHours: [] as number[],
      };
    }

    return {
      dates: report.buckets.map((bucket) => new Date(bucket.bucket)),
      cumulativeInvoiced: report.buckets.map((bucket) => parseFloat(bucket.cumulative_invoiced)),
      remainingContractAmount: report.buckets.map((bucket) => parseFloat(bucket.remaining_contract_amount)),
      cumulativeHours: report.buckets.map((bucket) => parseFloat(bucket.cumulative_hours)),
      weeklyHours: report.buckets.map((bucket) => parseFloat(bucket.weekly_hours)),
    };
  }, [report]);

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

  return (
    <Stack spacing={3}>
      {error && <Alert severity="error">{error}</Alert>}

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Invoice Burndown
          </Typography>
          {!report || chartSeries.dates.length === 0 ? (
            <Alert severity="info">No report data available</Alert>
          ) : (
            <>
              <LineChart
                xAxis={[{ data: chartSeries.dates, scaleType: 'time', valueFormatter: (date) => date.toLocaleDateString() }]}
                yAxis={[{ label: 'USD' }]}
                series={[
                  { data: chartSeries.cumulativeInvoiced, label: 'Cumulative Invoiced' },
                  { data: chartSeries.remainingContractAmount, label: 'Remaining Contract Amount' },
                ]}
                height={320}
                margin={{ top: 10, right: 10, bottom: 50, left: 80 }}
              />
              <Box sx={{ mt: 2, display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                <Typography variant="body2" color="text.secondary">
                  Contract Amount: <strong>{usdFormatter.format(parseFloat(report.contract_amount))}</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Invoiced: <strong>{usdFormatter.format(parseFloat(report.invoiced_amount))}</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Remaining: <strong>{usdFormatter.format(parseFloat(report.remaining_contract_amount))}</strong>
                </Typography>
              </Box>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Cumulative Hours Spent
          </Typography>
          {!report || chartSeries.dates.length === 0 ? (
            <Alert severity="info">No report data available</Alert>
          ) : (
            <LineChart
              xAxis={[{ data: chartSeries.dates, scaleType: 'time', valueFormatter: (date) => date.toLocaleDateString() }]}
              yAxis={[{ label: 'Hours' }]}
              series={[{ data: chartSeries.cumulativeHours, label: 'Cumulative Hours' }]}
              height={280}
              margin={{ top: 10, right: 10, bottom: 50, left: 80 }}
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Weekly Hours Spent
          </Typography>
          {!report || chartSeries.dates.length === 0 ? (
            <Alert severity="info">No report data available</Alert>
          ) : (
            <LineChart
              xAxis={[{ data: chartSeries.dates, scaleType: 'time', valueFormatter: (date) => date.toLocaleDateString() }]}
              yAxis={[{ label: 'Hours' }]}
              series={[{ data: chartSeries.weeklyHours, label: 'Weekly Hours' }]}
              height={280}
              margin={{ top: 10, right: 10, bottom: 50, left: 80 }}
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Invoiced Amount Updates
          </Typography>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
            <TextField
              label="Invoice Date"
              type="date"
              value={invoiceDate}
              onChange={(event) => setInvoiceDate(event.target.value)}
              InputLabelProps={{ shrink: true }}
              size="small"
            />
            <TextField
              label="Amount (USD)"
              type="number"
              value={invoiceAmount}
              onChange={(event) => setInvoiceAmount(event.target.value)}
              size="small"
              inputProps={{ min: 0.01, step: 0.01 }}
            />
            <TextField
              label="Note"
              value={invoiceNote}
              onChange={(event) => setInvoiceNote(event.target.value)}
              size="small"
              sx={{ flex: 1 }}
            />
            <Button variant="contained" onClick={handleAddInvoiceUpdate} disabled={saving}>
              {saving ? 'Saving...' : 'Add Update'}
            </Button>
          </Stack>

          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Invoice Date</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell>Note</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {invoiceUpdates.map((update) => (
                  <TableRow key={update.id}>
                    <TableCell>{update.invoice_date}</TableCell>
                    <TableCell align="right">{usdFormatter.format(parseFloat(update.amount))}</TableCell>
                    <TableCell>{update.note || '-'}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteInvoiceUpdate(update.id)}
                        disabled={saving}
                        aria-label="Delete invoice update"
                      >
                        <Delete fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
                {invoiceUpdates.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <Typography variant="body2" color="text.secondary">
                        No invoiced updates yet
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Stack>
  );
}
