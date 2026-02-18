import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
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
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { Add, Edit } from '@mui/icons-material';
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
  const [tagFilter, setTagFilter] = useState('all');
  const [showStaleOnly, setShowStaleOnly] = useState(false);
  const [showInactive, setShowInactive] = useState(false);

  const [formOpen, setFormOpen] = useState(false);
  const [savingForm, setSavingForm] = useState(false);
  const [editingInitiativeId, setEditingInitiativeId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    owner: '',
    status: 'active' as Initiative['status'],
    tags: '',
    target_date: '',
    notes: '',
  });

  const [quickUpdateInitiativeId, setQuickUpdateInitiativeId] = useState<number | null>(null);
  const [quickUpdatePeriodEnd, setQuickUpdatePeriodEnd] = useState(new Date().toISOString().split('T')[0]);
  const [quickUpdatePercent, setQuickUpdatePercent] = useState('0');
  const [quickUpdateSummary, setQuickUpdateSummary] = useState('');
  const [savingQuickUpdate, setSavingQuickUpdate] = useState(false);
  const [savingStatusInitiativeId, setSavingStatusInitiativeId] = useState<number | null>(null);

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
      if (!showInactive && initiative.status !== 'active') {
        return false;
      }
      if (tagFilter !== 'all') {
        const tags = (initiative.tags || []).map((tag) => tag.toLowerCase());
        if (!tags.includes(tagFilter.toLowerCase())) {
          return false;
        }
      }
      if (showStaleOnly && !initiative.is_update_stale) {
        return false;
      }
      return true;
    });
  }, [initiatives, search, statusFilter, showInactive, tagFilter, showStaleOnly]);

  const availableTags = useMemo(() => {
    const allTags = initiatives.flatMap((initiative) => initiative.tags || []);
    return Array.from(new Set(allTags)).sort((left, right) => left.localeCompare(right));
  }, [initiatives]);

  const openCreateDialog = () => {
    setEditingInitiativeId(null);
    setFormData({
      name: '',
      owner: '',
      status: 'active',
      tags: '',
      target_date: '',
      notes: '',
    });
    setFormOpen(true);
  };

  const openEditDialog = (initiative: Initiative) => {
    setEditingInitiativeId(initiative.id);
    setFormData({
      name: initiative.name,
      owner: initiative.owner ? String(initiative.owner) : '',
      status: initiative.status,
      tags: (initiative.tags || []).join(', '),
      target_date: initiative.target_date || '',
      notes: initiative.notes || '',
    });
    setFormOpen(true);
  };

  const handleSaveInitiative = async () => {
    setSavingForm(true);
    setError('');
    try {
      const tags = formData.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0);

      const payload = {
        name: formData.name,
        owner: formData.owner ? Number(formData.owner) : null,
        status: formData.status,
        tags,
        target_date: formData.target_date || null,
        notes: formData.notes,
      };

      if (editingInitiativeId) {
        await initiativesApi.update(editingInitiativeId, payload);
      } else {
        await initiativesApi.create(payload);
      }

      setFormOpen(false);
      setEditingInitiativeId(null);
      setFormData({ name: '', owner: '', status: 'active', tags: '', target_date: '', notes: '' });
      await loadData();
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to save initiative');
      } else {
        setError('Failed to save initiative');
      }
    } finally {
      setSavingForm(false);
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

  const updateInitiativeStatus = async (initiativeId: number, status: Initiative['status']) => {
    setSavingStatusInitiativeId(initiativeId);
    setError('');
    try {
      await initiativesApi.update(initiativeId, { status });
      setInitiatives((current) =>
        current.map((initiative) =>
          initiative.id === initiativeId
            ? {
                ...initiative,
                status,
              }
            : initiative
        )
      );
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to update initiative status');
      } else {
        setError('Failed to update initiative status');
      }
    } finally {
      setSavingStatusInitiativeId(null);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Initiatives</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={openCreateDialog}>
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
          label="Tag"
          size="small"
          value={tagFilter}
          onChange={(event) => setTagFilter(event.target.value)}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="all">All Tags</MenuItem>
          {availableTags.map((tag) => (
            <MenuItem key={tag} value={tag}>
              {tag}
            </MenuItem>
          ))}
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
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
            />
          }
          label="Show inactive"
          sx={{ ml: 'auto' }}
        />
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
                  <Fragment key={initiative.id}>
                    <TableRow>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{initiative.name}</Typography>
                        {!!initiative.tags?.length && (
                          <Box sx={{ mt: 0.5, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                            {initiative.tags.map((tag) => (
                              <Chip key={`${initiative.id}-${tag}`} size="small" variant="outlined" label={tag} />
                            ))}
                          </Box>
                        )}
                        {initiative.target_date && (
                          <Typography variant="caption" color="text.secondary">
                            Target: {initiative.target_date}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>{initiative.owner_name || 'Unassigned'}</TableCell>
                      <TableCell>
                        <TextField
                          select
                          size="small"
                          value={initiative.status}
                          onChange={(event) =>
                            void updateInitiativeStatus(initiative.id, event.target.value as Initiative['status'])
                          }
                          disabled={savingStatusInitiativeId === initiative.id}
                          sx={{ minWidth: 130 }}
                        >
                          <MenuItem value="active">Active</MenuItem>
                          <MenuItem value="on_hold">On Hold</MenuItem>
                          <MenuItem value="completed">Completed</MenuItem>
                        </TextField>
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
                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                          <Button size="small" variant="outlined" startIcon={<Edit />} onClick={() => openEditDialog(initiative)}>
                            Edit
                          </Button>
                          <Button size="small" variant="outlined" onClick={() => openQuickUpdate(initiative)}>
                            Add Weekly Update
                          </Button>
                        </Box>
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
                  </Fragment>
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

      <Dialog open={formOpen} onClose={() => !savingForm && setFormOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingInitiativeId ? 'Edit Initiative' : 'Add Initiative'}</DialogTitle>
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
              label="Tags"
              value={formData.tags}
              onChange={(event) => setFormData((current) => ({ ...current, tags: event.target.value }))}
              helperText="Comma-separated (example: internal, ops)"
              fullWidth
            />
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
          <Button onClick={() => setFormOpen(false)} disabled={savingForm}>Cancel</Button>
          <Button onClick={handleSaveInitiative} variant="contained" disabled={savingForm || !formData.name.trim()}>
            {savingForm ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
