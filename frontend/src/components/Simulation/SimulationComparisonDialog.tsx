/**
 * Dialog for comparing simulation results
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
} from '@mui/material';

import { simulationService, SimulationComparison } from '../../services/simulationService';

interface SimulationComparisonDialogProps {
  open: boolean;
  onClose: () => void;
  jobIds: string[];
}

export const SimulationComparisonDialog: React.FC<SimulationComparisonDialogProps> = ({
  open,
  onClose,
  jobIds,
}) => {
  const [comparison, setComparison] = useState<SimulationComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && jobIds.length >= 2) {
      loadComparison();
    }
  }, [open, jobIds]);

  const loadComparison = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await simulationService.compareResults(jobIds);
      setComparison(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to compare results');
    } finally {
      setLoading(false);
    }
  };

  const renderFragmentationComparison = () => {
    if (!comparison?.fragmentation_comparison) return null;

    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Fragmentation Comparison</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Simulation Type</TableCell>
                  <TableCell align="right">P10 (mm)</TableCell>
                  <TableCell align="right">P50 (mm)</TableCell>
                  <TableCell align="right">P80 (mm)</TableCell>
                  <TableCell align="right">Mean (mm)</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.entries(comparison.fragmentation_comparison).map(([simType, data]) => {
                  if (typeof data !== 'object' || !data.P10) return null;
                  return (
                    <TableRow key={simType}>
                      <TableCell>{simulationService.formatSimulationType(simType as any)}</TableCell>
                      <TableCell align="right">{data.P10?.toFixed(1) || 'N/A'}</TableCell>
                      <TableCell align="right">{data.P50?.toFixed(1) || 'N/A'}</TableCell>
                      <TableCell align="right">{data.P80?.toFixed(1) || 'N/A'}</TableCell>
                      <TableCell align="right">{data.mean?.toFixed(1) || 'N/A'}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    );
  };

  const renderPerformanceComparison = () => {
    if (!comparison?.performance_metrics) return null;

    const metrics = comparison.performance_metrics;

    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Performance Comparison</Typography>
          <Table size="small">
            <TableBody>
              <TableRow>
                <TableCell>Fastest Runtime</TableCell>
                <TableCell align="right">{metrics.fastest_runtime?.toFixed(2)} seconds</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Slowest Runtime</TableCell>
                <TableCell align="right">{metrics.slowest_runtime?.toFixed(2)} seconds</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Average Runtime</TableCell>
                <TableCell align="right">{metrics.average_runtime?.toFixed(2)} seconds</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Success Rate</TableCell>
                <TableCell align="right">{(metrics.success_rate * 100).toFixed(1)}%</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    );
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Simulation Results Comparison</DialogTitle>
      
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        {loading ? (
          <Box display="flex" justifyContent="center" p={3}>
            <CircularProgress />
          </Box>
        ) : comparison ? (
          <>
            {renderFragmentationComparison()}
            {renderPerformanceComparison()}
          </>
        ) : (
          <Typography>No comparison data available</Typography>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};