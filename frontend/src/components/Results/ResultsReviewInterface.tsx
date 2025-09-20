import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Grid,
  Button,
  Alert,
  Divider,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Checkbox,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  LinearProgress,
  Snackbar
} from '@mui/material';
import {
  Download,
  Edit,
  Compare,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Visibility,
  Save,
  Cancel,
  Assignment,
  Security
} from '@mui/icons-material';
import { OptimizationResult, BlastPlan, SafetyStatus } from '../../types';
import { FragmentationCurveChart } from './FragmentationCurveChart';
import { SafetyValidationDisplay } from './SafetyValidationDisplay';
import { EngineerSignOffDialog } from './EngineerSignOffDialog';
import { ExportControlsDialog } from './ExportControlsDialog';
import { PlanComparisonDialog } from './PlanComparisonDialog';
import { PlanModificationPanel } from './PlanModificationPanel';

interface ResultsReviewInterfaceProps {
  optimizationResults: OptimizationResult[];
  selectedResult?: OptimizationResult;
  onResultSelect: (result: OptimizationResult) => void;
  onExportPlan: (result: OptimizationResult, format: string, options: any) => Promise<void>;
  onSignOffPlan: (result: OptimizationResult, signOffData: any) => Promise<void>;
  onModifyPlan: (result: OptimizationResult, modifications: any) => Promise<OptimizationResult>;
  onComparePlans: (results: OptimizationResult[]) => void;
  isLoading?: boolean;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index}>
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
);

export const ResultsReviewInterface: React.FC<ResultsReviewInterfaceProps> = ({
  optimizationResults,
  selectedResult,
  onResultSelect,
  onExportPlan,
  onSignOffPlan,
  onModifyPlan,
  onComparePlans,
  isLoading = false
}) => {
  const [tabValue, setTabValue] = useState(0);
  const [signOffDialogOpen, setSignOffDialogOpen] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [comparisonDialogOpen, setComparisonDialogOpen] = useState(false);
  const [modificationMode, setModificationMode] = useState(false);
  const [selectedForComparison, setSelectedForComparison] = useState<OptimizationResult[]>([]);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error' | 'warning' | 'info'>('info');

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleResultSelect = (result: OptimizationResult) => {
    onResultSelect(result);
    setModificationMode(false);
  };

  const handleSignOff = async (signOffData: any) => {
    if (!selectedResult) return;
    
    try {
      await onSignOffPlan(selectedResult, signOffData);
      setSignOffDialogOpen(false);
      showSnackbar('Plan signed off successfully', 'success');
    } catch (error) {
      showSnackbar('Failed to sign off plan', 'error');
    }
  };

  const handleExport = async (format: string, options: any) => {
    if (!selectedResult) return;
    
    try {
      await onExportPlan(selectedResult, format, options);
      setExportDialogOpen(false);
      showSnackbar('Plan exported successfully', 'success');
    } catch (error) {
      showSnackbar('Failed to export plan', 'error');
    }
  };

  const handleModification = async (modifications: any) => {
    if (!selectedResult) return;
    
    try {
      const modifiedResult = await onModifyPlan(selectedResult, modifications);
      onResultSelect(modifiedResult);
      setModificationMode(false);
      showSnackbar('Plan modified successfully', 'success');
    } catch (error) {
      showSnackbar('Failed to modify plan', 'error');
    }
  };

  const handleCompareSelected = () => {
    if (selectedForComparison.length >= 2) {
      onComparePlans(selectedForComparison);
      setComparisonDialogOpen(true);
    }
  };

  const toggleComparisonSelection = (result: OptimizationResult) => {
    setSelectedForComparison(prev => {
      const isSelected = prev.some(r => r === result);
      if (isSelected) {
        return prev.filter(r => r !== result);
      } else {
        return [...prev, result];
      }
    });
  };

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'warning' | 'info') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const getSafetyStatusColor = (safetyStatus?: SafetyStatus) => {
    if (!safetyStatus) return 'default';
    return safetyStatus.is_valid ? 'success' : 'error';
  };

  const getSafetyStatusIcon = (safetyStatus?: SafetyStatus) => {
    if (!safetyStatus) return <Warning />;
    return safetyStatus.is_valid ? <CheckCircle /> : <ErrorIcon />;
  };

  const canExportPlan = (result: OptimizationResult): boolean => {
    // Check if plan has valid safety status and engineer sign-off
    const hasValidSafety = result.blast_plan.safety_status?.is_valid || false;
    const hasSignOff = !!result.blast_plan.economic_metrics; // Placeholder for sign-off check
    return hasValidSafety && hasSignOff;
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Results Review
          </Typography>
          <LinearProgress />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Loading optimization results...
          </Typography>
        </CardContent>
      </Card>
    );
  }

  if (optimizationResults.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Results Review
          </Typography>
          <Alert severity="info">
            No optimization results available. Run an optimization to review results here.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box>
      {/* Results Selection Header */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Results Review ({optimizationResults.length} results)
            </Typography>
            
            <Box display="flex" gap={1}>
              <Button
                variant="outlined"
                startIcon={<Compare />}
                onClick={handleCompareSelected}
                disabled={selectedForComparison.length < 2}
                size="small"
              >
                Compare ({selectedForComparison.length})
              </Button>
              
              {selectedResult && (
                <>
                  <Button
                    variant="outlined"
                    startIcon={<Edit />}
                    onClick={() => setModificationMode(!modificationMode)}
                    size="small"
                  >
                    {modificationMode ? 'Cancel Edit' : 'Modify Plan'}
                  </Button>
                  
                  <Button
                    variant="outlined"
                    startIcon={<Assignment />}
                    onClick={() => setSignOffDialogOpen(true)}
                    disabled={!selectedResult.blast_plan.safety_status?.is_valid}
                    size="small"
                  >
                    Sign Off
                  </Button>
                  
                  <Button
                    variant="contained"
                    startIcon={<Download />}
                    onClick={() => setExportDialogOpen(true)}
                    disabled={!canExportPlan(selectedResult)}
                    size="small"
                  >
                    Export
                  </Button>
                </>
              )}
            </Box>
          </Box>

          {/* Results Grid */}
          <Grid container spacing={2}>
            {optimizationResults.map((result, index) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <Card 
                  variant={selectedResult === result ? "elevation" : "outlined"}
                  sx={{ 
                    cursor: 'pointer',
                    border: selectedResult === result ? 2 : 1,
                    borderColor: selectedResult === result ? 'primary.main' : 'divider'
                  }}
                  onClick={() => handleResultSelect(result)}
                >
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                      <Chip
                        label={result.solver_info.algorithm}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                      
                      <Box display="flex" gap={0.5}>
                        <Checkbox
                          size="small"
                          checked={selectedForComparison.includes(result)}
                          onChange={() => toggleComparisonSelection(result)}
                          onClick={(e) => e.stopPropagation()}
                        />
                        
                        <Chip
                          icon={getSafetyStatusIcon(result.blast_plan.safety_status)}
                          label={result.blast_plan.safety_status?.is_valid ? 'Safe' : 'Unsafe'}
                          size="small"
                          color={getSafetyStatusColor(result.blast_plan.safety_status)}
                          variant="outlined"
                        />
                      </Box>
                    </Box>
                    
                    <Typography variant="h6" color="primary">
                      {result.objective_value.toFixed(2)}
                    </Typography>
                    
                    <Typography variant="body2" color="text.secondary">
                      Runtime: {result.solver_info.runtime_seconds.toFixed(1)}s
                    </Typography>
                    
                    <Typography variant="body2" color="text.secondary">
                      Holes: {result.blast_plan.holes.length}
                    </Typography>
                    
                    <Typography variant="body2" color="text.secondary">
                      Total Charge: {result.blast_plan.holes.reduce((sum, hole) => sum + hole.charge_kg, 0).toFixed(1)} kg
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {/* Detailed Review Tabs */}
      {selectedResult && (
        <Card>
          <CardContent>
            <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
              <Tab label="Fragmentation Analysis" />
              <Tab label="Safety Validation" />
              <Tab label="Plan Details" />
              <Tab label="Economic Analysis" />
            </Tabs>

            <TabPanel value={tabValue} index={0}>
              {/* Fragmentation Analysis */}
              <Grid container spacing={3}>
                <Grid item xs={12} md={8}>
                  <FragmentationCurveChart
                    fragmentationCurve={selectedResult.blast_plan.predicted_fragmentation}
                    targetP80={80} // This should come from optimization objectives
                    title="Predicted Fragmentation Curve"
                  />
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <Typography variant="h6" gutterBottom>
                    Fragmentation Metrics
                  </Typography>
                  
                  {selectedResult.blast_plan.predicted_fragmentation && (
                    <Box>
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2" color="text.secondary">P10:</Typography>
                        <Typography variant="body2">
                          {selectedResult.blast_plan.predicted_fragmentation.p10.toFixed(1)} mm
                        </Typography>
                      </Box>
                      
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2" color="text.secondary">P50:</Typography>
                        <Typography variant="body2">
                          {selectedResult.blast_plan.predicted_fragmentation.p50.toFixed(1)} mm
                        </Typography>
                      </Box>
                      
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2" color="text.secondary">P80:</Typography>
                        <Typography variant="body2" fontWeight="bold">
                          {selectedResult.blast_plan.predicted_fragmentation.p80.toFixed(1)} mm
                        </Typography>
                      </Box>
                      
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Typography variant="body2" color="text.secondary">Mean Size:</Typography>
                        <Typography variant="body2">
                          {selectedResult.blast_plan.predicted_fragmentation.mean.toFixed(1)} mm
                        </Typography>
                      </Box>
                      
                      <Box display="flex" justifyContent="space-between">
                        <Typography variant="body2" color="text.secondary">Uniformity Index:</Typography>
                        <Typography variant="body2">
                          {selectedResult.blast_plan.predicted_fragmentation.uniformity_index.toFixed(2)}
                        </Typography>
                      </Box>
                    </Box>
                  )}
                </Grid>
              </Grid>
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              {/* Safety Validation */}
              <SafetyValidationDisplay
                safetyStatus={selectedResult.blast_plan.safety_status}
                blastPlan={selectedResult.blast_plan}
              />
            </TabPanel>

            <TabPanel value={tabValue} index={2}>
              {/* Plan Details */}
              {modificationMode ? (
                <PlanModificationPanel
                  blastPlan={selectedResult.blast_plan}
                  onSave={handleModification}
                  onCancel={() => setModificationMode(false)}
                />
              ) : (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Blast Plan Details
                  </Typography>
                  
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle1" gutterBottom>
                        Plan Summary
                      </Typography>
                      
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Total Holes:</Typography>
                        <Typography variant="body1">{selectedResult.blast_plan.holes.length}</Typography>
                      </Box>
                      
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Total Charge:</Typography>
                        <Typography variant="body1">
                          {selectedResult.blast_plan.holes.reduce((sum, hole) => sum + hole.charge_kg, 0).toFixed(1)} kg
                        </Typography>
                      </Box>
                      
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Average Charge per Hole:</Typography>
                        <Typography variant="body1">
                          {(selectedResult.blast_plan.holes.reduce((sum, hole) => sum + hole.charge_kg, 0) / selectedResult.blast_plan.holes.length).toFixed(1)} kg
                        </Typography>
                      </Box>
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle1" gutterBottom>
                        Optimization Info
                      </Typography>
                      
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Algorithm:</Typography>
                        <Typography variant="body1">{selectedResult.solver_info.algorithm}</Typography>
                      </Box>
                      
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Runtime:</Typography>
                        <Typography variant="body1">{selectedResult.solver_info.runtime_seconds.toFixed(1)} seconds</Typography>
                      </Box>
                      
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Iterations:</Typography>
                        <Typography variant="body1">{selectedResult.solver_info.iterations.toLocaleString()}</Typography>
                      </Box>
                      
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Objective Value:</Typography>
                        <Typography variant="body1">{selectedResult.objective_value.toFixed(2)}</Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </Box>
              )}
            </TabPanel>

            <TabPanel value={tabValue} index={3}>
              {/* Economic Analysis */}
              <Typography variant="h6" gutterBottom>
                Economic Analysis
              </Typography>
              
              {selectedResult.blast_plan.economic_metrics ? (
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">Total Cost:</Typography>
                      <Typography variant="h5" color="primary">
                        ${selectedResult.blast_plan.economic_metrics.estimated_cost.toFixed(2)}
                      </Typography>
                    </Box>
                    
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">Powder Factor:</Typography>
                      <Typography variant="body1">
                        {selectedResult.blast_plan.economic_metrics.powder_factor.toFixed(3)} kg/t
                      </Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} md={6}>
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">Cost per Hole:</Typography>
                      <Typography variant="body1">
                        ${(selectedResult.blast_plan.economic_metrics.estimated_cost / selectedResult.blast_plan.economic_metrics.total_holes).toFixed(2)}
                      </Typography>
                    </Box>
                    
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">Cost per kg Charge:</Typography>
                      <Typography variant="body1">
                        ${(selectedResult.blast_plan.economic_metrics.estimated_cost / selectedResult.blast_plan.economic_metrics.total_charge).toFixed(2)}
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              ) : (
                <Alert severity="info">
                  Economic metrics not available for this result.
                </Alert>
              )}
            </TabPanel>
          </CardContent>
        </Card>
      )}

      {/* Dialogs */}
      <EngineerSignOffDialog
        open={signOffDialogOpen}
        onClose={() => setSignOffDialogOpen(false)}
        onSignOff={handleSignOff}
        blastPlan={selectedResult?.blast_plan}
      />

      <ExportControlsDialog
        open={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        onExport={handleExport}
        blastPlan={selectedResult?.blast_plan}
      />

      <PlanComparisonDialog
        open={comparisonDialogOpen}
        onClose={() => setComparisonDialogOpen(false)}
        results={selectedForComparison}
      />

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
      />
    </Box>
  );
};

export default ResultsReviewInterface;