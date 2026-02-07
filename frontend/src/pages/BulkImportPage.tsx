import { Alert, Box, Button, Card, CardContent, LinearProgress, Paper, Stack, Typography } from '@mui/material';
import { UploadFile } from '@mui/icons-material';
import { useState } from 'react';
import { apiClient } from '../api/client';

interface ImportStats {
  staff_created?: number;
  contracts_created?: number;
  deliverables_created?: number;
  tasks_created?: number;
  time_entries_created?: number;
}

interface ImportResult {
  success: boolean;
  message?: string;
  error?: string;
  stats?: ImportStats;
}

export function BulkImportPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importType, setImportType] = useState<'data' | 'time-entries'>('data');

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setResult(null);

    try {
      const fileContent = await selectedFile.text();
      const jsonData = JSON.parse(fileContent);

      const endpoint = importType === 'time-entries'
        ? '/bulk-import/time-entries/'
        : '/bulk-import/';

      const response = await apiClient.post(endpoint, jsonData);
      setResult(response.data);
    } catch (error: any) {
      setResult({
        success: false,
        error: error.response?.data?.error || error.message || 'Upload failed',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Bulk Import Data
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        Upload JSON files to import staff, contracts, deliverables, tasks, and time entries.
      </Typography>

      <Stack spacing={3}>
        {/* Import Type Selection */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Select Import Type
            </Typography>
            <Stack direction="row" spacing={2}>
              <Button
                variant={importType === 'data' ? 'contained' : 'outlined'}
                onClick={() => {
                  setImportType('data');
                  setSelectedFile(null);
                  setResult(null);
                }}
              >
                Staff, Contracts, Deliverables, Tasks
              </Button>
              <Button
                variant={importType === 'time-entries' ? 'contained' : 'outlined'}
                onClick={() => {
                  setImportType('time-entries');
                  setSelectedFile(null);
                  setResult(null);
                }}
              >
                Time Entries
              </Button>
            </Stack>
          </CardContent>
        </Card>

        {/* File Upload */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Upload JSON File
            </Typography>
            <Stack spacing={2}>
              <input
                accept=".json"
                style={{ display: 'none' }}
                id="file-upload"
                type="file"
                onChange={handleFileSelect}
              />
              <label htmlFor="file-upload">
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={<UploadFile />}
                  fullWidth
                >
                  Choose File
                </Button>
              </label>

              {selectedFile && (
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="body2">
                    <strong>Selected file:</strong> {selectedFile.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Size: {(selectedFile.size / 1024).toFixed(2)} KB
                  </Typography>
                </Paper>
              )}

              <Button
                variant="contained"
                onClick={handleUpload}
                disabled={!selectedFile || loading}
                fullWidth
              >
                {loading ? 'Uploading...' : 'Upload and Import'}
              </Button>
            </Stack>
          </CardContent>
        </Card>

        {/* Loading Indicator */}
        {loading && (
          <Card>
            <CardContent>
              <Typography variant="body2" gutterBottom>
                Importing data...
              </Typography>
              <LinearProgress />
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {result && (
          <Card>
            <CardContent>
              {result.success ? (
                <>
                  <Alert severity="success" sx={{ mb: 2 }}>
                    {result.message || 'Import completed successfully!'}
                  </Alert>
                  {result.stats && (
                    <Box>
                      <Typography variant="h6" gutterBottom>
                        Import Statistics
                      </Typography>
                      <Stack spacing={1}>
                        {result.stats.staff_created !== undefined && (
                          <Typography variant="body2">
                            Staff created: <strong>{result.stats.staff_created}</strong>
                          </Typography>
                        )}
                        {result.stats.contracts_created !== undefined && (
                          <Typography variant="body2">
                            Contracts created: <strong>{result.stats.contracts_created}</strong>
                          </Typography>
                        )}
                        {result.stats.deliverables_created !== undefined && (
                          <Typography variant="body2">
                            Deliverables created: <strong>{result.stats.deliverables_created}</strong>
                          </Typography>
                        )}
                        {result.stats.tasks_created !== undefined && (
                          <Typography variant="body2">
                            Tasks created: <strong>{result.stats.tasks_created}</strong>
                          </Typography>
                        )}
                        {result.stats.time_entries_created !== undefined && (
                          <Typography variant="body2">
                            Time entries created: <strong>{result.stats.time_entries_created}</strong>
                          </Typography>
                        )}
                      </Stack>
                    </Box>
                  )}
                </>
              ) : (
                <Alert severity="error">
                  <Typography variant="body2">
                    <strong>Error:</strong> {result.error || 'Import failed'}
                  </Typography>
                </Alert>
              )}
            </CardContent>
          </Card>
        )}

        {/* Instructions */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              JSON Format Instructions
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>For Staff, Contracts, Deliverables, and Tasks:</strong>
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50', mb: 2 }}>
              <pre style={{ margin: 0, fontSize: '0.875rem', overflow: 'auto' }}>
{`{
  "version": "1.0",
  "staff": [
    {
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "admin",
      "status": "active",
      "expected_hours_per_week": 40.0
    }
  ],
  "contracts": [
    {
      "name": "Project A",
      "client_name": "Client X",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "budget_hours": 1000,
      "status": "active"
    }
  ],
  "deliverables": [
    {
      "contract_name": "Project A",
      "contract_client_name": "Client X",
      "name": "Deliverable 1",
      "charge_code": "PROJ_A_D1",
      "budget_hours": 500,
      "target_completion_date": "2024-06-30",
      "status": "in_progress"
    }
  ],
  "tasks": [
    {
      "deliverable_name": "Deliverable 1",
      "title": "Task 1",
      "budget_hours": 100,
      "status": "todo",
      "assignee_email": "user@example.com"
    }
  ]
}`}
              </pre>
            </Paper>

            <Typography variant="body2" paragraph>
              <strong>For Time Entries:</strong>
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
              <pre style={{ margin: 0, fontSize: '0.875rem', overflow: 'auto' }}>
{`{
  "time_entries": [
    {
      "deliverable_name": "Deliverable 1",
      "entry_date": "2024-01-15",
      "hours": 8.5,
      "note": "Work completed on task"
    }
  ]
}`}
              </pre>
            </Paper>
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
}

