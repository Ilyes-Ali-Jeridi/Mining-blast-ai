/**
 * Main interface for advanced simulation management
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Alert,
  Chip,
  Button,
  Grid,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Refresh,
  Delete,
  Compare,
  Settings,
  Info,
  CheckCircle,
  Error,
  Cancel,
  Schedule,
} from '@mui/icons-material';

import { simulationService, SimulationJob, SimulationCapabilities } from '../../services/simulationService';
import { SimulationConfigDialog } from './SimulationConfigDialog';
import { SimulationProgressDialog } from './SimulationProgressDialog';
import { SimulationResultsDialog } from './SimulationResultsDialog';
import { SimulationComparisonDialog } from './SimulationComparisonDialog';
import { InstallationGuideDialog } from './InstallationGuideDialog';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simulation-tabpanel-${index}`}
      aria-labelledby={`simulation-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export const SimulationInterface: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [capabilities, setCapabilities] = useState<SimulationCapabilities | null>(null);
  const [jobs, setJobs] = useState<SimulationJob[]>([]);
  const [selectedJobs, setSelectedJobs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Dialog states
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [progressDialogOpen, setProgressDialogOpen] = useState(false);
  const [resultsDialogOpen, setResultsDialogOpen] = useState(false);
  const [comparisonDialogOpen, setComparisonDialogOpen] = useState(false);
  const [installationDialogOpen, setInstallationDialogOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<SimulationJob | null>(null);

  // Load capabilities and jobs on mount
  useEffect(() => {
    loadCapabilities();
    loadJobs();
  }, []);

  const loadCapabilities = async () => {
    try {
      const caps = await simulationService.getCapabilities();
      setCapabilities(caps);
    } catch (err) {
      setError('Failed to load simulation capabilities');
      console.error('Error loading capabilities:', err);
    }
  };

  const loadJobs = async () => {
    try {
      setLoading(true);
      const jobList = await simulationService.listJobs({ page_size: 50 });
      setJobs(jobList.jobs);
    } catch (err) {
      setError('Failed to load simulation jobs');
      console.error('Error loading jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleCreateSimulation = () => {
    setConfigDialogOpen(true);
  };

  const handleJobCreated = (job: SimulationJob) => {
    setJobs(prev => [job, ...prev]);
    setConfigDialogOpen(false);
    
    // Open progress dialog for the new job
    setSelectedJob(job);
    setProgressDialogOpen(true);
  };

  const handleViewProgress = (job: SimulationJob) => {
    setSelectedJob(job);
    setProgressDialogOpen(true);
  };

  const handleViewResults = (job: SimulationJob) => {
    setSelectedJob(job);
    setResultsDialogOpen(true);
  };

  const handleCancelJob = async (jobId: string) => {
    try {
      await simulationService.cancelJob(jobId);
      await loadJobs(); // Refresh jobs list
    } catch (err) {
      setError('Failed to cancel simulation');
      console.error('Error cancelling job:', err);
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    try {
      await simulationService.deleteJob(jobId);
      setJobs(prev => prev.filter(job => job.job_id !== jobId));
    } catch (err) {
      setError('Failed to delete simulation');
      console.error('Error deleting job:', err);
    }
  };

  const handleCompareResults = () => {
    if (selectedJobs.length < 2) {
      setError('Select at least 2 completed simulations to compare');
      return;
    }
    setComparisonDialogOpen(true);
  };

  const handleJobSelection = (jobId: string) => {
    setSelectedJobs(prev => 
      prev.includes(jobId) 
        ? prev.filter(id => id !== jobId)
        : [...prev, jobId]
    );
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'failed':
        return <Error color="error" />;
      case 'cancelled':
        return <Cancel color="disabled" />;
      case 'running':
        return <CircularProgress size={20} />;
      case 'pending':
        return <Schedule color="warning" />;
      default:
        return <Info />;
    }
  };

  const getStatusColor = (status: string) => {
    return simulationService.getStatusColor(status as any);
  };

  const renderCapabilitiesOverview = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Simulation Capabilities
        </Typography>
        
        {capabilities ? (
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="subtitle1">Physics-Only</Typography>
                <Chip label="Always Available" color="success" size="small" />
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Fast empirical models (Kuz-Ram, PPV)
                </Typography>
              </Paper>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="subtitle1">blastFoam CFD</Typography>
                <Chip 
                  label={capabilities.blastfoam_available ? "Available" : "Not Available"} 
                  color={capabilities.blastfoam_available ? "success" : "error"} 
                  size="small" 
                />
                <Typography variant="body2" sx={{ mt: 1 }}>
                  High-fidelity blast wave simulation
                </Typography>
                {!capabilities.blastfoam_available && (
                  <Button 
                    size="small" 
                    onClick={() => setInstallationDialogOpen(true)}
                    sx={{ mt: 1 }}
                  >
                    Installation Guide
                  </Button>
                )}
              </Paper>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="subtitle1">YADE DEM</Typography>
                <Chip 
                  label={capabilities.yade_available ? "Available" : "Not Available"} 
                  color={capabilities.yade_available ? "success" : "error"} 
                  size="small" 
                />
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Discrete element fragmentation modeling
                </Typography>
                {!capabilities.yade_available && (
                  <Button 
                    size="small" 
                    onClick={() => setInstallationDialogOpen(true)}
                    sx={{ mt: 1 }}
                  >
                    Installation Guide
                  </Button>
                )}
              </Paper>
            </Grid>
          </Grid>
        ) : (
          <CircularProgress />
        )}
      </CardContent>
    </Card>
  );

  const renderJobsList = () => (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            Simulation Jobs ({jobs.length})
          </Typography>
          <Box>
            <Button
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={handleCreateSimulation}
              sx={{ mr: 1 }}
            >
              New Simulation
            </Button>
            <Button
              variant="outlined"
              startIcon={<Compare />}
              onClick={handleCompareResults}
              disabled={selectedJobs.length < 2}
              sx={{ mr: 1 }}
            >
              Compare ({selectedJobs.length})
            </Button>
            <IconButton onClick={loadJobs}>
              <Refresh />
            </IconButton>
          </Box>
        </Box>

        {loading ? (
          <Box display="flex" justifyContent="center" p={3}>
            <CircularProgress />
          </Box>
        ) : jobs.length === 0 ? (
          <Typography variant="body2" color="text.secondary" textAlign="center" py={3}>
            No simulation jobs found. Create your first simulation to get started.
          </Typography>
        ) : (
          <List>
            {jobs.map((job) => (
              <ListItem
                key={job.job_id}
                sx={{
                  border: 1,
                  borderColor: 'divider',
                  borderRadius: 1,
                  mb: 1,
                  bgcolor: selectedJobs.includes(job.job_id) ? 'action.selected' : 'background.paper'
                }}
              >
                <Box
                  sx={{ cursor: 'pointer', flexGrow: 1 }}
                  onClick={() => handleJobSelection(job.job_id)}
                >
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        {getStatusIcon(job.status)}
                        <Typography variant="subtitle2">
                          {simulationService.formatSimulationType(job.simulation_type)}
                        </Typography>
                        <Chip
                          label={simulationService.formatSimulationStatus(job.status)}
                          color={getStatusColor(job.status) as any}
                          size="small"
                        />
                        {job.blast_plan_id && (
                          <Chip label={`Plan: ${job.blast_plan_id}`} size="small" variant="outlined" />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Created: {new Date(job.created_at).toLocaleString()}
                        </Typography>
                        {job.runtime_seconds && (
                          <Typography variant="body2" color="text.secondary">
                            Runtime: {job.runtime_seconds.toFixed(1)}s
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </Box>
                
                <ListItemSecondaryAction>
                  <Box display="flex" gap={1}>
                    {job.status === 'running' && (
                      <Tooltip title="View Progress">
                        <IconButton onClick={() => handleViewProgress(job)}>
                          <Settings />
                        </IconButton>
                      </Tooltip>
                    )}
                    
                    {job.status === 'completed' && job.result && (
                      <Tooltip title="View Results">
                        <IconButton onClick={() => handleViewResults(job)}>
                          <Info />
                        </IconButton>
                      </Tooltip>
                    )}
                    
                    {job.status === 'running' && (
                      <Tooltip title="Cancel">
                        <IconButton onClick={() => handleCancelJob(job.job_id)}>
                          <Stop />
                        </IconButton>
                      </Tooltip>
                    )}
                    
                    {['completed', 'failed', 'cancelled'].includes(job.status) && (
                      <Tooltip title="Delete">
                        <IconButton onClick={() => handleDeleteJob(job.job_id)}>
                          <Delete />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  );

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Overview" />
          <Tab label="Simulations" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        {renderCapabilitiesOverview()}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        {renderJobsList()}
      </TabPanel>

      {/* Dialogs */}
      <SimulationConfigDialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        onJobCreated={handleJobCreated}
        capabilities={capabilities}
      />

      <SimulationProgressDialog
        open={progressDialogOpen}
        onClose={() => setProgressDialogOpen(false)}
        job={selectedJob}
      />

      <SimulationResultsDialog
        open={resultsDialogOpen}
        onClose={() => setResultsDialogOpen(false)}
        job={selectedJob}
      />

      <SimulationComparisonDialog
        open={comparisonDialogOpen}
        onClose={() => setComparisonDialogOpen(false)}
        jobIds={selectedJobs}
      />

      <InstallationGuideDialog
        open={installationDialogOpen}
        onClose={() => setInstallationDialogOpen(false)}
        capabilities={capabilities}
      />
    </Box>
  );
};