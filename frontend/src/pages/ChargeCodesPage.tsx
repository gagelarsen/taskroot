import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import { LineChart } from '@mui/x-charts/LineChart';
import { chargeCodesApi, reportsApi } from '../api/client';
import type { ChargeCode, ChargeCodeUsageReport } from '../types/api';
import { getApiErrorMessage } from '../utils/apiErrors';
import { todayIsoDateOnly } from '../utils/dateHelpers';

function defaultStartDate(): string {
  const date = new Date();
  date.setDate(date.getDate() - 84);
  return date.toISOString().split('T')[0];
}

export function ChargeCodesPage() {
  const [chargeCodes, setChargeCodes] = useState<ChargeCode[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [savingAllAllotted, setSavingAllAllotted] = useState(false);
  const [savingAllottedId, setSavingAllottedId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const [report, setReport] = useState<ChargeCodeUsageReport | null>(null);
  const [allottedDrafts, setAllottedDrafts] = useState<Record<number, string>>({});
  const [activeTab, setActiveTab] = useState<'plot' | 'allotted'>('plot');

  const [mode, setMode] = useState<'charge_code' | 'base_code'>('charge_code');
  const [selectedChargeCode, setSelectedChargeCode] = useState('');
  const [selectedBaseCode, setSelectedBaseCode] = useState('');
  const [startDate, setStartDate] = useState(defaultStartDate());
  const [endDate, setEndDate] = useState(todayIsoDateOnly());

  const loadChargeCodes = useCallback(async () => {
    setLoadingOptions(true);
    setError('');

    try {
      const data: ChargeCode[] = await chargeCodesApi.list({ is_active: true, order_by: 'code', order_dir: 'asc' });
      setChargeCodes(data);
      setAllottedDrafts(
        data.reduce((current: Record<number, string>, chargeCode: ChargeCode) => {
          current[chargeCode.id] = chargeCode.allotted_hours ?? '';
          return current;
        }, {})
      );
      if (data.length > 0 && !selectedChargeCode) {
        setSelectedChargeCode(data[0].code);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to load charge codes'));
    } finally {
      setLoadingOptions(false);
    }
  }, [selectedChargeCode]);

  useEffect(() => {
    void loadChargeCodes();
  }, [loadChargeCodes]);

  const baseCodeOptions = useMemo(() => {
    return Array.from(
      new Set(
        chargeCodes
          .map((chargeCode) => chargeCode.code.split(':')[0]?.trim())
          .filter((value): value is string => Boolean(value))
      )
    ).sort((a, b) => a.localeCompare(b));
  }, [chargeCodes]);

  useEffect(() => {
    if (baseCodeOptions.length > 0 && !selectedBaseCode) {
      setSelectedBaseCode(baseCodeOptions[0]);
    }
  }, [baseCodeOptions, selectedBaseCode]);

  const loadReport = useCallback(async () => {
    setLoadingReport(true);
    setError('');
    setSaveMessage('');

    try {
      const params = {
        start_date: startDate,
        end_date: endDate,
        ...(mode === 'charge_code' ? { charge_code: selectedChargeCode } : { base_code: selectedBaseCode }),
      };
      const data = await reportsApi.getChargeCodeUsage(params);
      setReport(data);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to load charge code report'));
      setReport(null);
    } finally {
      setLoadingReport(false);
    }
  }, [endDate, mode, selectedBaseCode, selectedChargeCode, startDate]);

  useEffect(() => {
    if (!loadingOptions && ((mode === 'charge_code' && selectedChargeCode) || (mode === 'base_code' && selectedBaseCode))) {
      void loadReport();
    }
  }, [loadReport, loadingOptions, mode, selectedBaseCode, selectedChargeCode]);

  const canRunReport = mode === 'charge_code' ? Boolean(selectedChargeCode) : Boolean(selectedBaseCode);

  const hasAllottedChanges = chargeCodes.some((chargeCode) => {
    const currentValue = (chargeCode.allotted_hours ?? '').trim();
    const draftValue = (allottedDrafts[chargeCode.id] ?? '').trim();
    return currentValue !== draftValue;
  });

  const handleSaveAllottedHours = async (chargeCode: ChargeCode) => {
    const draftValue = (allottedDrafts[chargeCode.id] ?? '').trim();

    if (draftValue && Number.isNaN(Number(draftValue))) {
      setError(`Allotted hours must be numeric for ${chargeCode.code}.`);
      setSaveMessage('');
      return;
    }

    if (draftValue && Number(draftValue) < 0) {
      setError(`Allotted hours must be zero or greater for ${chargeCode.code}.`);
      setSaveMessage('');
      return;
    }

    setSavingAllottedId(chargeCode.id);
    setError('');
    setSaveMessage('');

    try {
      await chargeCodesApi.update(chargeCode.id, {
        allotted_hours: draftValue === '' ? null : Number(draftValue).toFixed(2),
      });
      setSaveMessage(`Saved allotted hours for ${chargeCode.code}.`);
      await loadChargeCodes();
      if ((mode === 'charge_code' && selectedChargeCode === chargeCode.code) || mode === 'base_code') {
        await loadReport();
      }
    } catch (err) {
      setError(getApiErrorMessage(err, `Failed to save allotted hours for ${chargeCode.code}`));
    } finally {
      setSavingAllottedId(null);
    }
  };

  const handleSaveAllAllottedHours = async () => {
    setError('');
    setSaveMessage('');

    const changedChargeCodes = chargeCodes.filter((chargeCode) => {
      const currentValue = (chargeCode.allotted_hours ?? '').trim();
      const draftValue = (allottedDrafts[chargeCode.id] ?? '').trim();
      return currentValue !== draftValue;
    });

    if (changedChargeCodes.length === 0) {
      return;
    }

    for (const chargeCode of changedChargeCodes) {
      const draftValue = (allottedDrafts[chargeCode.id] ?? '').trim();
      if (draftValue && Number.isNaN(Number(draftValue))) {
        setError(`Allotted hours must be numeric for ${chargeCode.code}.`);
        return;
      }

      if (draftValue && Number(draftValue) < 0) {
        setError(`Allotted hours must be zero or greater for ${chargeCode.code}.`);
        return;
      }
    }

    setSavingAllAllotted(true);

    try {
      for (const chargeCode of changedChargeCodes) {
        const draftValue = (allottedDrafts[chargeCode.id] ?? '').trim();
        await chargeCodesApi.update(chargeCode.id, {
          allotted_hours: draftValue === '' ? null : Number(draftValue).toFixed(2),
        });
      }

      setSaveMessage(`Saved allotted hours for ${changedChargeCodes.length} charge code(s).`);
      await loadChargeCodes();
      await loadReport();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to save all allotted hours'));
    } finally {
      setSavingAllAllotted(false);
    }
  };

  const chartXAxis = report?.buckets.map((bucket) => bucket.bucket) ?? [];
  const cumulativeActualSeries = report?.buckets.map((bucket) => Number(bucket.cumulative_actual)) ?? [];
  const cumulativeExpectedSeries =
    report?.buckets.map((bucket) => (bucket.cumulative_expected ? Number(bucket.cumulative_expected) : null)) ?? [];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Charge Codes
      </Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, value) => setActiveTab(value)}>
          <Tab value="plot" label="Plot" />
          <Tab value="allotted" label="Allotted Hours" />
        </Tabs>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {saveMessage && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {saveMessage}
        </Alert>
      )}

      {activeTab === 'plot' && (
        <>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
                <TextField
                  select
                  label="View"
                  value={mode}
                  onChange={(event) => setMode(event.target.value as 'charge_code' | 'base_code')}
                  fullWidth
                >
                  <MenuItem value="charge_code">Charge Code</MenuItem>
                  <MenuItem value="base_code">Base Code</MenuItem>
                </TextField>

                {mode === 'charge_code' ? (
                  <TextField
                    select
                    label="Charge Code"
                    value={selectedChargeCode}
                    onChange={(event) => setSelectedChargeCode(event.target.value)}
                    fullWidth
                  >
                    {chargeCodes.map((chargeCode) => (
                      <MenuItem key={chargeCode.id} value={chargeCode.code}>
                        {chargeCode.code}
                      </MenuItem>
                    ))}
                  </TextField>
                ) : (
                  <TextField
                    select
                    label="Base Code"
                    value={selectedBaseCode}
                    onChange={(event) => setSelectedBaseCode(event.target.value)}
                    fullWidth
                  >
                    {baseCodeOptions.map((baseCode) => (
                      <MenuItem key={baseCode} value={baseCode}>
                        {baseCode}
                      </MenuItem>
                    ))}
                  </TextField>
                )}

                <TextField
                  label="Start Date"
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />

                <TextField
                  label="End Date"
                  type="date"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />

                <Button variant="contained" onClick={() => void loadReport()} disabled={!canRunReport || loadingReport}>
                  Run Report
                </Button>
              </Stack>
            </CardContent>
          </Card>

          {(loadingOptions || loadingReport) && (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {!loadingReport && report && (
            <>
              <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
                <Box sx={{ flex: '1 1 220px' }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary">Allotted Hours</Typography>
                      <Typography variant="h5">{report.allotted_hours ?? 'Not set'}</Typography>
                    </CardContent>
                  </Card>
                </Box>
                <Box sx={{ flex: '1 1 220px' }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary">Spent Hours</Typography>
                      <Typography variant="h5">{report.spent_hours}</Typography>
                    </CardContent>
                  </Card>
                </Box>
                <Box sx={{ flex: '1 1 220px' }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary">Remaining Hours</Typography>
                      <Typography variant="h5">{report.remaining_hours ?? 'N/A'}</Typography>
                    </CardContent>
                  </Card>
                </Box>
                <Box sx={{ flex: '1 1 220px' }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary">Status</Typography>
                      <Typography variant="h5" color={report.is_over_allotted ? 'error.main' : 'success.main'}>
                        {report.is_over_allotted ? 'Over Allotted' : 'On Track'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>
              </Box>

              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Cumulative Burn
                  </Typography>
                  <LineChart
                    height={360}
                    xAxis={[{ scaleType: 'point', data: chartXAxis }]}
                    series={[
                      { label: 'Cumulative Actual', data: cumulativeActualSeries },
                      { label: 'Cumulative Expected', data: cumulativeExpectedSeries },
                    ]}
                    margin={{ top: 20, right: 20, bottom: 40, left: 50 }}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardContent>
                  <Typography variant="body2" color="text.secondary">
                    Included charge codes: {report.matched_charge_codes.join(', ')}
                  </Typography>
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}

      {activeTab === 'allotted' && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1} sx={{ mb: 1 }}>
              <Typography variant="h6">Allotted Hours</Typography>
              <Button
                variant="contained"
                onClick={() => void handleSaveAllAllottedHours()}
                disabled={savingAllAllotted || !hasAllottedChanges}
              >
                Save All
              </Button>
            </Stack>
            <Stack spacing={1.5}>
              {chargeCodes.map((chargeCode) => {
                const draftValue = allottedDrafts[chargeCode.id] ?? '';
                const isDirty = (chargeCode.allotted_hours ?? '').trim() !== draftValue.trim();
                return (
                  <Stack key={chargeCode.id} direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems="center">
                    <Box sx={{ flex: 1, width: '100%' }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2">{chargeCode.code}</Typography>
                        {isDirty && <Chip label="Unsaved" size="small" color="warning" variant="outlined" />}
                      </Stack>
                    </Box>
                    <TextField
                      label="Allotted Hours"
                      type="number"
                      size="small"
                      value={draftValue}
                      onChange={(event) =>
                        setAllottedDrafts((current) => ({
                          ...current,
                          [chargeCode.id]: event.target.value,
                        }))
                      }
                      inputProps={{ min: 0, step: '0.01' }}
                      sx={{ minWidth: 180 }}
                    />
                    <Button
                      variant="outlined"
                      onClick={() => void handleSaveAllottedHours(chargeCode)}
                      disabled={savingAllottedId === chargeCode.id || savingAllAllotted || !isDirty}
                    >
                      Save
                    </Button>
                  </Stack>
                );
              })}
            </Stack>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
