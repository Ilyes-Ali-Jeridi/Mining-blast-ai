/**
 * Fragmentation Analysis Interface
 * 
 * Component for analyzing fragmentation from muckpile images using SAM-based segmentation.
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
  Divider,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  CloudUpload,
  Analytics,
  CheckCircle,
  Warning,
  Error,
  Info,
  PhotoCamera,
  Straighten,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';

import mlPipelineService, { FragmentationAnalysisResult } from '../../services/mlPipelineService';
import FragmentationResultsDisplay from './FragmentationResultsDisplay';
import ScaleMarkerSelector from './ScaleMarkerSelector';

interface AnalysisState {
  loading: boolean;
  result: FragmentationAnalysisResult | null;
  error: string | null;
  recommendations: string[];
}

const FragmentationAnalysisInterface: React.FC = () => {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [scaleCoords, setScaleCoords] = useState<{
    x1?: number;
    y1?: number;
    x2?: number;
    y2?: number;
  }>({});
  const [knownScale, setKnownScale] = useState<string>('');
  const [analysisState, setAnalysisState] = useState<AnalysisState>({
    loading: false,
    result: null,
    error: null,
    recommendations: [],
  });

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setSelectedImage(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
      
      // Reset previous results
      setAnalysisState({
        loading: false,
        result: null,
        error: null,
        recommendations: [],
      });
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.bmp', '.tiff'],
    },
    multiple: false,
  });

  const handleAnalyze = async () => {
    if (!selectedImage) return;

    setAnalysisState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const request = {
        image: selectedImage,
        scaleX1: scaleCoords.x1,
        scaleY1: scaleCoords.y1,
        scaleX2: scaleCoords.x2,
        scaleY2: scaleCoords.y2,
        knownScaleMmPerPixel: knownScale ? parseFloat(knownScale) : undefined,
      };

      const response = await mlPipelineService.analyzeFragmentation(request);

      if (response.success) {
        setAnalysisState({
          loading: false,
          result: response.data.fragmentation_analysis,
          error: null,
          recommendations: response.data.recommendations || [],
        });
      } else {
        throw new Error(response.message || 'Analysis failed');
      }
    } catch (error) {
      setAnalysisState({
        loading: false,
        result: null,
        error: error instanceof Error ? error.message : 'Analysis failed',
        recommendations: [],
      });
    }
  };

  const handleScaleCoordsChange = (coords: { x1?: number; y1?: number; x2?: number; y2?: number }) => {
    setScaleCoords(coords);
  };

  const getQualityColor = (quality: number) => {
    if (quality >= 0.8) return 'success';
    if (quality >= 0.6) return 'warning';
    return 'error';
  };

  const getQualityIcon = (quality: number) => {
    if (quality >= 0.8) return <CheckCircle />;
    if (quality >= 0.6) return <Warning />;
    return <Error />;
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Fragmentation Analysis
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Upload muckpile images for automated fragmentation analysis using SAM-based segmentation.
        The system will detect fragments, calculate size distributions, and provide quality assessments.
      </Typography>

      <Grid container spacing={3}>
        {/* Image Upload Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <PhotoCamera sx={{ mr: 1, verticalAlign: 'middle' }} />
                Image Upload
              </Typography>

              {/* Dropzone */}
              <Paper
                {...getRootProps()}
                sx={{
                  p: 3,
                  border: '2px dashed',
                  borderColor: isDragActive ? 'primary.main' : 'grey.300',
                  backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
                  cursor: 'pointer',
                  textAlign: 'center',
                  mb: 2,
                }}
              >
                <input {...getInputProps()} />
                <CloudUpload sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                <Typography variant="body1" gutterBottom>
                  {isDragActive
                    ? 'Drop the image here...'
                    : 'Drag & drop a muckpile image here, or click to select'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Supported formats: JPEG, PNG, BMP, TIFF
                </Typography>
              </Paper>

              {selectedImage && (
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Selected: {selectedImage.name} ({(selectedImage.size / 1024 / 1024).toFixed(2)} MB)
                  </Typography>
                  
                  {imagePreview && (
                    <Box sx={{ mt: 2 }}>
                      <img
                        src={imagePreview}
                        alt="Preview"
                        style={{
                          width: '100%',
                          maxHeight: '300px',
                          objectFit: 'contain',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                        }}
                      />
                    </Box>
                  )}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Scale Configuration Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Straighten sx={{ mr: 1, verticalAlign: 'middle' }} />
                Scale Configuration
              </Typography>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure scale detection for accurate size measurements.
              </Typography>

              <TextField
                fullWidth
                label="Known Scale (mm per pixel)"
                value={knownScale}
                onChange={(e) => setKnownScale(e.target.value)}
                type="number"
                inputProps={{ step: 0.001, min: 0 }}
                helperText="If known, enter the scale factor directly"
                sx={{ mb: 2 }}
              />

              <Divider sx={{ my: 2 }} />

              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Or select scale marker coordinates:
              </Typography>

              {imagePreview && (
                <ScaleMarkerSelector
                  imageUrl={imagePreview}
                  onCoordsChange={handleScaleCoordsChange}
                />
              )}

              {!imagePreview && (
                <Alert severity="info">
                  Upload an image to enable scale marker selection
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Analysis Controls */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button
                  variant="contained"
                  onClick={handleAnalyze}
                  disabled={!selectedImage || analysisState.loading}
                  startIcon={analysisState.loading ? <CircularProgress size={20} /> : <Analytics />}
                >
                  {analysisState.loading ? 'Analyzing...' : 'Analyze Fragmentation'}
                </Button>

                {selectedImage && (
                  <Typography variant="body2" color="text.secondary">
                    Ready to analyze {selectedImage.name}
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Error Display */}
        {analysisState.error && (
          <Grid item xs={12}>
            <Alert severity="error">
              <Typography variant="body2">
                Analysis failed: {analysisState.error}
              </Typography>
            </Alert>
          </Grid>
        )}

        {/* Results Display */}
        {analysisState.result && (
          <Grid item xs={12}>
            <FragmentationResultsDisplay
              result={analysisState.result}
              recommendations={analysisState.recommendations}
            />
          </Grid>
        )}

        {/* Quality Summary */}
        {analysisState.result && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quality Assessment
                </Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getQualityIcon(analysisState.result.measurement_quality)}
                    <Typography variant="body2">
                      Overall Quality: {(analysisState.result.measurement_quality * 100).toFixed(1)}%
                    </Typography>
                    <Chip
                      size="small"
                      label={analysisState.result.is_valid ? 'Valid' : 'Invalid'}
                      color={analysisState.result.is_valid ? 'success' : 'error'}
                    />
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getQualityIcon(analysisState.result.scale_detection_quality)}
                    <Typography variant="body2">
                      Scale Detection: {(analysisState.result.scale_detection_quality * 100).toFixed(1)}%
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getQualityIcon(analysisState.result.segmentation_quality)}
                    <Typography variant="body2">
                      Segmentation: {(analysisState.result.segmentation_quality * 100).toFixed(1)}%
                    </Typography>
                  </Box>
                </Box>

                {analysisState.result.quality_flags.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Quality Issues:
                    </Typography>
                    <List dense>
                      {analysisState.result.quality_flags.map((flag, index) => (
                        <ListItem key={index} sx={{ py: 0 }}>
                          <ListItemIcon sx={{ minWidth: 32 }}>
                            <Warning color="warning" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText
                            primary={flag}
                            primaryTypographyProps={{ variant: 'body2' }}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Recommendations */}
        {analysisState.recommendations.length > 0 && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Recommendations
                </Typography>

                <List dense>
                  {analysisState.recommendations.map((recommendation, index) => (
                    <ListItem key={index} sx={{ py: 0 }}>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        <Info color="info" fontSize="small" />
                      </ListItemIcon>
                      <ListItemText
                        primary={recommendation}
                        primaryTypographyProps={{ variant: 'body2' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default FragmentationAnalysisInterface;