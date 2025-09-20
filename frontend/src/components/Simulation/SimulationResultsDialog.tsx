/**
 * Dialog for viewing simulation results
 */

import React from 'react';
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
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material';

import { SimulationJob, simulationService } from '../../services/simulationService';

interface SimulationResultsDialogProps {
  open: boolean;
  onClose: () => void;
  job: SimulationJob | null;
}

export const SimulationResultsDialog: React.FC<SimulationResultsDialogProps> = ({
  open,
  onClose,
  job,
}) => {
  if (!job?.result) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogContent>
          <Typography>No results available for this simulation</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>
    );
  }

  const result = job.result;

  const renderFragmentationResults = () => {
    if (!result.fragment_size_distribution) return null;

    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Fragmentation Results</Typography>
          <Grid container spacing={2}>
            {Object.entries(result.fragment_size_distribution).map(([key, value]) => (
              <Grid item xs={6} sm={3} key={key}>
                <Paper sx={{ p: 2, textAlign: 'center' }}>
                  <Typography variant="h6">{typeof value === 'number' ? value.toFixed(1) : value}</Typography>
                  <Typography variant="caption">{key}</Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    );
  };

  const renderPPVResults = () => {
    if (!result.ppv_predictions || Object.keys(result.ppv_predictions).length === 0) return null;

    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>PPV Predictions</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Receptor</TableCell>
                  <TableCell align="right">PPV (mm/s)</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.entries(result.ppv_predictions).map(([receptor, ppv]) => (
                  <TableRow key={receptor}>
                    <TableCell>{receptor}</TableCell>
                    <TableCell align="right">{ppv.toFixed(2)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    );
  };

  const renderMetrics = () => (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>Simulation Metrics</Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <Typography variant="body2" color="text.secondary">Runtime</Typography>
            <Typography variant="body1">{result.runtime_seconds.toFixed(2)} seconds</Typography>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Typography variant="body2" color="text.secondary">Status</Typography>
            <Chip 
              label={result.success ? 'Success' : 'Failed'} 
              color={result.success ? 'success' : 'error'} 
              size="small" 
            />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Simulation Results - {simulationService.formatSimulationType(job.simulation_type)}
      </DialogTitle>
      
      <DialogContent>
        {renderMetrics()}
        {renderFragmentationResults()}
        {renderPPVResults()}
        
        {result.warnings.length > 0 && (
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom color="warning.main">Warnings</Typography>
              {result.warnings.map((warning, index) => (
                <Typography key={index} variant="body2">• {warning}</Typography>
              ))}
            </CardContent>
          </Card>
        )}
        
        {result.errors.length > 0 && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom color="error.main">Errors</Typography>
              {result.errors.map((error, index) => (
                <Typography key={index} variant="body2">• {error}</Typography>
              ))}
            </CardContent>
          </Card>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};