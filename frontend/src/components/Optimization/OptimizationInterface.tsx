import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Button,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Card,
  CardContent,
  Tabs,
  Tab,
  Divider
} from '@mui/material';
import {
  PlayArrow,
  Settings,
  History,
  Compare
} from '@mui/icons-material';
import OptimizationConfigComponent from './OptimizationConfig';
import OptimizationProgressComponent from './OptimizationProgress';
import OptimizationResultsComponent from './OptimizationResults';
import { 
  OptimizationConfig, 
  OptimizationSession, 
  OptimizationResult,
  OptimizationHistory,
  BlastPlan 
} from '../../types';
import optimizationService from '../../services/optimizationService';

interface OptimizationInterfaceProps {
  blastPlan: BlastPlan;
  onOptimizationComplete?: (result: OptimizationResult) => void;
  onBlastPlanUpdate?: (updatedPlan: BlastPlan) => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index}>
    {value === index && <Box>{children}</Box>}
  </div>
);

const defaultOptimizationConfig: OptimizationConfig = {
  algorithms: ['cp_sat', 'scipy_de'],
  max_iterations: 1000,
  timeout_seconds: 300,
  convergence_tolerance: 1e-6,
  population_size: 50,
  mutation_rate: 0.1,
  crossover_rate: 0.8
};

export const OptimizationInterface: React.FC<OptimizationInterfaceProps> = ({
  blastPlan,
  onOptimizationComplete,
  onBlastPlanUpdate
}) => {
  const [tabValue, setTabValue] = useState(0);
  const [config, setConfig] = useState<OptimizationConfig>(defaultOptimizationConfig);
  const [currentSession, setCurrentSession] = useState<OptimizationSession | null>(null);
  const [optimizationHistory, setOptimizationHistory] = useState<OptimizationHistory | null>(null);
  const [results, setResults] = useState<OptimizationResult[]>([]);
  const [presets, setPresets] = useState<Array<{ id: number; name: string; config: OptimizationConfig }>>([]);
  
  // UI State
  const [isStarting, setIsStarting] = useState(false);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [showComparisonDialog, setShowComparisonDialog] = useState(false);
  const [comparisonResults, setComparisonResults] = useState<OptimizationResult[]>([]);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' }>({
    open: false,
    message: '',
    severity: 'info'
  });

  // Load optimization history and presets on mount
  useEffect(() => {
    loadOptimizationHistory();
    loadOptimizationPresets();
  }, [blastPlan.id]);

  // Poll for active optimizations
  useEffect(() => {
    const checkActiveOptimizations = async () => {
      try {
        const response = await optimizationService.listActiveOptimizations();
        const activeOpts = response.data.active_optimizations;
        
        // Find any active optimization for this blast plan
        const activeOpt = activeOpts.find(opt => 
          opt.blast_id === blastPlan.id && 
          (opt.status === 'running' || opt.status === 'started')
        );
        
        if (activeOpt && !currentSession) {
          setCurrentSession(activeOpt);
        }
      } catch (error) {
        console.error('Failed to check active optimizations:', error);
      }
    };

    checkActiveOptimizations();
    const interval = setInterval(checkActiveOptimizations, 10000); // Check every 10 seconds
    
    return () => clearInterval(interval);
  }, [blastPlan.id, currentSession]);

  const loadOptimizationHistory = async () => {
    try {
      const response = await optimizationService.getOptimizationHistory(blastPlan.id!);
      setOptimizationHistory(response.data);
      
      // Extract results from completed sessions
      const completedResults = response.data.sessions
        .filter(session => session.status === 'completed' && session.results)
        .flatMap(session => session.results!);
      
      setResults(completedResults);
    } catch (error) {
      console.error('Failed to load optimization history:', error);
    }
  };

  const loadOptimizationPresets = async () => {
    try {
      const response = await optimizationService.getOptimizationPresets();
      setPresets(response.data);
    } catch (error) {
      console.error('Failed to load optimization presets:', error);
    }
  };

  const handleStartOptimization = async () => {
    if (!blastPlan.id) {
      showSnackbar('Blast plan must be saved before optimization', 'error');
      return;
    }

    if (config.algorithms.length === 0) {
      showSnackbar('Please select at least one optimization algorithm', 'error');
      return;
    }

    setIsStarting(true);
    
    try {
      const response = await optimizationService.startOptimization(blastPlan.id, config);
      
      if (response.success) {
        setCurrentSession(response.data);
        showSnackbar('Optimization started successfully', 'success');
        setTabValue(1); // Switch to progress tab
      } else {
        showSnackbar(response.message || 'Failed to start optimization', 'error');
      }
    } catch (error: any) {
      console.error('Failed to start optimization:', error);
      showSnackbar(
        error.response?.data?.detail || 'Failed to start optimization', 
        'error'
      );
    } finally {
      setIsStarting(false);
    }
  };

  const handleCancelOptimization = async () => {
    if (!currentSession) return;

    try {
      await optimizationService.cancelOptimization(currentSession.optimization_id);
      showSnackbar('Optimization cancelled', 'info');
      setCurrentSession(null);
    } catch (error: any) {
      console.error('Failed to cancel optimization:', error);
      showSnackbar('Failed to cancel optimization', 'error');
    }
  };

  const handleRestartOptimization = () => {
    setCurrentSession(null);
    handleStartOptimization();
  };

  const handleSavePreset = async (name: string, presetConfig: OptimizationConfig) => {
    try {
      await optimizationService.saveOptimizationPreset(name, presetConfig);
      await loadOptimizationPresets();
      showSnackbar('Preset saved successfully', 'success');
    } catch (error: any) {
      console.error('Failed to save preset:', error);
      showSnackbar('Failed to save preset', 'error');
    }
  };

  const handleSelectResult = (result: OptimizationResult) => {
    // Update blast plan with selected result
    if (onBlastPlanUpdate) {
      onBlastPlanUpdate(result.blast_plan);
    }
    
    if (onOptimizationComplete) {
      onOptimizationComplete(result);
    }
    
    showSnackbar('Blast plan updated with optimization result', 'success');
  };

  const handleCompareResults = (resultsToCompare: OptimizationResult[]) => {
    setComparisonResults(resultsToCompare);
    setShowComparisonDialog(true);
  };

  const handleDownloadResult = async (result: OptimizationResult) => {
    try {
      // This would typically call an export API
      const dataStr = JSON.stringify(result, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `optimization_result_${result.solver_info.algorithm}_${Date.now()}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      URL.revokeObjectURL(url);
      showSnackbar('Result downloaded successfully', 'success');
    } catch (error) {
      console.error('Failed to download result:', error);
      showSnackbar('Failed to download result', 'error');
    }
  };

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const canStartOptimization = !currentSession || 
    (currentSession.status !== 'running' && currentSession.status !== 'started');

  return (
    <Box>
      {/* Header */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h5">
              Optimization Interface
            </Typography>
            
            <Box display="flex" gap={1}>
              <Button
                variant="outlined"
                startIcon={<Settings />}
                onClick={() => setShowConfigDialog(true)}
              >
                Configure
              </Button>
              
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={handleStartOptimization}
                disabled={!canStartOptimization || isStarting}
                loading={isStarting}
              >
                {isStarting ? 'Starting...' : 'Start Optimization'}
              </Button>
            </Box>
          </Box>
          
          {!canStartOptimization && (
            <Alert severity="info" sx={{ mt: 2 }}>
              An optimization is currently running for this blast plan.
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Main Content */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Configuration" />
          <Tab label="Progress" />
          <Tab label="Results" />
          <Tab label="History" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <OptimizationConfigComponent
          config={config}
          onChange={setConfig}
          onSavePreset={handleSavePreset}
          presets={presets}
          onLoadPreset={setConfig}
        />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <OptimizationProgressComponent
          session={currentSession}
          onCancel={handleCancelOptimization}
          onRestart={handleRestartOptimization}
        />
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <OptimizationResultsComponent
          results={results}
          onSelectResult={handleSelectResult}
          onCompareResults={handleCompareResults}
          onDownloadResult={handleDownloadResult}
        />
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        {optimizationHistory && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Optimization History
              </Typography>
              
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Total Sessions: {optimizationHistory.total_count}
              </Typography>
              
              {optimizationHistory.sessions.length === 0 ? (
                <Alert severity="info">
                  No optimization history available for this blast plan.
                </Alert>
              ) : (
                <Box>
                  {optimizationHistory.sessions.map((session, index) => (
                    <Card key={session.optimization_id} variant="outlined" sx={{ mb: 2 }}>
                      <CardContent>
                        <Box display="flex" justifyContent="space-between" alignItems="center">
                          <Box>
                            <Typography variant="subtitle2">
                              Session {session.optimization_id}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Started: {new Date(session.started_at).toLocaleString()}
                            </Typography>
                            {session.completed_at && (
                              <Typography variant="body2" color="text.secondary">
                                Completed: {new Date(session.completed_at).toLocaleString()}
                              </Typography>
                            )}
                          </Box>
                          
                          <Box textAlign="right">
                            <Typography variant="body2" color="text.secondary">
                              Status: {session.status}
                            </Typography>
                            {session.results && (
                              <Typography variant="body2" color="text.secondary">
                                Results: {session.results.length}
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        )}
      </TabPanel>

      {/* Configuration Dialog */}
      <Dialog
        open={showConfigDialog}
        onClose={() => setShowConfigDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Optimization Configuration</DialogTitle>
        <DialogContent>
          <OptimizationConfigComponent
            config={config}
            onChange={setConfig}
            onSavePreset={handleSavePreset}
            presets={presets}
            onLoadPreset={setConfig}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConfigDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Comparison Dialog */}
      <Dialog
        open={showComparisonDialog}
        onClose={() => setShowComparisonDialog(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <Compare />
            Results Comparison ({comparisonResults.length} results)
          </Box>
        </DialogTitle>
        <DialogContent>
          <OptimizationResultsComponent
            results={comparisonResults}
            showComparison={false}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowComparisonDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default OptimizationInterface;