import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
  Chip,
  Button,
  Stack,
  Menu,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import { ArrowBack, Add, Edit, Delete, Save, Close, ExpandMore } from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { deliverablesApi, timeEntriesApi, statusUpdatesApi, tasksApi, assignmentsApi, staffApi } from '../api/client';
import type { Deliverable, TimeEntry, DeliverableStatusUpdate, Staff } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { TargetDateBadge } from '../components/TargetDateBadge';
import { DeliverableBurnDownChart } from '../components/DeliverableBurnDownChart';
import { AxiosError } from 'axios';
import { formatDeliverableStatusLabel, getDeliverableStatusChipColor } from '../utils/statusUpdates';
import {
  formatDeliverableLifecycleStatusLabel,
  getDeliverableLifecycleStatusChipColor,
} from '../utils/deliverableStatus';
import { formatTaskStatusLabel, getTaskStatusChipColor } from '../utils/taskStatus';

const DELIVERABLE_DETAIL_TAB_STORAGE_KEY = 'deliverable_detail_active_tab';

export function DeliverableDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [statusUpdates, setStatusUpdates] = useState<DeliverableStatusUpdate[]>([]);
  const [newStatusUpdate, setNewStatusUpdate] = useState({
    period_end: new Date().toISOString().split('T')[0],
    status: 'on_track' as DeliverableStatusUpdate['status'],
    summary: '',
  });
  const [savingStatusUpdate, setSavingStatusUpdate] = useState(false);
  const [statusUpdateCreateError, setStatusUpdateCreateError] = useState('');
  const [statusUpdateActionError, setStatusUpdateActionError] = useState('');
  const [editingStatusUpdateId, setEditingStatusUpdateId] = useState<number | null>(null);
  const [editingStatusUpdate, setEditingStatusUpdate] = useState<{
    period_end: string;
    status: DeliverableStatusUpdate['status'];
    summary: string;
  } | null>(null);
  const [savingEditedStatusUpdateId, setSavingEditedStatusUpdateId] = useState<number | null>(null);
  const [deletingStatusUpdateId, setDeletingStatusUpdateId] = useState<number | null>(null);
  const [taskQuickUpdateError, setTaskQuickUpdateError] = useState('');
  const [updatingTaskId, setUpdatingTaskId] = useState<number | null>(null);
  const [taskContextMenu, setTaskContextMenu] = useState<{
    mouseX: number;
    mouseY: number;
    taskId: number;
    currentPercentComplete: number;
  } | null>(null);
  const [activeTab, setActiveTab] = useState(() => {
    const storedTab = localStorage.getItem(DELIVERABLE_DETAIL_TAB_STORAGE_KEY);
    const parsedTab = storedTab ? Number.parseInt(storedTab, 10) : 0;
    return Number.isInteger(parsedTab) && parsedTab >= 0 && parsedTab <= 3 ? parsedTab : 0;
  });
  const [timeEntriesExpanded, setTimeEntriesExpanded] = useState(false);
  const [newTimeEntry, setNewTimeEntry] = useState({
    entry_date: new Date().toISOString().split('T')[0],
    hours: '',
    note: '',
  });
  const [savingTimeEntry, setSavingTimeEntry] = useState(false);
  const [timeEntryCreateError, setTimeEntryCreateError] = useState('');
  const [staffMembers, setStaffMembers] = useState<Staff[]>([]);
  const [newAssignment, setNewAssignment] = useState({
    staff: '',
    budget_hours: '',
    is_lead: false,
  });
  const [savingAssignment, setSavingAssignment] = useState(false);
  const [assignmentCreateError, setAssignmentCreateError] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const getApiErrorMessage = (err: unknown, fallbackMessage: string) => {
    if (!(err instanceof AxiosError)) {
      return fallbackMessage;
    }

    const responseData = err.response?.data;
    if (typeof responseData === 'string') {
      return responseData;
    }

    if (responseData?.detail && typeof responseData.detail === 'string') {
      return responseData.detail;
    }

    if (responseData && typeof responseData === 'object') {
      for (const value of Object.values(responseData as Record<string, unknown>)) {
        if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'string') {
          return value[0];
        }
        if (typeof value === 'string') {
          return value;
        }
      }
    }

    return fallbackMessage;
  };

  const loadData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const [deliverableData, timeEntriesData, statusUpdatesData] = await Promise.all([
        deliverablesApi.get(parseInt(id)),
        timeEntriesApi.list({ deliverable_id: parseInt(id) }),
        statusUpdatesApi.list({ deliverable_id: parseInt(id), order_by: 'period_end', order_dir: 'desc' }),
      ]);
      setDeliverable(deliverableData);
      setTimeEntries(timeEntriesData);
      setStatusUpdates(statusUpdatesData);
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to load deliverable');
      } else {
        setError('Failed to load deliverable');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const loadStaffMembers = async () => {
      try {
        const data = await staffApi.list({ order_by: 'id', order_dir: 'desc' });
        setStaffMembers(data);
      } catch {
        setStaffMembers([]);
      }
    };

    void loadStaffMembers();
  }, []);

  useEffect(() => {
    localStorage.setItem(DELIVERABLE_DETAIL_TAB_STORAGE_KEY, activeTab.toString());
  }, [activeTab]);

  const handleCreateStatusUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deliverable) return;

    setSavingStatusUpdate(true);
    setStatusUpdateCreateError('');

    try {
      await statusUpdatesApi.create({
        deliverable: deliverable.id,
        period_end: newStatusUpdate.period_end,
        status: newStatusUpdate.status,
        summary: newStatusUpdate.summary,
      });

      setNewStatusUpdate({
        period_end: new Date().toISOString().split('T')[0],
        status: 'on_track',
        summary: '',
      });

      await loadData();
    } catch (err) {
      setStatusUpdateCreateError(getApiErrorMessage(err, 'Failed to save status update'));
    } finally {
      setSavingStatusUpdate(false);
    }
  };

  const startEditStatusUpdate = (update: DeliverableStatusUpdate) => {
    setEditingStatusUpdateId(update.id);
    setEditingStatusUpdate({
      period_end: update.period_end,
      status: update.status,
      summary: update.summary,
    });
    setStatusUpdateActionError('');
  };

  const cancelEditStatusUpdate = () => {
    setEditingStatusUpdateId(null);
    setEditingStatusUpdate(null);
    setStatusUpdateActionError('');
  };

  const handleSaveEditedStatusUpdate = async (statusUpdateId: number) => {
    if (!editingStatusUpdate || !deliverable) return;

    setSavingEditedStatusUpdateId(statusUpdateId);
    setStatusUpdateActionError('');

    try {
      await statusUpdatesApi.update(statusUpdateId, {
        deliverable: deliverable.id,
        period_end: editingStatusUpdate.period_end,
        status: editingStatusUpdate.status,
        summary: editingStatusUpdate.summary,
      });
      cancelEditStatusUpdate();
      await loadData();
    } catch (err) {
      setStatusUpdateActionError(getApiErrorMessage(err, 'Failed to update status update'));
    } finally {
      setSavingEditedStatusUpdateId(null);
    }
  };

  const handleDeleteStatusUpdate = async (statusUpdateId: number) => {
    const confirmed = window.confirm('Delete this status update?');
    if (!confirmed) return;

    setDeletingStatusUpdateId(statusUpdateId);
    setStatusUpdateActionError('');

    try {
      await statusUpdatesApi.delete(statusUpdateId);
      if (editingStatusUpdateId === statusUpdateId) {
        cancelEditStatusUpdate();
      }
      await loadData();
    } catch (err) {
      setStatusUpdateActionError(getApiErrorMessage(err, 'Failed to delete status update'));
    } finally {
      setDeletingStatusUpdateId(null);
    }
  };

  const handleTaskContextMenu = (event: React.MouseEvent, taskId: number, currentPercentComplete: number) => {
    event.preventDefault();
    setTaskQuickUpdateError('');
    setTaskContextMenu({
      mouseX: event.clientX + 2,
      mouseY: event.clientY - 6,
      taskId,
      currentPercentComplete,
    });
  };

  const handleCloseTaskContextMenu = () => {
    setTaskContextMenu(null);
  };

  const handleQuickSetTaskPercent = async (percentComplete: number) => {
    if (!taskContextMenu) return;

    setUpdatingTaskId(taskContextMenu.taskId);
    setTaskQuickUpdateError('');

    try {
      await tasksApi.update(taskContextMenu.taskId, { percent_complete: percentComplete.toString() });
      await loadData();
      handleCloseTaskContextMenu();
    } catch (err) {
      setTaskQuickUpdateError(getApiErrorMessage(err, 'Failed to update task % complete'));
    } finally {
      setUpdatingTaskId(null);
    }
  };

  const handleCreateTimeEntry = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!deliverable) return;

    setSavingTimeEntry(true);
    setTimeEntryCreateError('');

    try {
      await timeEntriesApi.create({
        deliverable: deliverable.id,
        entry_date: newTimeEntry.entry_date,
        hours: newTimeEntry.hours,
        note: newTimeEntry.note,
      });

      setNewTimeEntry({
        entry_date: new Date().toISOString().split('T')[0],
        hours: '',
        note: '',
      });

      await loadData();
    } catch (err) {
      setTimeEntryCreateError(getApiErrorMessage(err, 'Failed to save time entry'));
    } finally {
      setSavingTimeEntry(false);
    }
  };

  const handleCreateAssignment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!deliverable || !newAssignment.staff) return;

    setSavingAssignment(true);
    setAssignmentCreateError('');

    try {
      await assignmentsApi.create({
        deliverable: deliverable.id,
        staff: Number.parseInt(newAssignment.staff, 10),
        budget_hours: newAssignment.budget_hours,
        is_lead: newAssignment.is_lead,
      });

      setNewAssignment({
        staff: '',
        budget_hours: '',
        is_lead: false,
      });

      await loadData();
    } catch (err) {
      setAssignmentCreateError(getApiErrorMessage(err, 'Failed to save assignment'));
    } finally {
      setSavingAssignment(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !deliverable) {
    return <Alert severity="error">{error || 'Deliverable not found'}</Alert>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate(-1)}>
          Back
        </Button>
        <Button
          variant="outlined"
          startIcon={<Edit />}
          onClick={() => navigate(`/deliverables/${deliverable.id}/edit`)}
        >
          Edit Deliverable
        </Button>
      </Box>

      <Typography variant="h4" gutterBottom>
        {deliverable.name}
      </Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, value) => setActiveTab(value)}>
          <Tab label="Basic Info" />
          <Tab label="Burn & Time" />
          <Tab label="Staff Assignments" />
          <Tab label="Tasks" />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Budget Hours
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.budget_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Assigned Budget Hours
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.assigned_budget_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Spent Hours
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.spent_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Variance
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.variance_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Status
            </Typography>
            <Box sx={{ mt: 1 }}>
              <Chip
                label={formatDeliverableLifecycleStatusLabel(deliverable.status)}
                color={getDeliverableLifecycleStatusChipColor(deliverable.status)}
              />
            </Box>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              % Complete
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.estimated_percent_complete).toFixed(1)}%</Typography>
          </CardContent>
        </Card>
      </Stack>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Details
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Target Completion Date
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography>{deliverable.target_completion_date || 'Not set'}</Typography>
                    <TargetDateBadge targetDate={deliverable.target_completion_date} />
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Charge Code
                  </Typography>
                  <Typography>{deliverable.charge_code || 'N/A'}</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Per-Week Metrics
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Assigned Budget Hours/Week
                </Typography>
                <Typography>{parseFloat(deliverable.assigned_budget_hours_per_week).toFixed(1)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Spent Hours/Week
                </Typography>
                <Typography>{parseFloat(deliverable.spent_hours_per_week).toFixed(1)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Estimated Burn Rate
                </Typography>
                <Typography>{parseFloat(deliverable.estimated_burn_rate).toFixed(1)} h/week</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Actual Burn Rate (last 4 weeks)
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography>{parseFloat(deliverable.actual_burn_rate).toFixed(1)} h/week</Typography>
                  {(() => {
                    const estimated = parseFloat(deliverable.estimated_burn_rate);
                    const actual = parseFloat(deliverable.actual_burn_rate);
                    const variance = actual - estimated;
                    const percentDiff = estimated > 0 ? (variance / estimated) * 100 : 0;

                    if (Math.abs(percentDiff) < 5) {
                      return <Chip label="On Pace" size="small" color="success" />;
                    } else if (variance > 0) {
                      return <Chip label={`+${variance.toFixed(1)} h/week`} size="small" color="warning" />;
                    } else if (variance < 0) {
                      return <Chip label={`${variance.toFixed(1)} h/week`} size="small" color="info" />;
                    }
                    return null;
                  })()}
                </Box>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Health Flags
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
                  {deliverable.is_over_budget && <StatusBadge type="over_budget" />}
                  {deliverable.is_missing_lead && <StatusBadge type="missing_lead" />}
                  {deliverable.is_missing_budget && <StatusBadge type="missing_budget" />}
                  {!deliverable.is_over_budget && !deliverable.is_missing_lead && !deliverable.is_missing_budget && (
                    <StatusBadge type="on_track" />
                  )}
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Latest Status Update
            </Typography>
            {deliverable.latest_status_update ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Period End
                  </Typography>
                  <Typography>{deliverable.latest_status_update.period_end}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Status
                  </Typography>
                  <Box sx={{ mt: 0.5 }}>
                    <Chip
                      label={formatDeliverableStatusLabel(deliverable.latest_status_update.status)}
                      size="small"
                      color={getDeliverableStatusChipColor(deliverable.latest_status_update.status)}
                    />
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Summary
                  </Typography>
                  <Typography>
                    {deliverable.latest_status_update.summary || 'No summary provided'}
                  </Typography>
                </Box>
              </Box>
            ) : (
              <Typography color="text.secondary">No status updates yet</Typography>
            )}
          </CardContent>
        </Card>
      </Stack>

      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Status Updates
      </Typography>

      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Add Status Update
        </Typography>

        {statusUpdateCreateError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {statusUpdateCreateError}
          </Alert>
        )}

        <Box component="form" onSubmit={handleCreateStatusUpdate}>
          <Stack spacing={2}>
            <TextField
              label="Period End"
              type="date"
              value={newStatusUpdate.period_end}
              onChange={(e) =>
                setNewStatusUpdate({
                  ...newStatusUpdate,
                  period_end: e.target.value,
                })
              }
              required
              fullWidth
              slotProps={{
                inputLabel: { shrink: true },
              }}
            />

            <TextField
              label="Status"
              select
              value={newStatusUpdate.status}
              onChange={(e) =>
                setNewStatusUpdate({
                  ...newStatusUpdate,
                  status: e.target.value as DeliverableStatusUpdate['status'],
                })
              }
              required
              fullWidth
            >
              <MenuItem value="on_track">On Track</MenuItem>
              <MenuItem value="at_risk">At Risk</MenuItem>
              <MenuItem value="off_track">Off Track</MenuItem>
            </TextField>

            <TextField
              label="Summary"
              value={newStatusUpdate.summary}
              onChange={(e) =>
                setNewStatusUpdate({
                  ...newStatusUpdate,
                  summary: e.target.value,
                })
              }
              fullWidth
              multiline
              minRows={3}
            />

            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button type="submit" variant="contained" startIcon={<Add />} disabled={savingStatusUpdate}>
                {savingStatusUpdate ? 'Saving...' : 'Add Update'}
              </Button>
            </Box>
          </Stack>
        </Box>
      </Paper>

      {statusUpdateActionError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {statusUpdateActionError}
        </Alert>
      )}

      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Period End</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Summary</TableCell>
              <TableCell>Created At</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {statusUpdates.map((update) => (
              <TableRow key={update.id}>
                <TableCell>
                  {editingStatusUpdateId === update.id && editingStatusUpdate ? (
                    <TextField
                      type="date"
                      size="small"
                      value={editingStatusUpdate.period_end}
                      onChange={(e) =>
                        setEditingStatusUpdate({
                          ...editingStatusUpdate,
                          period_end: e.target.value,
                        })
                      }
                      slotProps={{ inputLabel: { shrink: true } }}
                    />
                  ) : (
                    update.period_end
                  )}
                </TableCell>
                <TableCell>
                  {editingStatusUpdateId === update.id && editingStatusUpdate ? (
                    <TextField
                      select
                      size="small"
                      value={editingStatusUpdate.status}
                      onChange={(e) =>
                        setEditingStatusUpdate({
                          ...editingStatusUpdate,
                          status: e.target.value as DeliverableStatusUpdate['status'],
                        })
                      }
                      sx={{ minWidth: 140 }}
                    >
                      <MenuItem value="on_track">On Track</MenuItem>
                      <MenuItem value="at_risk">At Risk</MenuItem>
                      <MenuItem value="off_track">Off Track</MenuItem>
                    </TextField>
                  ) : (
                    <Chip
                      label={formatDeliverableStatusLabel(update.status)}
                      size="small"
                      color={getDeliverableStatusChipColor(update.status)}
                    />
                  )}
                </TableCell>
                <TableCell>
                  {editingStatusUpdateId === update.id && editingStatusUpdate ? (
                    <TextField
                      size="small"
                      fullWidth
                      value={editingStatusUpdate.summary}
                      onChange={(e) =>
                        setEditingStatusUpdate({
                          ...editingStatusUpdate,
                          summary: e.target.value,
                        })
                      }
                    />
                  ) : (
                    update.summary
                  )}
                </TableCell>
                <TableCell>{new Date(update.created_at).toLocaleString()}</TableCell>
                <TableCell align="right">
                  {editingStatusUpdateId === update.id ? (
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button
                        size="small"
                        startIcon={<Save />}
                        onClick={() => handleSaveEditedStatusUpdate(update.id)}
                        disabled={savingEditedStatusUpdateId === update.id}
                      >
                        {savingEditedStatusUpdateId === update.id ? 'Saving...' : 'Save'}
                      </Button>
                      <Button size="small" startIcon={<Close />} onClick={cancelEditStatusUpdate}>
                        Cancel
                      </Button>
                    </Stack>
                  ) : (
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button size="small" startIcon={<Edit />} onClick={() => startEditStatusUpdate(update)}>
                        Edit
                      </Button>
                      <Button
                        size="small"
                        color="error"
                        startIcon={<Delete />}
                        onClick={() => handleDeleteStatusUpdate(update.id)}
                        disabled={deletingStatusUpdateId === update.id}
                      >
                        {deletingStatusUpdateId === update.id ? 'Deleting...' : 'Delete'}
                      </Button>
                    </Stack>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {statusUpdates.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No status updates found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
        </>
      )}

      {activeTab === 1 && (
        <>
          <Box sx={{ mt: 2, mb: 3 }}>
            <DeliverableBurnDownChart deliverable={deliverable} />
          </Box>

          <Paper sx={{ p: 3, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              Add Time Entry
            </Typography>

            {timeEntryCreateError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {timeEntryCreateError}
              </Alert>
            )}

            <Box component="form" onSubmit={handleCreateTimeEntry}>
              <Stack spacing={2}>
                <TextField
                  label="Date"
                  type="date"
                  value={newTimeEntry.entry_date}
                  onChange={(e) =>
                    setNewTimeEntry({
                      ...newTimeEntry,
                      entry_date: e.target.value,
                    })
                  }
                  required
                  fullWidth
                  slotProps={{
                    inputLabel: { shrink: true },
                  }}
                />

                <TextField
                  label="Hours"
                  type="number"
                  value={newTimeEntry.hours}
                  onChange={(e) =>
                    setNewTimeEntry({
                      ...newTimeEntry,
                      hours: e.target.value,
                    })
                  }
                  required
                  fullWidth
                  inputProps={{ min: 0, step: 0.25 }}
                />

                <TextField
                  label="Note"
                  value={newTimeEntry.note}
                  onChange={(e) =>
                    setNewTimeEntry({
                      ...newTimeEntry,
                      note: e.target.value,
                    })
                  }
                  fullWidth
                  multiline
                  minRows={2}
                />

                <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <Button type="submit" variant="contained" startIcon={<Add />} disabled={savingTimeEntry}>
                    {savingTimeEntry ? 'Saving...' : 'Add Time Entry'}
                  </Button>
                </Box>
              </Stack>
            </Box>
          </Paper>

          <Accordion expanded={timeEntriesExpanded} onChange={(_, expanded) => setTimeEntriesExpanded(expanded)}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography variant="h6">Time Entries</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell align="right">Hours</TableCell>
                      <TableCell>Note</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {timeEntries.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell>{entry.entry_date}</TableCell>
                        <TableCell align="right">{parseFloat(entry.hours).toFixed(1)}</TableCell>
                        <TableCell>{entry.note || entry.notes || 'N/A'}</TableCell>
                      </TableRow>
                    ))}
                    {timeEntries.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={3} align="center">
                          No time entries found
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </AccordionDetails>
          </Accordion>
        </>
      )}

      {activeTab === 2 && (
        <>
          <Typography variant="h5" gutterBottom sx={{ mt: 2 }}>
            Staff Assignments
          </Typography>

          <Paper sx={{ p: 3, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              Add Staff Assignment
            </Typography>

            {assignmentCreateError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {assignmentCreateError}
              </Alert>
            )}

            <Box component="form" onSubmit={handleCreateAssignment}>
              <Stack spacing={2}>
                <TextField
                  label="Staff Member"
                  select
                  value={newAssignment.staff}
                  onChange={(e) =>
                    setNewAssignment({
                      ...newAssignment,
                      staff: e.target.value,
                    })
                  }
                  required
                  fullWidth
                >
                  {staffMembers.map((staffMember) => (
                    <MenuItem key={staffMember.id} value={staffMember.id.toString()}>
                      {staffMember.first_name} {staffMember.last_name}
                    </MenuItem>
                  ))}
                </TextField>

                <TextField
                  label="Budget Hours"
                  type="number"
                  value={newAssignment.budget_hours}
                  onChange={(e) =>
                    setNewAssignment({
                      ...newAssignment,
                      budget_hours: e.target.value,
                    })
                  }
                  required
                  fullWidth
                  inputProps={{ min: 0, step: 0.5 }}
                />

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={newAssignment.is_lead}
                      onChange={(e) =>
                        setNewAssignment({
                          ...newAssignment,
                          is_lead: e.target.checked,
                        })
                      }
                    />
                  }
                  label="Lead Assignment"
                />

                <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <Button type="submit" variant="contained" startIcon={<Add />} disabled={savingAssignment}>
                    {savingAssignment ? 'Saving...' : 'Add Assignment'}
                  </Button>
                </Box>
              </Stack>
            </Box>
          </Paper>

          <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Staff Member</TableCell>
              <TableCell align="right">Budget Hours</TableCell>
              <TableCell>Lead</TableCell>
              <TableCell>Assigned At</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {deliverable.assignments && deliverable.assignments.length > 0 ? (
              deliverable.assignments.map((assignment) => (
                <TableRow key={assignment.id}>
                  <TableCell>{assignment.staff_name}</TableCell>
                  <TableCell align="right">{parseFloat(assignment.budget_hours).toFixed(1)}</TableCell>
                  <TableCell>
                    {assignment.is_lead ? (
                      <Chip label="Lead" color="primary" size="small" />
                    ) : (
                      <Chip label="Member" size="small" />
                    )}
                  </TableCell>
                  <TableCell>{new Date(assignment.created_at).toLocaleDateString()}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  <Typography color="text.secondary">No staff assigned</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
        </>
      )}

      {activeTab === 3 && (
        <>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2, mb: 2 }}>
        <Typography variant="h5">Tasks</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => navigate(`/tasks/new?deliverable=${deliverable.id}`)}
        >
          Create Task
        </Button>
      </Box>

      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Assignee</TableCell>
              <TableCell align="right">Budget Hours</TableCell>
              <TableCell align="right">% Complete</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Updated At</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {deliverable.tasks && deliverable.tasks.length > 0 ? (
              deliverable.tasks.map((task) => (
                <TableRow
                  key={task.id}
                  hover
                  onContextMenu={(event) => handleTaskContextMenu(event, task.id, parseFloat(task.percent_complete))}
                >
                  <TableCell>{task.title}</TableCell>
                  <TableCell>{task.assignee_name || 'Unassigned'}</TableCell>
                  <TableCell align="right">{parseFloat(task.budget_hours).toFixed(1)}</TableCell>
                  <TableCell align="right">{parseFloat(task.percent_complete).toFixed(0)}%</TableCell>
                  <TableCell>
                    <Chip
                      label={formatTaskStatusLabel(task.status)}
                      size="small"
                      color={getTaskStatusChipColor(task.status)}
                    />
                  </TableCell>
                  <TableCell>{new Date(task.updated_at).toLocaleDateString()}</TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      startIcon={<Edit />}
                      onClick={() => navigate(`/tasks/${task.id}`)}
                    >
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="text.secondary">No tasks</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {taskQuickUpdateError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {taskQuickUpdateError}
        </Alert>
      )}

      <Menu
        open={taskContextMenu !== null}
        onClose={handleCloseTaskContextMenu}
        anchorReference="anchorPosition"
        anchorPosition={
          taskContextMenu !== null
            ? { top: taskContextMenu.mouseY, left: taskContextMenu.mouseX }
            : undefined
        }
      >
        {[0, 25, 50, 75, 100].map((value) => (
          <MenuItem
            key={value}
            selected={taskContextMenu?.currentPercentComplete === value}
            disabled={updatingTaskId === taskContextMenu?.taskId}
            onClick={() => void handleQuickSetTaskPercent(value)}
          >
            Set to {value}%
          </MenuItem>
        ))}
      </Menu>
        </>
      )}
    </Box>
  );
}

