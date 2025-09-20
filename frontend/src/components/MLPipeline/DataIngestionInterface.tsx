/**
 * Data Ingestion Interface
 * 
 * Component for ingesting fragmentation images and PPV data files.
 */

import React, { useState, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Alert,
  CircularProgress,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Paper,
  LinearProgress,
  Tabs,
  Tab,
} from '@mui/material';
import {
  CloudUpload,
  Delete,
  PhotoCamera,
  GraphicEq,
  CheckCircle,
  Error,
  Info,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';

import mlPipelineService from '../../services/mlPipelineService';

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
      id={`ingestion-tabpanel-${index}`}
      aria-labelledby={`ingestion-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
}

interface IngestionState {
  loading: boolean;
  progress: number;
  result: any | null;
  error: string | null;
}

const DataIngestionInterface: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [blastRecordId, setBlastRecordId] = useState<string>('');
  
  // Fragmentation images
  const [fragmentationImages, setFragmentationImages] = useState<File[]>([]);
  const [fragmentationState, setFragmentationState] = useState<IngestionState>({
    loading: false,
    progress: 0,
    result: null,
    error: null,
  });

  // PPV data files
  const [ppvFiles, setPpvFiles] = useState<File[]>([]);
  const [ppvState, setPpvState] = useState<IngestionState>({
    loading: false,
    progress: 0,
    result: null,
    error: null,
  });

  // Batch processing
  const [batchState, setBatchState] = useState<IngestionState>({
    loading: false,
    progress: 0,
    result: null,
    error: null,
  });

  // Metadata
  const [metadata, setMetadata] = useState({
    measurementName: '',
    operatorName: '',
    equipmentUsed: '',
    measurementDate: new Date().toISOString().slice(0, 16),
    notes: '',
  });

  const onDropFragmentation = useCallback((acceptedFiles: File[]) => {
    setFragmentationImages(prev => [...prev, ...acceptedFiles]);
  }, []);

  const onDropPPV = useCallback((acceptedFiles: File[]) => {
    setPpvFiles(prev => [...prev, ...acceptedFiles]);
  }, []);

  const {
    getRootProps: getFragmentationRootProps,
    getInputProps: getFragmentationInputProps,
    isDragActive: isFragmentationDragActive,
  } = useDropzone({
    onDrop: onDropFragmentation,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.bmp', '.tiff'],
    },
  });

  const {
    getRootProps: getPPVRootProps,
    getInputProps: getPPVInputProps,
    isDragActive: isPPVDragActive,
  } = useDropzone({
    onDrop: onDropPPV,
    accept: {
      'text/*': ['.txt', '.csv', '.dat'],
      'application/*': ['.json', '.xml'],
    },
  });

  const handleRemoveFragmentationImage = (index: number) => {
    setFragmentationImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleRemovePPVFile = (index: number) => {
    setPpvFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleIngestFragmentation = async () => {
    if (!blastRecordId || fragmentationImages.length === 0) {
      setFragmentationState(prev => ({ ...prev, error: 'Please select blast record and images' }));
      return;
    }

    setFragmentationState({
      loading: true,
      progress: 0,
      result: null,
      error: null,
    });

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setFragmentationState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90),
        }));
      }, 500);

      const response = await mlPipelineService.ingestFragmentationImages(
        parseInt(blastRecordId),
        fragmentationImages,
        metadata
      );

      clearInterval(progressInterval);

      if (response.success) {
        setFragmentationState({
          loading: false,
          progress: 100,
          result: response.data,
          error: null,
        });
        setFragmentationImages([]);
      } else {
        throw new Error(response.message || 'Ingestion failed');
      }
    } catch (error) {
      setFragmentationState({
        loading: false,
        progress: 0,
        result: null,
        error: error instanceof Error ? error.message : 'Ingestion failed',
      });
    }
  };

  const handleIngestPPV = async () => {
    if (!blastRecordId || ppvFiles.length === 0) {
      setPpvState(prev => ({ ...prev, error: 'Please select blast record and PPV files' }));
      return;
    }

    setPpvState({
      loading: true,
      progress: 0,
      result: null,
      error: null,
    });

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setPpvState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90),
        }));
      }, 500);

      const response = await mlPipelineService.ingestPPVData(
        parseInt(blastRecordId),
        ppvFiles,
        metadata
      );

      clearInterval(progressInterval);

      if (response.success) {
        setPpvState({
          loading: false,
          progress: 100,
          result: response.data,
          error: null,
        });
        setPpvFiles([]);
      } else {
        throw new Error(response.message || 'Ingestion failed');
      }
    } catch (error) {
      setPpvState({
        loading: false,
        progress: 0,
        result: null,
        error: error instanceof Error ? error.message : 'Ingestion failed',
      });
    }
  };

  const handleBatchIngest = async () => {
    if (!blastRecordId || (fragmentationImages.length === 0 && ppvFiles.length === 0)) {
      setBatchState(prev => ({ ...prev, error: 'Please select blast record and files' }));
      return;
    }

    setBatchState({
      loading: true,
      progress: 0,
      result: null,
      error: null,
    });

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setBatchState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 5, 90),
        }));
      }, 1000);

      const response = await mlPipelineService.submitBatchJob(
        parseInt(blastRecordId),
        fragmentationImages.length > 0 ? fragmentationImages : undefined,
        ppvFiles.length > 0 ? ppvFiles : undefined,
        metadata
      );

      clearInterval(progressInterval);

      if (response.success) {
        setBatchState({
          loading: false,
          progress: 100,
          result: response.data,
          error: null,
        });
        setFragmentationImages([]);
        setPpvFiles([]);
      } else {
        throw new Error(response.message || 'Batch job submission failed');
      }
    } catch (error) {
      setBatchState({
        loading: false,
        progress: 0,
        result: null,
        error: error instanceof Error ? error.message : 'Batch job submission failed',
      });
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Data Ingestion
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Upload post-blast measurement data including fragmentation images and PPV sensor data.
        This data will be used to train and improve the residual learning models.
      </Typography>

      <Grid container spacing={3}>
        {/* Blast Record Selection */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Blast Record Configuration
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    label="Blast Record ID"
                    type="number"
                    value={blastRecordId}
                    onChange={(e) => setBlastRecordId(e.target.value)}
                    required
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    label="Measurement Name"
                    value={metadata.measurementName}
                    onChange={(e) => setMetadata(prev => ({ ...prev, measurementName: e.target.value }))}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    label="Operator Name"
                    value={metadata.operatorName}
                    onChange={(e) => setMetadata(prev => ({ ...prev, operatorName: e.target.value }))}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    label="Equipment Used"
                    value={metadata.equipmentUsed}
                    onChange={(e) => setMetadata(prev => ({ ...prev, equipmentUsed: e.target.value }))}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Measurement Date"
                    type="datetime-local"
                    value={metadata.measurementDate}
                    onChange={(e) => setMetadata(prev => ({ ...prev, measurementDate: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Notes"
                    multiline
                    rows={2}
                    value={metadata.notes}
                    onChange={(e) => setMetadata(prev => ({ ...prev, notes: e.target.value }))}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Ingestion Tabs */}
        <Grid item xs={12}>
          <Card>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={activeTab} onChange={handleTabChange}>
                <Tab icon={<PhotoCamera />} label="Fragmentation Images" />
                <Tab icon={<GraphicEq />} label="PPV Data" />
                <Tab icon={<CloudUpload />} label="Batch Processing" />
              </Tabs>
            </Box>

            <CardContent>
              <TabPanel value={activeTab} index={0}>
                {/* Fragmentation Images */}
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Paper
                      {...getFragmentationRootProps()}
                      sx={{
                        p: 3,
                        border: '2px dashed',
                        borderColor: isFragmentationDragActive ? 'primary.main' : 'grey.300',
                        backgroundColor: isFragmentationDragActive ? 'action.hover' : 'background.paper',
                        cursor: 'pointer',
                        textAlign: 'center',
                      }}
                    >
                      <input {...getFragmentationInputProps()} />
                      <PhotoCamera sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                      <Typography variant="body1" gutterBottom>
                        {isFragmentationDragActive
                          ? 'Drop fragmentation images here...'
                          : 'Drag & drop fragmentation images, or click to select'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Supported: JPEG, PNG, BMP, TIFF
                      </Typography>
                    </Paper>

                    {fragmentationImages.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="body2" gutterBottom>
                          Selected Images ({fragmentationImages.length}):
                        </Typography>
                        <List dense>
                          {fragmentationImages.map((file, index) => (
                            <ListItem key={index}>
                              <ListItemIcon>
                                <PhotoCamera />
                              </ListItemIcon>
                              <ListItemText
                                primary={file.name}
                                secondary={formatFileSize(file.size)}
                              />
                              <ListItemSecondaryAction>
                                <IconButton
                                  edge="end"
                                  onClick={() => handleRemoveFragmentationImage(index)}
                                >
                                  <Delete />
                                </IconButton>
                              </ListItemSecondaryAction>
                            </ListItem>
                          ))}
                        </List>
                      </Box>
                    )}
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Button
                      fullWidth
                      variant="contained"
                      onClick={handleIngestFragmentation}
                      disabled={fragmentationState.loading || !blastRecordId || fragmentationImages.length === 0}
                      startIcon={fragmentationState.loading ? <CircularProgress size={20} /> : <CloudUpload />}
                      sx={{ mb: 2 }}
                    >
                      {fragmentationState.loading ? 'Processing...' : 'Ingest Fragmentation Images'}
                    </Button>

                    {fragmentationState.loading && (
                      <Box sx={{ mb: 2 }}>
                        <LinearProgress variant="determinate" value={fragmentationState.progress} />
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          Processing: {fragmentationState.progress}%
                        </Typography>
                      </Box>
                    )}

                    {fragmentationState.error && (
                      <Alert severity="error" sx={{ mb: 2 }}>
                        {fragmentationState.error}
                      </Alert>
                    )}

                    {fragmentationState.result && (
                      <Alert severity="success">
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          Ingestion Completed
                        </Typography>
                        <Typography variant="body2">
                          Processed: {fragmentationState.result.batch_summary?.successful_measurements || 0} images
                        </Typography>
                        <Typography variant="body2">
                          Failed: {fragmentationState.result.batch_summary?.failed_measurements || 0} images
                        </Typography>
                      </Alert>
                    )}
                  </Grid>
                </Grid>
              </TabPanel>

              <TabPanel value={activeTab} index={1}>
                {/* PPV Data */}
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Paper
                      {...getPPVRootProps()}
                      sx={{
                        p: 3,
                        border: '2px dashed',
                        borderColor: isPPVDragActive ? 'primary.main' : 'grey.300',
                        backgroundColor: isPPVDragActive ? 'action.hover' : 'background.paper',
                        cursor: 'pointer',
                        textAlign: 'center',
                      }}
                    >
                      <input {...getPPVInputProps()} />
                      <GraphicEq sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                      <Typography variant="body1" gutterBottom>
                        {isPPVDragActive
                          ? 'Drop PPV data files here...'
                          : 'Drag & drop PPV data files, or click to select'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Supported: TXT, CSV, DAT, JSON, XML
                      </Typography>
                    </Paper>

                    {ppvFiles.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="body2" gutterBottom>
                          Selected Files ({ppvFiles.length}):
                        </Typography>
                        <List dense>
                          {ppvFiles.map((file, index) => (
                            <ListItem key={index}>
                              <ListItemIcon>
                                <GraphicEq />
                              </ListItemIcon>
                              <ListItemText
                                primary={file.name}
                                secondary={formatFileSize(file.size)}
                              />
                              <ListItemSecondaryAction>
                                <IconButton
                                  edge="end"
                                  onClick={() => handleRemovePPVFile(index)}
                                >
                                  <Delete />
                                </IconButton>
                              </ListItemSecondaryAction>
                            </ListItem>
                          ))}
                        </List>
                      </Box>
                    )}
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Button
                      fullWidth
                      variant="contained"
                      onClick={handleIngestPPV}
                      disabled={ppvState.loading || !blastRecordId || ppvFiles.length === 0}
                      startIcon={ppvState.loading ? <CircularProgress size={20} /> : <CloudUpload />}
                      sx={{ mb: 2 }}
                    >
                      {ppvState.loading ? 'Processing...' : 'Ingest PPV Data'}
                    </Button>

                    {ppvState.loading && (
                      <Box sx={{ mb: 2 }}>
                        <LinearProgress variant="determinate" value={ppvState.progress} />
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          Processing: {ppvState.progress}%
                        </Typography>
                      </Box>
                    )}

                    {ppvState.error && (
                      <Alert severity="error" sx={{ mb: 2 }}>
                        {ppvState.error}
                      </Alert>
                    )}

                    {ppvState.result && (
                      <Alert severity="success">
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          Ingestion Completed
                        </Typography>
                        <Typography variant="body2">
                          Processed: {ppvState.result.batch_summary?.successful_measurements || 0} files
                        </Typography>
                        <Typography variant="body2">
                          Failed: {ppvState.result.batch_summary?.failed_measurements || 0} files
                        </Typography>
                      </Alert>
                    )}
                  </Grid>
                </Grid>
              </TabPanel>

              <TabPanel value={activeTab} index={2}>
                {/* Batch Processing */}
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <Alert severity="info" sx={{ mb: 2 }}>
                      Batch processing allows you to submit both fragmentation images and PPV data files
                      in a single job for asynchronous processing.
                    </Alert>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography variant="h6" gutterBottom>
                      Files Summary
                    </Typography>
                    
                    <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                      <Chip
                        icon={<PhotoCamera />}
                        label={`${fragmentationImages.length} Images`}
                        color={fragmentationImages.length > 0 ? 'primary' : 'default'}
                      />
                      <Chip
                        icon={<GraphicEq />}
                        label={`${ppvFiles.length} PPV Files`}
                        color={ppvFiles.length > 0 ? 'primary' : 'default'}
                      />
                    </Box>

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Use the other tabs to select files for batch processing.
                    </Typography>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Button
                      fullWidth
                      variant="contained"
                      onClick={handleBatchIngest}
                      disabled={
                        batchState.loading ||
                        !blastRecordId ||
                        (fragmentationImages.length === 0 && ppvFiles.length === 0)
                      }
                      startIcon={batchState.loading ? <CircularProgress size={20} /> : <CloudUpload />}
                      sx={{ mb: 2 }}
                    >
                      {batchState.loading ? 'Submitting...' : 'Submit Batch Job'}
                    </Button>

                    {batchState.loading && (
                      <Box sx={{ mb: 2 }}>
                        <LinearProgress variant="determinate" value={batchState.progress} />
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          Submitting: {batchState.progress}%
                        </Typography>
                      </Box>
                    )}

                    {batchState.error && (
                      <Alert severity="error" sx={{ mb: 2 }}>
                        {batchState.error}
                      </Alert>
                    )}

                    {batchState.result && (
                      <Alert severity="success">
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          Batch Job Submitted
                        </Typography>
                        <Typography variant="body2">
                          Job ID: {batchState.result.job_id}
                        </Typography>
                        <Typography variant="body2">
                          Total Files: {batchState.result.batch_info?.total_files || 0}
                        </Typography>
                      </Alert>
                    )}
                  </Grid>
                </Grid>
              </TabPanel>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DataIngestionInterface;