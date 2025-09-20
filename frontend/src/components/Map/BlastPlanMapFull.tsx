import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polygon,
  Polyline,
  useMapEvents,
  Circle,
  Rectangle,
} from 'react-leaflet';
import L from 'leaflet';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Stack,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  CenterFocusStrong as CenterIcon,
  Straighten as MeasureIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import { BlastPlan, DrillHole, BenchGeometry, Receptor, Polygon as PolygonType } from '../../types';

// Fix Leaflet default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface BlastPlanMapProps {
  blastPlan?: BlastPlan;
  benchGeometry?: BenchGeometry;
  receptors?: Receptor[];
  excludedZones?: PolygonType[];
  onHoleSelect?: (hole: DrillHole) => void;
  onHoleEdit?: (hole: DrillHole) => void;
  onMeasurement?: (distance: number, area: number) => void;
  editable?: boolean;
  showControls?: boolean;
}

// Color schemes for hole visualization
const COLOR_SCHEMES = {
  charge: {
    name: 'Charge (kg)',
    getColor: (hole: DrillHole, minVal: number, maxVal: number) => {
      const ratio = maxVal > minVal ? (hole.charge_kg - minVal) / (maxVal - minVal) : 0;
      const hue = (1 - ratio) * 120; // Green to red
      return `hsl(${hue}, 70%, 50%)`;
    },
  },
  delay: {
    name: 'Delay (ms)',
    getColor: (hole: DrillHole, minVal: number, maxVal: number) => {
      const ratio = maxVal > minVal ? (hole.delay_ms - minVal) / (maxVal - minVal) : 0;
      const hue = ratio * 270; // Red to blue
      return `hsl(${hue}, 70%, 50%)`;
    },
  },
  explosive: {
    name: 'Explosive Type',
    getColor: (hole: DrillHole, minVal: number, maxVal: number) => {
      const colors: Record<string, string> = {
        'ANFO': '#ff6b6b',
        'Emulsion': '#4ecdc4',
        'Slurry': '#45b7d1',
      };
      return colors[hole.explosive_type] || '#95a5a6';
    },
  },
};

export const BlastPlanMap: React.FC<BlastPlanMapProps> = ({
  blastPlan,
  benchGeometry,
  receptors = [],
  excludedZones = [],
  onHoleSelect,
  onHoleEdit,
  onMeasurement,
  editable = false,
  showControls = true,
}) => {
  const mapRef = useRef<L.Map | null>(null);
  const [selectedHole, setSelectedHole] = useState<DrillHole | null>(null);
  const [colorBy, setColorBy] = useState('charge');
  const [showReceptors, setShowReceptors] = useState(true);

  // Calculate map bounds and center
  const { center, bounds } = useMemo(() => {
    const holes = blastPlan?.holes || [];
    if (holes.length === 0) {
      return { center: [0, 0] as [number, number], bounds: null };
    }

    const lats = holes.map(h => h.coordinates.y);
    const lngs = holes.map(h => h.coordinates.x);
    
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);

    const centerLat = (minLat + maxLat) / 2;
    const centerLng = (minLng + maxLng) / 2;

    return {
      center: [centerLat, centerLng] as [number, number],
      bounds: [[minLat, minLng], [maxLat, maxLng]] as [[number, number], [number, number]],
    };
  }, [blastPlan?.holes]);

  // Calculate color values for holes
  const holeColors = useMemo(() => {
    const holes = blastPlan?.holes || [];
    if (holes.length === 0) {
      return new Map();
    }

    const scheme = COLOR_SCHEMES[colorBy as keyof typeof COLOR_SCHEMES];
    const colors = new Map<string, string>();
    
    if (colorBy === 'explosive') {
      holes.forEach(hole => {
        colors.set(hole.hole_id, scheme.getColor(hole, 0, 0));
      });
      return colors;
    }

    // Calculate min/max for numeric schemes
    let values: number[] = [];
    switch (colorBy) {
      case 'charge':
        values = holes.map(h => h.charge_kg);
        break;
      case 'delay':
        values = holes.map(h => h.delay_ms);
        break;
    }

    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);

    holes.forEach(hole => {
      colors.set(hole.hole_id, scheme.getColor(hole, minVal, maxVal));
    });

    return colors;
  }, [blastPlan?.holes, colorBy]);

  const handleHoleClick = useCallback((hole: DrillHole) => {
    setSelectedHole(hole);
    onHoleSelect?.(hole);
  }, [onHoleSelect]);

  return (
    <Box sx={{ position: 'relative', height: '100%', width: '100%' }}>
      <MapContainer
        center={center}
        zoom={15}
        style={{ height: '100%', width: '100%' }}
        bounds={bounds || undefined}
        ref={mapRef}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Drill holes */}
        {blastPlan?.holes.map((hole) => (
          <Circle
            key={hole.hole_id}
            center={[hole.coordinates.y, hole.coordinates.x]}
            radius={2}
            pathOptions={{
              color: holeColors.get(hole.hole_id) || '#3388ff',
              fillColor: holeColors.get(hole.hole_id) || '#3388ff',
              fillOpacity: 0.7,
              weight: 2,
            }}
            eventHandlers={{
              click: () => handleHoleClick(hole),
            }}
          >
            <Popup>
              <Box sx={{ minWidth: 200 }}>
                <Typography variant="h6" gutterBottom>
                  Hole {hole.hole_id}
                </Typography>
                <Stack spacing={1}>
                  <Typography variant="body2">
                    <strong>Coordinates:</strong> ({hole.coordinates.x.toFixed(2)}, {hole.coordinates.y.toFixed(2)})
                  </Typography>
                  <Typography variant="body2">
                    <strong>Depth:</strong> {hole.depth}m
                  </Typography>
                  <Typography variant="body2">
                    <strong>Charge:</strong> {hole.charge_kg}kg
                  </Typography>
                  <Typography variant="body2">
                    <strong>Delay:</strong> {hole.delay_ms}ms
                  </Typography>
                  <Typography variant="body2">
                    <strong>Explosive:</strong> {hole.explosive_type}
                  </Typography>
                </Stack>
              </Box>
            </Popup>
          </Circle>
        ))}

        {/* Sensitive receptors */}
        {showReceptors && receptors.map((receptor) => (
          <Marker
            key={receptor.id}
            position={[receptor.coordinates.y, receptor.coordinates.x]}
          >
            <Popup>
              <Box>
                <Typography variant="h6">{receptor.name}</Typography>
                <Typography variant="body2">
                  PPV Limit: {receptor.ppv_limit} mm/s
                </Typography>
              </Box>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Simple controls */}
      {showControls && (
        <Paper
          sx={{
            position: 'absolute',
            top: 10,
            right: 10,
            zIndex: 1000,
            p: 2,
            minWidth: 200,
          }}
        >
          <Typography variant="h6" gutterBottom>
            Map Controls
          </Typography>
          
          <FormControl size="small" fullWidth sx={{ mb: 2 }}>
            <InputLabel>Color By</InputLabel>
            <Select
              value={colorBy}
              label="Color By"
              onChange={(e) => setColorBy(e.target.value)}
            >
              {Object.entries(COLOR_SCHEMES).map(([key, scheme]) => (
                <MenuItem key={key} value={key}>
                  {scheme.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            variant="text"
            startIcon={showReceptors ? <VisibilityIcon /> : <VisibilityOffIcon />}
            onClick={() => setShowReceptors(!showReceptors)}
            size="small"
            fullWidth
          >
            Receptors
          </Button>
        </Paper>
      )}

      {/* Color legend */}
      {blastPlan?.holes && blastPlan.holes.length > 0 && colorBy === 'explosive' && (
        <Paper
          sx={{
            position: 'absolute',
            bottom: 10,
            right: 10,
            zIndex: 1000,
            p: 2,
            minWidth: 150,
          }}
        >
          <Typography variant="subtitle2" gutterBottom>
            Explosive Types
          </Typography>
          <Stack spacing={0.5}>
            <Chip label="ANFO" size="small" sx={{ bgcolor: '#ff6b6b', color: 'white' }} />
            <Chip label="Emulsion" size="small" sx={{ bgcolor: '#4ecdc4', color: 'white' }} />
            <Chip label="Slurry" size="small" sx={{ bgcolor: '#45b7d1', color: 'white' }} />
          </Stack>
        </Paper>
      )}
    </Box>
  );
};