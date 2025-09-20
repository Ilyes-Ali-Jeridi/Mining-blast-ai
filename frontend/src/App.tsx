import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { store } from './store';
import { AppLayout } from './components/Layout/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { Sites } from './pages/Sites';
import { SiteCreate } from './pages/SiteCreate';
import { BlastPlans } from './pages/BlastPlans';
import { Safety } from './pages/Safety';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';
import { OptimizationPage } from './pages/Optimization';
import { AdminPage } from './pages/Admin';
import SyntheticData from './pages/SyntheticData';
import MLPipelinePage from './pages/MLPipeline';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <AppLayout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/sites" element={<Sites />} />
              <Route path="/sites/new" element={<SiteCreate />} />
              <Route path="/blast-plans" element={<BlastPlans />} />
              <Route path="/blast-plans/new" element={<BlastPlans />} />
              <Route path="/blast-plans/:blastId/optimize" element={<OptimizationPage />} />
              <Route path="/safety" element={<Safety />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/synthetic" element={<SyntheticData />} />
              <Route path="/ml-pipeline" element={<MLPipelinePage />} />
              <Route path="/admin" element={<AdminPage />} />
            </Routes>
          </AppLayout>
        </Router>
      </ThemeProvider>
    </Provider>
  );
}

export default App;
