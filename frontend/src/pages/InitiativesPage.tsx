import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
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
import { Add } from '@mui/icons-material';
import { AxiosError } from 'axios';
import { initiativeWeeklyUpdatesApi, initiativesApi, staffApi } from '../api/client';
import type { Initiative, Staff } from '../types/api';

const MS_PER_DAY = 1000 * 60 * 60 * 24;

function daysSince(dateValue: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const date = new Date(dateValue);
  date.setHours(0, 0, 0, 0);
  return Math.floor((today.getTime() - date.getTime()) / MS_PER_DAY);
}

export function InitiativesPage() {
  const [initiatives, setInitiatives] = useState<Initiative[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | Initiative['status']>('all');
  const [showStaleOnly, setShowStaleOnly] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    owner: '',
    status: 'active' as Initiative['status'],
    target_date: '',
    notes: '',
  });

  const [quickUpdateInitiativeId, setQuickUpdateInitiativeId] = useState<number | null>(null);
  const [quickUpdatePeriodEnd, setQuickUpdatePeriodEnd] = useState(new Date().toISOString().split('T')[0]);
  const [quickUpdatePercent, setQuickUpdatePercent] = useState('0');
  const [quickUpdateSummary, setQuickUpdateSummary] = useState('');
  const [savingQuickUpdate, setSavingQuickUpdate] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [initiativeData, staffData] = await Promise.all([
        initiativesApi.list({ order_by: 'id', order_dir: 'desc' }),
        staffApi.list({ order_by: 'id', order_dir: 'asc' }),
      ]);
      setInitiatives(initiativeData);
      setStaff(staffData);
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to load initiatives');
      } else {
        setError('Failed to load initiatives');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const filteredInitiatives = useMemo(() => {
    const query = search.trim().toLowerCase();
    return initiatives.filter((initiative) => {
      if (query) {
        const inName = initiative.name.toLowerCase().includes(query);
        const inOwner = (initiative.owner_name || '').toLowerCase().includes(query);
        const inNotes = initiative.notes.toLowerCase().includes(query);
        if (!inName && !inOwner && !inNotes) {
          return false;
        }
      }
      if (statusFilter !== 'all' && initiative.status !== statusFilter) {
        return false;
      }
      if (showStaleOnly && !initiative.is_update_stale) {
        return false;
      }
      return true;
    });
  }, [initiatives, search, statusFilter, showStaleOnly]);

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    try {
      await initiativesApi.create({
        name: formData.name,
        owner: formData.owner ? Number(formData.owner) : null,
        status: formData.status,
        target_date: formData.target_date || null,
        notes: formData.notes,
      });
      setCreateOpen(false);
      setFormData({ name: '', owner: '', status: 'active', target_date: '', notes: '' });
      await loadData();
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to create initiative');
      } else {
        setError('Failed to create initiative');
      }
    } finally {
      setCreating(false);
    }
  };

  const openQuickUpdate = (initiative: Initiative) => {
    setQuickUpdateInitiativeId(initiative.id);
    setQuickUpdatePeriodEnd(new Date().toISOString().split('T')[0]);
    setQuickUpdatePercent(initiative.current_percent_complete || '0');
    setQuickUpdateSummary('');
  };

  const saveQuickUpdate = async () => {
    if (!quickUpdateInitiativeId) {
      return;
    }

    setSavingQuickUpdate(true);
    setError('');
    try {
      await initiativeWeeklyUpdatesApi.create({
        initiative: quickUpdateInitiativeId,
        period_end: quickUpdatePeriodEnd,
        percent_complete: quickUpdatePercent,
        summary: quickUpdateSummary,
      });
      setQuickUpdateInitiativeId(null);
      await loadData();
    } catch (err) {
      if (err instanceof AxiosError) {
        const data = err.response?.data;
        if (typeof data === 'object' && data) {
          const values = Object.values(data as Record<string, unknown>);
          const first = values.find((value) => typeof value === 'string' || (Array.isArray(value) && value.length));
          if (typeof first === 'string') {
            setError(first);
          } else if (Array.isArray(first) && typeof first[0] === 'string') {
            setError(first[0]);
          } else {
            setError('Failed to save weekly update');
          }
        } else {
          setError('Failed to save weekly update');
        }
      } else {
        setError('Failed to save weekly update');
      }
    } finally {
      setSavingQuickUpdate(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Initiatives</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => setCreateOpen(true)}>
          Add Initiative
        </Button>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Track non-contract activities with weekly percent-complete updates.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
        <TextField
          label="Search"
          size="small"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          sx={{ minWidth: 220 }}
        />
        <TextField
          select
          label="Status"
          size="small"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value as 'all' | Initiative['status'])}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="all">All</MenuItem>
          <MenuItem value="active">Active</MenuItem>
          <MenuItem value="on_hold">On Hold</MenuItem>
          <MenuItem value="completed">Completed</MenuItem>
        </TextField>
        <TextField
          select
          label="Update Health"
          size="small"
          value={showStaleOnly ? 'stale' : 'all'}
          onChange={(event) => setShowStaleOnly(event.target.value === 'stale')}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="all">All</MenuItem>
          <MenuItem value="stale">Stale only</MenuItem>
        </TextField>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Initiative</TableCell>
                <TableCell>Owner</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">% Complete</TableCell>
                <TableCell>Latest Update</TableCell>
                <TableCell>Update Health</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredInitiatives.map((initiative) => {
                const latest = initiative.latest_update;
                const isQuickOpen = quickUpdateInitiativeId === initiative.id;
                return (
                  <>
                    <TableRow key={initiative.id}>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{initiative.name}</Typography>
                        {initiative.target_date && (
                          <Typography variant="caption" color="text.secondary">
                            Target: {initiative.target_date}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>{initiative.owner_name || 'Unassigned'}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={initiative.status === 'on_hold' ? 'On Hold' : initiative.status === 'completed' ? 'Completed' : 'Active'}
                          color={initiative.status === 'completed' ? 'success' : initiative.status === 'on_hold' ? 'warning' : 'primary'}
                        />
                      </TableCell>
                      <TableCell align="right">{Number(initiative.current_percent_complete).toFixed(0)}%</TableCell>
                      <TableCell>
                        {latest ? (
                          <Box>
                            <Typography variant="body2">{latest.period_end}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {latest.summary || 'No summary'}
                            </Typography>
                          </Box>
                        ) : (
                          <Typography variant="body2" color="text.secondary">No updates</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {initiative.is_update_stale ? (
                          <Chip
                            size="small"
                            color="warning"
                            variant="outlined"
                            label={latest ? `Stale (${daysSince(latest.period_end)}d)` : 'No recent update'}
                          />
                        ) : (
                          <Chip size="small" color="success" variant="outlined" label="Current" />
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Button size="small" variant="outlined" onClick={() => openQuickUpdate(initiative)}>
                          Add Weekly Update
                        </Button>
                      </TableCell>
                    </TableRow>
                    {isQuickOpen && (
                      <TableRow>
                        <TableCell colSpan={7}>
                          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ alignItems: { md: 'center' } }}>
                            <TextField
                              label="Period End"
                              type="date"
                              size="small"
                              value={quickUpdatePeriodEnd}
                              onChange={(event) => setQuickUpdatePeriodEnd(event.target.value)}
                              slotProps={{ inputLabel: { shrink: true } }}
                            />
                            <TextField
                              label="% Complete"
                              type="number"
                              size="small"
                              value={quickUpdatePercent}
                              onChange={(event) => setQuickUpdatePercent(event.target.value)}
                              inputProps={{ min: 0, max: 100, step: 1 }}
                              sx={{ width: 140 }}
                            />
                            <TextField
                              label="Summary"
                              size="small"
                              value={quickUpdateSummary}
                              onChange={(event) => setQuickUpdateSummary(event.target.value)}
                              sx={{ flex: 1, minWidth: 260 }}
                            />
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <Button
                                size="small"
                                variant="contained"
                                onClick={saveQuickUpdate}
                                disabled={savingQuickUpdate}
                              >
                                {savingQuickUpdate ? 'Saving...' : 'Save'}
                              </Button>
                              <Button size="small" onClick={() => setQuickUpdateInitiativeId(null)}>
                                Cancel
                              </Button>
                            </Box>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                );
              })}
              {filteredInitiatives.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} align="center">No initiatives found</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={createOpen} onClose={() => !creating && setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Initiative</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Name"
              value={formData.name}
              onChange={(event) => setFormData((current) => ({ ...current, name: event.target.value }))}
              required
              fullWidth
            />
            <TextField
              select
              label="Owner"
              value={formData.owner}
              onChange={(event) => setFormData((current) => ({ ...current, owner: event.target.value }))}
              fullWidth
            >
              <MenuItem value="">Unassigned</MenuItem>
              {staff.map((member) => (
                <MenuItem key={member.id} value={String(member.id)}>
                  {member.first_name} {member.last_name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Status"
              value={formData.status}
              onChange={(event) =>
                setFormData((current) => ({ ...current, status: event.target.value as Initiative['status'] }))
              }
              fullWidth
            >
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="on_hold">On Hold</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
            </TextField>
            <TextField
              label="Target Date"
              type="date"
              value={formData.target_date}
              onChange={(event) => setFormData((current) => ({ ...current, target_date: event.target.value }))}
              slotProps={{ inputLabel: { shrink: true } }}
              fullWidth
            />
            <TextField
              label="Notes"
              multiline
              minRows={3}
              value={formData.notes}
              onChange={(event) => setFormData((current) => ({ ...current, notes: event.target.value }))}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)} disabled={creating}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained" disabled={creating || !formData.name.trim()}>
            {creating ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
