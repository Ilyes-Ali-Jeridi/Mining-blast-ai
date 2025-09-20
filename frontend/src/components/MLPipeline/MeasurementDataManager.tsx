/**
 * Measurement Data Manager Component
 * 
 * Manages and displays measurement data records with filtering, search, and quality assessment.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Tooltip,
  Pagination,
  Box as MuiBox,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Search,
  FilterList,
  Visibility,
  Edit,
  Delete,
  Download,
  PhotoCamera,
  GraphicEq,
  CheckCircle,
  Warning,
  Error,
  ExpandMore,
  Refresh,
} from '@mui/icons-material';

import { api } from '../../services/api';

interface MeasurementData {
  id: number;
  blast_record_id: number;
  measurement_name: string;
  measurement_type: 'fragmentation' | 'ppv' | 'vibration' | 'airblast';
  measurement_quality: 'excellent' | 'good' | 'fair' | 'poor' | 'invalid';
  measurement_date: string;
  measurement_method: string;
  operator_name?: string;
  equipment_used?: string;
  measured_values: any;
  quality_metrics?: any;
  confidence_score?: number;
  is_high_quality: boolean;
  use_for_training: boolean;
  use_for_validation: boolean;
  is_outlier: boolean;
  created_at: string;
  updated_at: string;
}

interface FilterState {
  search: string;
  measurementType: string;
  quality: string;
  blastRecordId: string;
  dateFrom: string;
  dateTo: string;
  useForTraining: string;
  isOutlier: string;
}

const MeasurementDataManager: React.FC = () => {
  const [measurements, setMeasurements] = useState<MeasurementData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMeasurement, setSelectedMeasurement] = useState<MeasurementData | null>(null);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [pageSize] = useState(20);

  const [filters, setFilters] = useState<FilterState>({
    search: '',
    measurementType: '',
    quality: '',
    blastRecordId: '',
    dateFrom: '',
    dateTo: '',
    useForTraining: '',
    isOutlier: '',
  });

  const fetchMeasurements = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      // Add filters
      if (filters.search) params.append('search', filters.search);
      if (filters.measurementType) params.append('measurement_type', filters.measurementType);
      if (filters.quality) params.append('quality', filters.quality);
      if (filters.blastRecordId) params.append('blast_record_id', filters.blastRecordId);
      if (filters.dateFrom) params.append('date_from', filters.dateFrom);
      if (filters.dateTo) params.append('date_to', filters.dateTo);
      if (filters.useForTraining) params.append('use_for_training', filters.useForTraining);
      if (filters.isOutlier) params.append('is_outlier', filters.isOutlier);

      const response = await api.get(`/measurement-data?${params.toString()}`);
      
      if (response.data.success) {
        setMeasurements(response.data.data.items || []);
        setTotalPages(response.data.data.total_pages || 1);
        setTotalCount(response.data.data.total_count || 0);
      } else {
        throw new Error(response.data.message || 'Failed to fetch measurements');
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch measurements');
      setMeasurements([]);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filters]);

  const handleFilterChange = (field: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setPage(1); // Reset to first page when filtering
  };

  const handleViewDetails = (measurement: MeasurementData) => {
    setSelectedMeasurement(measurement);
    setDetailsDialogOpen(true);
  };

  const handleToggleTraining = async (measurementId: number, useForTraining: boolean) => {
    try {
      const response = await api.patch(`/measurement-data/${measurementId}`, {
        use_for_training: !useForTraining,
      });

      if (response.data.success) {
        await fetchMeasurements();
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to update measurement');
    }
  };

  const handleMarkAsOutlier = async (measurementId: number, isOutlier: boolean) => {
    try {
      const response = await api.patch(`/measurement-data/${measurementId}`, {
        is_outlier: !isOutlier,
      });

      if (response.data.success) {
        await fetchMeasurements();
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to update measurement');
    }
  };

  const handleDeleteMeasurement = async (measurementId: number) => {
    if (!window.confirm('Are you sure you want to delete this measurement?')) {
      return;
    }

    try {
      const response = await api.delete(`/measurement-data/${measurementId}`);

      if (response.data.success) {
        await fetchMeasurements();
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to delete measurement');
    }
  };

  const getQualityIcon = (quality: string) => {
    switch (quality) {
      case 'excellent':
      case 'good':
        return <CheckCircle color="success" />;
      case 'fair':
        return <Warning color="warning" />;
      case 'poor':
      case 'invalid':
        return <Error color="error" />;
      default:
        return <Warning color="action" />;
    }
  };

  const getQualityColor = (quality: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (quality) {
      case 'excellent':
        return 'success';
      case 'good':
        return 'primary';
      case 'fair':
        return 'warning';
      case 'poor':
      case 'invalid':
        return 'error';
      default:
        return 'default';
    }
  };

  const getMeasurementTypeIcon = (type: string) => {
    switch (type) {
      case 'fragmentation':
        return <PhotoCamera />;
      case 'ppv':
      case 'vibration':
        return <GraphicEq />;
      default:
        return <GraphicEq />;
    }
  };

  const formatMeasurementValue = (measurement: MeasurementData) => {
    if (measurement.measurement_type === 'fragmentation') {
      return `P80: ${measurement.measured_values?.p80?.toFixed(1) || 'N/A'} mm`;
    } else if (measurement.measurement_type === 'ppv') {
      return `Peak: ${measurement.measured_values?.peak_ppv?.toFixed(2) || 'N/A'} mm/s`;
    }
    return 'N/A';
  };

  useEffect(() => {
    fetchMeasurements();
  }, [fetchMeasurements]);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Measurement Data Manager
        </Typography>
        
        <Button
          variant="outlined"
          onClick={fetchMeasurements}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={16} /> : <Refresh />}
        >
          Refresh
        </Button>
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 2 }}>
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FilterList />
              <Typography>Filters</Typography>
              {Object.values(filters).some(v => v !== '') && (
                <Chip label="Active" color="primary" size="small" />
              )}
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="Search"
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  InputProps={{
                    startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
                  }}
                />
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Measurement Type</InputLabel>
                  <Select
                    value={filters.measurementType}
                    onChange={(e) => handleFilterChange('measurementType', e.target.value)}
                    label="Measurement Type"
                  >
                    <MenuItem value="">All Types</MenuItem>
                    <MenuItem value="fragmentation">Fragmentation</MenuItem>
                    <MenuItem value="ppv">PPV</MenuItem>
                    <MenuItem value="vibration">Vibration</MenuItem>
                    <MenuItem value="airblast">Airblast</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Quality</InputLabel>
                  <Select
                    value={filters.quality}
                    onChange={(e) => handleFilterChange('quality', e.target.value)}
                    label="Quality"
                  >
                    <MenuItem value="">All Qualities</MenuItem>
                    <MenuItem value="excellent">Excellent</MenuItem>
                    <MenuItem value="good">Good</MenuItem>
                    <MenuItem value="fair">Fair</MenuItem>
                    <MenuItem value="poor">Poor</MenuItem>
                    <MenuItem value="invalid">Invalid</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="Blast Record ID"
                  type="number"
                  value={filters.blastRecordId}
                  onChange={(e) => handleFilterChange('blastRecordId', e.target.value)}
                />
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="Date From"
                  type="date"
                  value={filters.dateFrom}
                  onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="Date To"
                  type="date"
                  value={filters.dateTo}
                  onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Training Use</InputLabel>
                  <Select
                    value={filters.useForTraining}
                    onChange={(e) => handleFilterChange('useForTraining', e.target.value)}
                    label="Training Use"
                  >
                    <MenuItem value="">All</MenuItem>
                    <MenuItem value="true">Used for Training</MenuItem>
                    <MenuItem value="false">Not Used for Training</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Outlier Status</InputLabel>
                  <Select
                    value={filters.isOutlier}
                    onChange={(e) => handleFilterChange('isOutlier', e.target.value)}
                    label="Outlier Status"
                  >
                    <MenuItem value="">All</MenuItem>
                    <MenuItem value="false">Normal</MenuItem>
                    <MenuItem value="true">Outliers</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
            
            <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
              <Button
                variant="outlined"
                onClick={() => setFilters({
                  search: '',
                  measurementType: '',
                  quality: '',
                  blastRecordId: '',
                  dateFrom: '',
                  dateTo: '',
                  useForTraining: '',
                  isOutlier: '',
                })}
              >
                Clear Filters
              </Button>
            </Box>
          </AccordionDetails>
        </Accordion>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Results Summary */}
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Showing {measurements.length} of {totalCount} measurements
        </Typography>
        {loading && <CircularProgress size={16} />}
      </Box>

      {/* Measurements Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Type</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Blast Record</TableCell>
              <TableCell>Quality</TableCell>
              <TableCell>Value</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Training</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {measurements.map((measurement) => (
              <TableRow key={measurement.id}>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getMeasurementTypeIcon(measurement.measurement_type)}
                    <Typography variant="body2">
                      {measurement.measurement_type.toUpperCase()}
                    </Typography>
                  </Box>
                </TableCell>
                
                <TableCell>
                  <Typography variant="body2">
                    {measurement.measurement_name}
                  </Typography>
                  {measurement.operator_name && (
                    <Typography variant="caption" color="text.secondary">
                      by {measurement.operator_name}
                    </Typography>
                  )}
                </TableCell>
                
                <TableCell>{measurement.blast_record_id}</TableCell>
                
                <TableCell>
                  <Chip
                    icon={getQualityIcon(measurement.measurement_quality)}
                    label={measurement.measurement_quality.toUpperCase()}
                    color={getQualityColor(measurement.measurement_quality)}
                    size="small"
                  />
                </TableCell>
                
                <TableCell>
                  <Typography variant="body2">
                    {formatMeasurementValue(measurement)}
                  </Typography>
                </TableCell>
                
                <TableCell>
                  {measurement.confidence_score && (
                    <Typography variant="body2">
                      {(measurement.confidence_score * 100).toFixed(1)}%
                    </Typography>
                  )}
                </TableCell>
                
                <TableCell>
                  <Typography variant="body2">
                    {new Date(measurement.measurement_date).toLocaleDateString()}
                  </Typography>
                </TableCell>
                
                <TableCell>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    <Chip
                      label={measurement.use_for_training ? 'Training' : 'No Training'}
                      color={measurement.use_for_training ? 'success' : 'default'}
                      size="small"
                      onClick={() => handleToggleTraining(measurement.id, measurement.use_for_training)}
                      clickable
                    />
                    {measurement.is_outlier && (
                      <Chip
                        label="Outlier"
                        color="error"
                        size="small"
                        onClick={() => handleMarkAsOutlier(measurement.id, measurement.is_outlier)}
                        clickable
                      />
                    )}
                  </Box>
                </TableCell>
                
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    <Tooltip title="View Details">
                      <IconButton
                        size="small"
                        onClick={() => handleViewDetails(measurement)}
                      >
                        <Visibility />
                      </IconButton>
                    </Tooltip>
                    
                    <Tooltip title="Mark as Outlier">
                      <IconButton
                        size="small"
                        onClick={() => handleMarkAsOutlier(measurement.id, measurement.is_outlier)}
                        color={measurement.is_outlier ? 'error' : 'default'}
                      >
                        <Warning />
                      </IconButton>
                    </Tooltip>
                    
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteMeasurement(measurement.id)}
                        color="error"
                      >
                        <Delete />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, newPage) => setPage(newPage)}
            color="primary"
          />
        </Box>
      )}

      {/* Details Dialog */}
      <Dialog
        open={detailsDialogOpen}
        onClose={() => setDetailsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Measurement Details
          {selectedMeasurement && (
            <Typography variant="body2" color="text.secondary">
              ID: {selectedMeasurement.id} | Type: {selectedMeasurement.measurement_type.toUpperCase()}
            </Typography>
          )}
        </DialogTitle>
        
        <DialogContent>
          {selectedMeasurement && (
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <Typography variant="h6" gutterBottom>
                  Basic Information
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Typography variant="body2">
                    <strong>Name:</strong> {selectedMeasurement.measurement_name}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Blast Record:</strong> {selectedMeasurement.blast_record_id}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Method:</strong> {selectedMeasurement.measurement_method}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Operator:</strong> {selectedMeasurement.operator_name || 'N/A'}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Equipment:</strong> {selectedMeasurement.equipment_used || 'N/A'}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Date:</strong> {new Date(selectedMeasurement.measurement_date).toLocaleString()}
                  </Typography>
                </Box>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="h6" gutterBottom>
                  Quality & Status
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Box>
                    <Chip
                      icon={getQualityIcon(selectedMeasurement.measurement_quality)}
                      label={selectedMeasurement.measurement_quality.toUpperCase()}
                      color={getQualityColor(selectedMeasurement.measurement_quality)}
                    />
                  </Box>
                  {selectedMeasurement.confidence_score && (
                    <Typography variant="body2">
                      <strong>Confidence:</strong> {(selectedMeasurement.confidence_score * 100).toFixed(1)}%
                    </Typography>
                  )}
                  <Typography variant="body2">
                    <strong>High Quality:</strong> {selectedMeasurement.is_high_quality ? 'Yes' : 'No'}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Use for Training:</strong> {selectedMeasurement.use_for_training ? 'Yes' : 'No'}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Use for Validation:</strong> {selectedMeasurement.use_for_validation ? 'Yes' : 'No'}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Is Outlier:</strong> {selectedMeasurement.is_outlier ? 'Yes' : 'No'}
                  </Typography>
                </Box>
              </Grid>
              
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Measured Values
                </Typography>
                <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
                  <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(selectedMeasurement.measured_values, null, 2)}
                  </pre>
                </Paper>
              </Grid>
              
              {selectedMeasurement.quality_metrics && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Quality Metrics
                  </Typography>
                  <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
                    <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(selectedMeasurement.quality_metrics, null, 2)}
                    </pre>
                  </Paper>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setDetailsDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MeasurementDataManager;