import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { theme } from './theme';
import { AppShell } from './components/AppShell';
import { LoginPage } from './pages/LoginPage';
import { ContractsListPage } from './pages/ContractsListPage';
import { ContractDetailPage } from './pages/ContractDetailPage';
import { ContractEditPage } from './pages/ContractEditPage';
import { DeliverableDetailPage } from './pages/DeliverableDetailPage';
import { DeliverableEditPage } from './pages/DeliverableEditPage';
import { TaskEditPage } from './pages/TaskEditPage';
import { StaffListPage } from './pages/StaffListPage';
import { StaffDetailPage } from './pages/StaffDetailPage';
import { StaffEditPage } from './pages/StaffEditPage';
import { AssignmentsPage } from './pages/AssignmentsPage';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = !!localStorage.getItem('access_token');
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <AppShell>
                  <ContractsListPage />
                </AppShell>
              </PrivateRoute>
            }
          />
          <Route
            path="/contracts"
            element={
              <PrivateRoute>
                <AppShell>
                  <ContractsListPage />
                </AppShell>
              </PrivateRoute>
            }
          />
          <Route
            path="/contracts/:id/edit"
            element={
              <PrivateRoute>
                <AppShell>
                  <ContractEditPage />
                </AppShell>
              </PrivateRoute>
            }
          />
          <Route
            path="/contracts/:id"
            element={
              <PrivateRoute>
                <AppShell>
                  <ContractDetailPage />
                </AppShell>
              </PrivateRoute>
            }
          />
          <Route
            path="/deliverables/:id/edit"
            element={
              <PrivateRoute>
                <AppShell>
                  <DeliverableEditPage />
                </AppShell>
              </PrivateRoute>
            }
          />
          <Route
            path="/deliverables/:id"
            element={
              <PrivateRoute>
                <AppShell>
                  <DeliverableDetailPage />
                </AppShell>
              </PrivateRoute>
            }
          />
          <Route
            path="/tasks/:id"
            element={
              <PrivateRoute>
                <AppShell>
                  <TaskEditPage />
                </AppShell>
              </PrivateRoute>
            }
          />
          <Route
            path="/staff"
            element={
              <PrivateRoute>
                <AppShell>
                  <StaffListPage />
                </AppShell>
              </PrivateRoute>
            }
          />
          <Route
            path="/staff/:id/edit"
            element={
              <PrivateRoute>
                <AppShell>
                  <StaffEditPage />
                </AppShell>
              </PrivateRoute>
            }
          />
          <Route
            path="/staff/:id"
            element={
              <PrivateRoute>
                <AppShell>
                  <StaffDetailPage />
                </AppShell>
              </PrivateRoute>
            }
          />
          <Route
            path="/assignments"
            element={
              <PrivateRoute>
                <AppShell>
                  <AssignmentsPage />
                </AppShell>
              </PrivateRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
