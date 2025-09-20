import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Chip,
  Grid,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
  Alert,
  Divider
} from '@mui/material';
import {
  Visibility,
  Download,
  Compare,
  Star,
  StarBorder,
  TrendingUp,
  TrendingDown,
  Remove,
  RateReview
} from '@mui/icons-material';
import { OptimizationResult, BlastPlan } from '../../types';
import { ResultsReviewInterface } from '../Results';
import resultsService from '../../services/resultsService';

interface OptimizationResultsProps {
  results: OptimizationResult[];
  onSelectResult?: (result: OptimizationResult) => void;
  onCompareResults?: (results: OptimizationResult[]) => void;
  onDownloadResult?: (result: OptimizationResult) => void;
  selectedResults?: OptimizationResult[];
  showComparison?: boolean;
  showDetailedReview?: boolean;
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

export const OptimizationResultsComponent: React.FC<OptimizationResultsProps> = ({
  results,
  onSelectResult,
  onCompareResults,
  onDownloadResult,
  selectedResults = [],
  showComparison = true,
  showDetailedReview = false
}) => {
  const [tabValue, setTabValue] = useState(0);
  const [compareMode, setCompareMode] = useState(false);
  const [comparisonResults, setComparisonResults] = useState<OptimizationResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<OptimizationResult | undefined>(results[0]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const toggleCompareMode = () => {
    setCompareMode(!compareMode);
    if (!compareMode) {
      setComparisonResults([]);
    }
  };

  const toggleResultComparison = (result: OptimizationResult) => {
    if (comparisonResults.includes(result)) {
      setComparisonResults(comparisonResults.filter(r => r !== result));
    } else {
      setComparisonResults([...comparisonResults, result]);
    }
  };

  const handleCompareSelected = () => {
    if (onCompareResults && comparisonResults.length >= 2) {
      onCompareResults(comparisonResults);
    }
  };

  const getBestResult = (): OptimizationResult | null => {
    if (results.length === 0) return null;
    return results.reduce((best, current) => 
      current.objective_value < best.objective_value ? current : best
    );
  };

  const getObjectiveTrend = (result: OptimizationResult): 'up' | 'down' | 'neutral' => {
    const bestResult = getBestResult();
    if (!bestResult || result === bestResult) return 'neutral';
    
    const percentDiff = ((result.objective_value - bestResult.objective_value) / bestResult.objective_value) * 100;
    return percentDiff > 5 ? 'up' : percentDiff < -5 ? 'down' : 'neutral';
  };

  const formatObjectiveValue = (value: number): string => {
    return value.toFixed(2);
  };

  const formatRuntime = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  const getAlgorithmColor = (algorithm: string) => {
    const colors: Record<string, any> = {
      'cp_sat': 'primary',
      'scipy_de': 'secondary',
      'scipy_slsqp': 'success',
      'genetic': 'warning'
    };
    return colors[algorithm] || 'default';
  };

  // Handle result selection for detailed review
  const handleResultSelect = (result: OptimizationResult) => {
    setSelectedResult(result);
    onSelectResult?.(result);
  };

  // Handle export functionality
  const handleExportPlan = async (result: OptimizationResult, format: string, options: any) => {
    try {
      const blob = await resultsService.exportBlastPlan(
        result.blast_plan.id || 0,
        format,
        options
      );
      
      const filename = resultsService.generateExportFilename(format, 'blast_plan');
      resultsService.downloadFile(blob, filename);
    } catch (error) {
      console.error('Export failed:', error);
      throw error;
    }
  };

  // Handle sign-off functionality
  const handleSignOffPlan = async (result: OptimizationResult, signOffData: any) => {
    try {
      await resultsService.signOffBlastPlan(
        result.blast_plan.id || 0,
        signOffData
      );
      // Update the result with sign-off status
      // This would typically trigger a refresh of the results
    } catch (error) {
      console.error('Sign-off failed:', error);
      throw error;
    }
  };

  // Handle plan modification
  const handleModifyPlan = async (result: OptimizationResult, modifications: any) => {
    try {
      const response = await resultsService.modifyBlastPlan(
        result.blast_plan.id || 0,
        modifications
      );
      return response.data;
    } catch (error) {
      console.error('Modification failed:', error);
      throw error;
    }
  };

  if (results.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Optimization Results
          </Typography>
          <Alert severity="info">
            No optimization results available. Run an optimization to see results here.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  // If detailed review is enabled, show the full results review interface
  if (showDetailedReview) {
    return (
      <ResultsReviewInterface
        optimizationResults={results}
        selectedResult={selectedResult}
        onResultSelect={handleResultSelect}
        onExportPlan={handleExportPlan}
        onSignOffPlan={handleSignOffPlan}
        onModifyPlan={handleModifyPlan}
        onComparePlans={onCompareResults || (() => {})}
      />
    );
  }

  const bestResult = getBestResult();

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            Optimization Results ({results.length})
          </Typography>
          
          <Box display="flex" gap={1}>
            {showComparison && (
              <>
                <Button
                  variant={compareMode ? "contained" : "outlined"}
                  startIcon={<Compare />}
                  onClick={toggleCompareMode}
                  size="small"
                >
                  Compare Mode
                </Button>
                
                {compareMode && comparisonResults.length >= 2 && (
                  <Button
                    variant="contained"
                    onClick={handleCompareSelected}
                    size="small"
                  >
                    Compare Selected ({comparisonResults.length})
                  </Button>
                )}
              </>
            )}
            
            <Button
              variant="outlined"
              startIcon={<RateReview />}
              onClick={() => {/* Toggle detailed review mode */}}
              size="small"
            >
              Detailed Review
            </Button>
          </Box>
        </Box>

        <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
          <Tab label="Results Summary" />
          <Tab label="Detailed Comparison" />
          <Tab label="Performance Metrics" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          {/* Results Summary */}
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>
                    {compareMode && (
                      <Tooltip title="Select for comparison">
                        <Compare fontSize="small" />
                      </Tooltip>
                    )}
                  </TableCell>
                  <TableCell>Algorithm</TableCell>
                  <TableCell align="right">Objective Value</TableCell>
                  <TableCell align="right">Runtime</TableCell>
                  <TableCell align="right">Iterations</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {results.map((result, index) => {
                  const isBest = result === bestResult;
                  const trend = getObjectiveTrend(result);
                  const isSelected = comparisonResults.includes(result);
                  
                  return (
                    <TableRow 
                      key={index}
                      sx={{ 
                        backgroundColor: isBest ? 'success.light' : 'inherit',
                        opacity: compareMode && !isSelected ? 0.6 : 1
                      }}
                    >
                      <TableCell>
                        {compareMode ? (
                          <IconButton
                            size="small"
                            onClick={() => toggleResultComparison(result)}
                            color={isSelected ? "primary" : "default"}
                          >
                            {isSelected ? <Star /> : <StarBorder />}
                          </IconButton>
                        ) : (
                          isBest && (
                            <Tooltip title="Best result">
                              <Star color="warning" fontSize="small" />
                            </Tooltip>
                          )
                        )}
                      </TableCell>
                      
                      <TableCell>
                        <Chip
                          label={result.solver_info.algorithm}
                          color={getAlgorithmColor(result.solver_info.algorithm)}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      
                      <TableCell align="right">
                        <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5}>
                          <Typography variant="body2" fontWeight={isBest ? "bold" : "normal"}>
                            {formatObjectiveValue(result.objective_value)}
                          </Typography>
                          {trend === 'up' && <TrendingUp color="error" fontSize="small" />}
                          {trend === 'down' && <TrendingDown color="success" fontSize="small" />}
                        </Box>
                      </TableCell>
                      
                      <TableCell align="right">
                        {formatRuntime(result.solver_info.runtime_seconds)}
                      </TableCell>
                      
                      <TableCell align="right">
                        {result.solver_info.iterations.toLocaleString()}
                      </TableCell>
                      
                      <TableCell>
                        <Chip
                          label="Completed"
                          color="success"
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      
                      <TableCell align="center">
                        <Box display="flex" gap={0.5}>
                          <Tooltip title="View details">
                            <IconButton
                              size="small"
                              onClick={() => onSelectResult?.(result)}
                            >
                              <Visibility />
                            </IconButton>
                          </Tooltip>
                          
                          <Tooltip title="Download result">
                            <IconButton
                              size="small"
                              onClick={() => onDownloadResult?.(result)}
                            >
                              <Download />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {/* Detailed Comparison */}
          <Grid container spacing={3}>
            {results.slice(0, 3).map((result, index) => (
              <Grid item xs={12} md={4} key={index}>
                <Card variant="outlined" sx={{ height: '100%' }}>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                      <Chip
                        label={result.solver_info.algorithm}
                        color={getAlgorithmColor(result.solver_info.algorithm)}
                        size="small"
                      />
                      {result === bestResult && (
                        <Star color="warning" fontSize="small" />
                      )}
                    </Box>
                    
                    <Typography variant="h4" color="primary" gutterBottom>
                      {formatObjectiveValue(result.objective_value)}
                    </Typography>
                    
                    <Divider sx={{ my: 1 }} />
                    
                    <Box display="flex" justifyContent="space-between" mb={1}>
                      <Typography variant="body2" color="text.secondary">
                        Runtime:
                      </Typography>
                      <Typography variant="body2">
                        {formatRuntime(result.solver_info.runtime_seconds)}
                      </Typography>
                    </Box>
                    
                    <Box display="flex" justifyContent="space-between" mb={1}>
                      <Typography variant="body2" color="text.secondary">
                        Iterations:
                      </Typography>
                      <Typography variant="body2">
                        {result.solver_info.iterations.toLocaleString()}
                      </Typography>
                    </Box>
                    
                    <Box display="flex" justifyContent="space-between" mb={1}>
                      <Typography variant="body2" color="text.secondary">
                        Total Holes:
                      </Typography>
                      <Typography variant="body2">
                        {result.blast_plan.holes.length}
                      </Typography>
                    </Box>
                    
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        Total Charge:
                      </Typography>
                      <Typography variant="body2">
                        {result.blast_plan.holes.reduce((sum, hole) => sum + hole.charge_kg, 0).toFixed(1)} kg
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {/* Performance Metrics */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Algorithm Performance
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Algorithm</TableCell>
                      <TableCell align="right">Avg Runtime</TableCell>
                      <TableCell align="right">Best Objective</TableCell>
                      <TableCell align="right">Success Rate</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(
                      results.reduce((acc, result) => {
                        const algo = result.solver_info.algorithm;
                        if (!acc[algo]) {
                          acc[algo] = {
                            count: 0,
                            totalRuntime: 0,
                            bestObjective: Infinity,
                            successes: 0
                          };
                        }
                        acc[algo].count++;
                        acc[algo].totalRuntime += result.solver_info.runtime_seconds;
                        acc[algo].bestObjective = Math.min(acc[algo].bestObjective, result.objective_value);
                        acc[algo].successes++;
                        return acc;
                      }, {} as Record<string, any>)
                    ).map(([algorithm, stats]) => (
                      <TableRow key={algorithm}>
                        <TableCell>
                          <Chip
                            label={algorithm}
                            color={getAlgorithmColor(algorithm)}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">
                          {formatRuntime(stats.totalRuntime / stats.count)}
                        </TableCell>
                        <TableCell align="right">
                          {formatObjectiveValue(stats.bestObjective)}
                        </TableCell>
                        <TableCell align="right">
                          {((stats.successes / stats.count) * 100).toFixed(0)}%
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Solution Quality
              </Typography>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Best Objective Value
                </Typography>
                <Typography variant="h4" color="success.main" gutterBottom>
                  {bestResult ? formatObjectiveValue(bestResult.objective_value) : 'N/A'}
                </Typography>
                
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Average Objective Value
                </Typography>
                <Typography variant="h5" gutterBottom>
                  {formatObjectiveValue(
                    results.reduce((sum, r) => sum + r.objective_value, 0) / results.length
                  )}
                </Typography>
                
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Standard Deviation
                </Typography>
                <Typography variant="body1">
                  {(() => {
                    const mean = results.reduce((sum, r) => sum + r.objective_value, 0) / results.length;
                    const variance = results.reduce((sum, r) => sum + Math.pow(r.objective_value - mean, 2), 0) / results.length;
                    return Math.sqrt(variance).toFixed(2);
                  })()}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </TabPanel>
      </CardContent>
    </Card>
  );
};

export default OptimizationResultsComponent;