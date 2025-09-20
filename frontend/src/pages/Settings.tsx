import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Alert,
  Button,
  CircularProgress,
} from '@mui/material';
import { Save as SaveIcon } from '@mui/icons-material';
import { ExplosivesManagement } from '../components/Forms';
import { ExplosiveSpec, FormValidationState } from '../types';
import apiService from '../services/api';

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
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Explosives management state
  const [explosives, setExplosives] = useState<ExplosiveSpec[]>([]);
  const [explosivesValidation, setExplosivesValidation] = useState<FormValidationState>({
    isValid: true,
    errors: [],
    warnings: []
  });

  // Load initial data
  useEffect(() => {
    loadExplosives();
  }, []);

  const loadExplosives = async () => {
    setLoading(true);
    try {
      const response = await apiService.get<ExplosiveSpec[]>('/configuration/explosives');
      if (response.success) {
        setExplosives(response.data);
      }
    } catch (err: any) {
      setError('Failed to load explosives configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
    setError(null);
    setSuccess(null);
  };

  const handleSaveExplosives = async () => {
    if (!explosivesValidation.isValid) {
      setError('Please correct validation errors before saving');
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await apiService.post('/configuration/explosives', { explosives });
      if (response.success) {
        setSuccess('Explosives configuration saved successfully');
      } else {
        setError(response.message || 'Failed to save explosives configuration');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to save explosives configuration');
    } finally {
      setSaving(false);
    }
  };

  const canSave = () => {
    switch (activeTab) {
      case 0: // Explosives
        return explosivesValidation.isValid && explosives.length > 0;
      default:
        return false;
    }
  };

  const handleSave = () => {
    switch (activeTab) {
      case 0:
        handleSaveExplosives();
        break;
      default:
        break;
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Settings
        </Typography>
        <Button
          variant="contained"
          startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
          onClick={handleSave}
          disabled={!canSave() || saving}
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Paper sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={handleTabChange}>
            <Tab label="Explosives Database" />
            <Tab label="Safety Parameters" disabled />
            <Tab label="Physics Constants" disabled />
            <Tab label="System Configuration" disabled />
          </Tabs>
        </Box>

        <TabPanel value={activeTab} index={0}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Box>
              <Typography variant="h6" gutterBottom>
                Explosives Database Management
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Configure the available explosive types for blast planning. These will be available
                when creating sites and optimizing blast plans.
              </Typography>
              
              <ExplosivesManagement
                explosives={explosives}
                onChange={setExplosives}
                onValidationChange={setExplosivesValidation}
              />
            </Box>
          )}
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <Typography variant="h6" gutterBottom>
            Safety Parameters
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure default safety limits and regulatory constraints.
            (Coming in future updates)
          </Typography>
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <Typography variant="h6" gutterBottom>
            Physics Model Constants
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure default parameters for Kuz-Ram, PPV models, and other physics calculations.
            (Coming in future updates)
          </Typography>
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          <Typography variant="h6" gutterBottom>
            System Configuration
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure system-wide settings, units, and preferences.
            (Coming in future updates)
          </Typography>
        </TabPanel>
      </Paper>
    </Box>
  );
};