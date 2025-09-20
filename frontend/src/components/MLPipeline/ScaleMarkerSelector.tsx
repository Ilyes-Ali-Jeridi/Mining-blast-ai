/**
 * Scale Marker Selector
 * 
 * Component for selecting scale marker coordinates on an image.
 */

import React, { useState, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
} from '@mui/material';
import { Clear, CropFree } from '@mui/icons-material';

interface Props {
  imageUrl: string;
  onCoordsChange: (coords: { x1?: number; y1?: number; x2?: number; y2?: number }) => void;
}

interface Point {
  x: number;
  y: number;
}

const ScaleMarkerSelector: React.FC<Props> = ({ imageUrl, onCoordsChange }) => {
  const [startPoint, setStartPoint] = useState<Point | null>(null);
  const [endPoint, setEndPoint] = useState<Point | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const getRelativeCoordinates = useCallback((event: React.MouseEvent) => {
    if (!imageRef.current || !containerRef.current) return null;

    const rect = imageRef.current.getBoundingClientRect();
    const containerRect = containerRef.current.getBoundingClientRect();
    
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // Convert to image coordinates
    const imageX = (x / rect.width) * imageRef.current.naturalWidth;
    const imageY = (y / rect.height) * imageRef.current.naturalHeight;
    
    return { x: imageX, y: imageY };
  }, []);

  const handleMouseDown = (event: React.MouseEvent) => {
    if (!isSelecting) return;
    
    const coords = getRelativeCoordinates(event);
    if (coords) {
      setStartPoint(coords);
      setEndPoint(null);
    }
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    if (!isSelecting || !startPoint) return;
    
    const coords = getRelativeCoordinates(event);
    if (coords) {
      setEndPoint(coords);
    }
  };

  const handleMouseUp = (event: React.MouseEvent) => {
    if (!isSelecting || !startPoint) return;
    
    const coords = getRelativeCoordinates(event);
    if (coords) {
      setEndPoint(coords);
      setIsSelecting(false);
      
      // Update parent component
      onCoordsChange({
        x1: Math.min(startPoint.x, coords.x),
        y1: Math.min(startPoint.y, coords.y),
        x2: Math.max(startPoint.x, coords.x),
        y2: Math.max(startPoint.y, coords.y),
      });
    }
  };

  const handleStartSelection = () => {
    setIsSelecting(true);
    setStartPoint(null);
    setEndPoint(null);
  };

  const handleClearSelection = () => {
    setIsSelecting(false);
    setStartPoint(null);
    setEndPoint(null);
    onCoordsChange({});
  };

  const getSelectionStyle = () => {
    if (!startPoint || !endPoint || !imageRef.current) return {};

    const rect = imageRef.current.getBoundingClientRect();
    const scaleX = rect.width / imageRef.current.naturalWidth;
    const scaleY = rect.height / imageRef.current.naturalHeight;

    const left = Math.min(startPoint.x, endPoint.x) * scaleX;
    const top = Math.min(startPoint.y, endPoint.y) * scaleY;
    const width = Math.abs(endPoint.x - startPoint.x) * scaleX;
    const height = Math.abs(endPoint.y - startPoint.y) * scaleY;

    return {
      position: 'absolute' as const,
      left: `${left}px`,
      top: `${top}px`,
      width: `${width}px`,
      height: `${height}px`,
      border: '2px solid #1976d2',
      backgroundColor: 'rgba(25, 118, 210, 0.1)',
      pointerEvents: 'none' as const,
    };
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <Button
          size="small"
          variant={isSelecting ? 'contained' : 'outlined'}
          onClick={handleStartSelection}
          startIcon={<CropFree />}
        >
          Select Scale Marker
        </Button>
        
        <Button
          size="small"
          variant="outlined"
          onClick={handleClearSelection}
          startIcon={<Clear />}
          disabled={!startPoint && !endPoint}
        >
          Clear
        </Button>
      </Box>

      {isSelecting && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Click and drag to select the scale marker area on the image.
        </Alert>
      )}

      <Box
        ref={containerRef}
        sx={{
          position: 'relative',
          display: 'inline-block',
          cursor: isSelecting ? 'crosshair' : 'default',
        }}
      >
        <img
          ref={imageRef}
          src={imageUrl}
          alt="Scale marker selection"
          style={{
            maxWidth: '100%',
            maxHeight: '400px',
            objectFit: 'contain',
            border: '1px solid #ddd',
            borderRadius: '4px',
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          draggable={false}
        />
        
        {startPoint && endPoint && (
          <div style={getSelectionStyle()} />
        )}
      </Box>

      {startPoint && endPoint && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Selected area: {Math.abs(endPoint.x - startPoint.x).toFixed(0)} × {Math.abs(endPoint.y - startPoint.y).toFixed(0)} pixels
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default ScaleMarkerSelector;