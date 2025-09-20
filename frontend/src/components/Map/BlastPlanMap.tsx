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

interface MapControlsProps {
  map: L.Map | null;
  onMeasureToggle: () => void;
  isMeasuring: boolean;
  colorBy: string;
  onColorByChange: (value: string) => void;
  showReceptors: boolean;
  onShowReceptorsChange: (show: boolean) => void;
  showExcludedZones: boolean;
  onShowExcludedZonesChange: (show: boolean) => void;
}

interface HoleEditDialogProps {
  hole: DrillHole | null;
  open: boolean;
  onClose: () => void;
  onSave: (hole: DrillHole) => void;
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
  depth: {
    name: 'Depth (m)',
    getColor: (hole: DrillHole, minVal: number, maxVal: number) => {
      const ratio = maxVal > minVal ? (hole.depth - minVal) / (maxVal - minVal) : 0;
      const hue = ratio * 240; // Red to blue
      return `hsl(${hue}, 70%, 50%)`;
    },
  },
  explosive: {
    name: 'Explosive Type',
    getColor: (hole: DrillHole) => {
      const colors: Record<string, string> = {
        'ANFO': '#ff6b6b',
        'Emulsion': '#4ecdc4',
        'Slurry': '#45b7d1',
      };
      return colors[hole.explosive_type] || '#95a5a6';
    },
  },
};

// Custom hook for map measurement
const useMeasurement = () => {
  const [isMeasuring, setIsMeasuring] = useState(false);
  const [measurementPath, setMeasurementPath] = useState<L.LatLng[]>([]);
  const [totalDistance, setTotalDistance] = useState(0);

  const startMeasurement = useCallback(() => {
    setIsMeasuring(true);
    setMeasurementPath([]);
    setTotalDistance(0);
  }, []);

  const stopMeasurement = useCallback(() => {
    setIsMeasuring(false);
    setMeasurementPath([]);
    setTotalDistance(0);
  }, []);

  const addMeasurementPoint = useCallback((latlng: L.LatLng) => {
    setMeasurementPath(prev => {
      const newPath = [...prev, latlng];
      if (newPath.length > 1) {
        let distance = 0;
        for (let i = 1; i < newPath.length; i++) {
          distance += newPath[i - 1].distanceTo(newPath[i]);
        }
        setTotalDistance(distance);
      }
      return newPath;
    });
  }, []);

  return {
    isMeasuring,
    measurementPath,
    totalDistance,
    startMeasurement,
    stopMeasurement,
    addMeasurementPoint,
  };
};

// Map event handler component
const MapEventHandler: React.FC<{
  isMeasuring: boolean;
  onMeasurementPoint: (latlng: L.LatLng) => void;
}> = ({ isMeasuring, onMeasurementPoint }) => {
  useMapEvents({
    click: (e) => {
      if (isMeasuring) {
        onMeasurementPoint(e.latlng);
      }
    },
  });

  return null;
};

// Map controls component
const MapControls: React.FC<MapControlsProps> = ({
  map,
  onMeasureToggle,
  isMeasuring,
  colorBy,
  onColorByChange,
  showReceptors,
  onShowReceptorsChange,
  showExcludedZones,
  onShowExcludedZonesChange,
}) => {
  const handleZoomIn = () => map?.zoomIn();
  const handleZoomOut = () => map?.zoomOut();
  const handleCenter = () => {
    if (map) {
      map.setView([0, 0], 2);
    }
  };

  return (
    <Paper
      sx={{
        position: 'absolute',
        top: 10,
        right: 10,
        zIndex: 1000,
        p: 2,
        minWidth: 250,
      }}
    >
      <Typography variant="h6" gutterBottom>
        Map Controls
      </Typography>
      
      <Stack spacing={2}>
        {/* Zoom Controls */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Navigation
          </Typography>
          <Stack direction="row" spacing={1}>
            <Tooltip title="Zoom In">
              <IconButton onClick={handleZoomIn} size="small">
                <ZoomInIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Zoom Out">
              <IconButton onClick={handleZoomOut} size="small">
                <ZoomOutIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Center Map">
              <IconButton onClick={handleCenter} size="small">
                <CenterIcon />
              </IconButton>
            </Tooltip>
          </Stack>
        </Box>

        {/* Measurement Tool */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Tools
          </Typography>
          <Button
            variant={isMeasuring ? "contained" : "outlined"}
            startIcon={<MeasureIcon />}
            onClick={onMeasureToggle}
            size="small"
            fullWidth
          >
            {isMeasuring ? 'Stop Measuring' : 'Measure Distance'}
          </Button>
        </Box>

        {/* Color Scheme */}
        <FormControl size="small" fullWidth>
          <InputLabel>Color By</InputLabel>
          <Select
            value={colorBy}
            label="Color By"
            onChange={(e) => onColorByChange(e.target.value)}
          >
            {Object.entries(COLOR_SCHEMES).map(([key, scheme]) => (
              <MenuItem key={key} value={key}>
                {scheme.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Layer Toggles */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Layers
          </Typography>
          <Stack spacing={1}>
            <Button
              variant="text"
              startIcon={showReceptors ? <VisibilityIcon /> : <VisibilityOffIcon />}
              onClick={() => onShowReceptorsChange(!showReceptors)}
              size="small"
              sx={{ justifyContent: 'flex-start' }}
            >
              Receptors
            </Button>
            <Button
              variant="text"
              startIcon={showExcludedZones ? <VisibilityIcon /> : <VisibilityOffIcon />}
              onClick={() => onShowExcludedZonesChange(!showExcludedZones)}
              size="small"
              sx={{ justifyContent: 'flex-start' }}
            >
              Excluded Zones
            </Button>
          </Stack>
        </Box>
      </Stack>
    </Paper>
  );
};

// Hole edit dialog component
const HoleEditDialog: React.FC<HoleEditDialogProps> = ({ hole, open, onClose, onSave }) => {
  const [editedHole, setEditedHole] = useState<DrillHole | null>(null);

  useEffect(() => {
    setEditedHole(hole);
  }, [hole]);

  const handleSave = () => {
    if (editedHole) {
      onSave(editedHole);
      onClose();
    }
  };

  if (!editedHole) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit Hole {editedHole.hole_id}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            label="Charge (kg)"
            type="number"
            value={editedHole.charge_kg}
            onChange={(e) => setEditedHole({
              ...editedHole,
              charge_kg: parseFloat(e.target.value) || 0
            })}
            fullWidth
          />
          <TextField
            label="Depth (m)"
            type="number"
            value={editedHole.depth}
            onChange={(e) => setEditedHole({
              ...editedHole,
              depth: parseFloat(e.target.value) || 0
            })}
            fullWidth
          />
          <TextField
            label="Diameter (mm)"
            type="number"
            value={editedHole.diameter}
            onChange={(e) => setEditedHole({
              ...editedHole,
              diameter: parseFloat(e.target.value) || 0
            })}
            fullWidth
          />
          <TextField
            label="Stemming (m)"
            type="number"
            value={editedHole.stemming_m}
            onChange={(e) => setEditedHole({
              ...editedHole,
              stemming_m: parseFloat(e.target.value) || 0
            })}
            fullWidth
          />
          <TextField
            label="Delay (ms)"
            type="number"
            value={editedHole.delay_ms}
            onChange={(e) => setEditedHole({
              ...editedHole,
              delay_ms: parseInt(e.target.value) || 0
            })}
            fullWidth
          />
          <FormControl fullWidth>
            <InputLabel>Explosive Type</InputLabel>
            <Select
              value={editedHole.explosive_type}
              label="Explosive Type"
              onChange={(e) => setEditedHole({
                ...editedHole,
                explosive_type: e.target.value
              })}
            >
              <MenuItem value="ANFO">ANFO</MenuItem>
              <MenuItem value="Emulsion">Emulsion</MenuItem>
              <MenuItem value="Slurry">Slurry</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained">Save</Button>
      </DialogActions>
    </Dialog>
  );
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
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [colorBy, setColorBy] = useState('charge');
  const [showReceptors, setShowReceptors] = useState(true);
  const [showExcludedZones, setShowExcludedZones] = useState(true);

  const {
    isMeasuring,
    measurementPath,
    totalDistance,
    startMeasurement,
    stopMeasurement,
    addMeasurementPoint,
  } = useMeasurement();

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
  const { holeColors, colorRange } = useMemo(() => {
    const holes = blastPlan?.holes || [];
    if (holes.length === 0) {
      return { holeColors: new Map(), colorRange: { min: 0, max: 0 } };
    }

    const scheme = COLOR_SCHEMES[colorBy as keyof typeof COLOR_SCHEMES];
    const colors = new Map<string, string>();
    
    if (colorBy === 'explosive') {
      holes.forEach(hole => {
        colors.set(hole.hole_id, (scheme.getColor as any)(hole));
      });
      return { holeColors: colors, colorRange: { min: 0, max: 0 } };
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
      case 'depth':
        values = holes.map(h => h.depth);
        break;
    }

    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);

    holes.forEach(hole => {
      colors.set(hole.hole_id, scheme.getColor(hole, minVal, maxVal));
    });

    return { 
      holeColors: colors, 
      colorRange: { min: minVal, max: maxVal } 
    };
  }, [blastPlan?.holes, colorBy]);

  const handleHoleClick = useCallback((hole: DrillHole) => {
    setSelectedHole(hole);
    onHoleSelect?.(hole);
  }, [onHoleSelect]);

  const handleHoleEdit = useCallback((hole: DrillHole) => {
    setSelectedHole(hole);
    setEditDialogOpen(true);
  }, []);

  const handleHoleSave = useCallback((hole: DrillHole) => {
    onHoleEdit?.(hole);
  }, [onHoleEdit]);

  const handleMeasureToggle = useCallback(() => {
    if (isMeasuring) {
      stopMeasurement();
    } else {
      startMeasurement();
    }
  }, [isMeasuring, startMeasurement, stopMeasurement]);

  useEffect(() => {
    if (onMeasurement && totalDistance > 0) {
      onMeasurement(totalDistance, 0); // Area calculation would need polygon measurement
    }
  }, [totalDistance, onMeasurement]);

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

        {/* Map event handler */}
        <MapEventHandler
          isMeasuring={isMeasuring}
          onMeasurementPoint={addMeasurementPoint}
        />

        {/* Drill holes */}
        {blastPlan?.holes.map((hole) => (
          <Circle
            key={hole.hole_id}
            center={[hole.coordinates.y, hole.coordinates.x]}
            radius={2} // 2 meter radius for visibility
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
                  {editable && (
                    <Button
                      size="small"
                      startIcon={<EditIcon />}
                      onClick={() => handleHoleEdit(hole)}
                    >
                      Edit Hole
                    </Button>
                  )}
                </Stack>
              </Box>
            </Popup>
          </Circle>
        ))}

        {/* Bench geometry */}
        {benchGeometry && (
          <Rectangle
            bounds={[
              [0, 0], // This would need proper coordinate conversion
              [benchGeometry.bench_length, benchGeometry.bench_width]
            ]}
            pathOptions={{
              color: '#666',
              fillColor: 'transparent',
              weight: 2,
              dashArray: '5, 5',
            }}
          />
        )}

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

        {/* Excluded zones */}
        {showExcludedZones && excludedZones.map((zone) => (
          <Polygon
            key={zone.id}
            positions={zone.coordinates.map(coord => [coord.y, coord.x])}
            pathOptions={{
              color: '#ff0000',
              fillColor: '#ff0000',
              fillOpacity: 0.2,
              weight: 2,
            }}
          >
            <Popup>
              <Typography variant="h6">{zone.name}</Typography>
              <Typography variant="body2">Excluded Zone</Typography>
            </Popup>
          </Polygon>
        ))}

        {/* Measurement path */}
        {measurementPath.length > 1 && (
          <Polyline
            positions={measurementPath}
            pathOptions={{
              color: '#ff0000',
              weight: 3,
              dashArray: '10, 5',
            }}
          />
        )}
      </MapContainer>

      {/* Map controls */}
      {showControls && (
        <MapControls
          map={mapRef.current}
          onMeasureToggle={handleMeasureToggle}
          isMeasuring={isMeasuring}
          colorBy={colorBy}
          onColorByChange={setColorBy}
          showReceptors={showReceptors}
          onShowReceptorsChange={setShowReceptors}
          showExcludedZones={showExcludedZones}
          onShowExcludedZonesChange={setShowExcludedZones}
        />
      )}

      {/* Measurement display */}
      {isMeasuring && totalDistance > 0 && (
        <Paper
          sx={{
            position: 'absolute',
            bottom: 10,
            left: 10,
            zIndex: 1000,
            p: 2,
          }}
        >
          <Typography variant="h6">
            Distance: {(totalDistance / 1000).toFixed(2)} km
          </Typography>
        </Paper>
      )}

      {/* Color legend */}
      {blastPlan?.holes && blastPlan.holes.length > 0 && (
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
            {COLOR_SCHEMES[colorBy as keyof typeof COLOR_SCHEMES].name}
          </Typography>
          {colorBy !== 'explosive' && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="caption">{colorRange.min.toFixed(1)}</Typography>
              <Box
                sx={{
                  width: 100,
                  height: 10,
                  background: `linear-gradient(to right, ${
                    colorBy === 'charge' ? 'hsl(120, 70%, 50%), hsl(0, 70%, 50%)' :
                    colorBy === 'delay' ? 'hsl(0, 70%, 50%), hsl(270, 70%, 50%)' :
                    'hsl(0, 70%, 50%), hsl(240, 70%, 50%)'
                  })`,
                  borderRadius: 1,
                }}
              />
              <Typography variant="caption">{colorRange.max.toFixed(1)}</Typography>
            </Box>
          )}
          {colorBy === 'explosive' && (
            <Stack spacing={0.5}>
              <Chip label="ANFO" size="small" sx={{ bgcolor: '#ff6b6b', color: 'white' }} />
              <Chip label="Emulsion" size="small" sx={{ bgcolor: '#4ecdc4', color: 'white' }} />
              <Chip label="Slurry" size="small" sx={{ bgcolor: '#45b7d1', color: 'white' }} />
            </Stack>
          )}
        </Paper>
      )}

      {/* Hole edit dialog */}
      <HoleEditDialog
        hole={selectedHole}
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        onSave={handleHoleSave}
      />
    </Box>
  );
};