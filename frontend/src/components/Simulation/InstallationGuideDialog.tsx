/**
 * Dialog for displaying installation guides for simulation tools
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
  Tabs,
  Tab,
  Paper,
  CircularProgress,
  Alert,
} from '@mui/material';

import { simulationService, SimulationCapabilities } from '../../services/simulationService';

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
      id={`guide-tabpanel-${index}`}
      aria-labelledby={`guide-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

interface InstallationGuideDialogProps {
  open: boolean;
  onClose: () => void;
  capabilities: SimulationCapabilities | null;
}

export const InstallationGuideDialog: React.FC<InstallationGuideDialogProps> = ({
  open,
  onClose,
  capabilities,
}) => {
  const [tabValue, setTabValue] = useState(0);
  const [guides, setGuides] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      loadGuides();
    }
  }, [open]);

  const loadGuides = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const installationGuides = await simulationService.getInstallationGuides();
      setGuides(installationGuides);
    } catch (err: any) {
      setError('Failed to load installation guides');
      console.error('Error loading guides:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const renderGuideContent = (guide: string) => (
    <Paper sx={{ p: 2, maxHeight: 400, overflow: 'auto' }}>
      <pre style={{ 
        whiteSpace: 'pre-wrap', 
        fontFamily: 'monospace', 
        fontSize: '0.875rem',
        margin: 0 
      }}>
        {guide}
      </pre>
    </Paper>
  );

  const availableGuides = Object.keys(guides);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Installation Guides</DialogTitle>
      
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
        ) : availableGuides.length === 0 ? (
          <Typography>No installation guides available</Typography>
        ) : (
          <>
            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
              <Tabs value={tabValue} onChange={handleTabChange}>
                {availableGuides.map((tool, index) => (
                  <Tab 
                    key={tool} 
                    label={tool === 'blastfoam' ? 'blastFoam' : tool.toUpperCase()} 
                  />
                ))}
              </Tabs>
            </Box>
            
            {availableGuides.map((tool, index) => (
              <TabPanel key={tool} value={tabValue} index={index}>
                <Typography variant="h6" gutterBottom>
                  {tool === 'blastfoam' ? 'blastFoam' : tool.toUpperCase()} Installation Guide
                </Typography>
                
                {capabilities && (
                  <Alert 
                    severity={
                      (tool === 'blastfoam' && capabilities.blastfoam_available) ||
                      (tool === 'yade' && capabilities.yade_available) 
                        ? 'success' 
                        : 'warning'
                    }
                    sx={{ mb: 2 }}
                  >
                    {(tool === 'blastfoam' && capabilities.blastfoam_available) ||
                     (tool === 'yade' && capabilities.yade_available) 
                      ? `${tool === 'blastfoam' ? 'blastFoam' : tool.toUpperCase()} is already available on this system`
                      : `${tool === 'blastfoam' ? 'blastFoam' : tool.toUpperCase()} is not currently available. Follow the guide below to install it.`
                    }
                  </Alert>
                )}
                
                {renderGuideContent(guides[tool])}
              </TabPanel>
            ))}
          </>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};