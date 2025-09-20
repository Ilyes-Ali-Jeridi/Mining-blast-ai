import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControlLabel,
  Checkbox,
  Typography,
  Box,
  Alert,
  Divider,
  Grid,
  Card,
  CardContent,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CircularProgress
} from '@mui/material';
import {
  Assignment,
  Security,
  CheckCircle,
  Warning,
  Person,
  Today,
  Gavel
} from '@mui/icons-material';
import { BlastPlan } from '../../types';

interface EngineerSignOffDialogProps {
  open: boolean;
  onClose: () => void;
  onSignOff: (signOffData: SignOffData) => Promise<void>;
  blastPlan?: BlastPlan;
}

interface SignOffData {
  engineer_name: string;
  engineer_license: string;
  certification_statement: string;
  safety_acknowledgment: boolean;
  regulatory_compliance: boolean;
  technical_review: boolean;
  signature_timestamp: string;
  comments?: string;
}

const LEGAL_DISCLAIMER = `
I, as a qualified mining engineer, hereby certify that:

1. I have reviewed this blast plan in its entirety and confirm it meets all applicable safety standards and regulatory requirements.

2. All safety constraints have been validated and are within acceptable limits for the specified site conditions.

3. The blast design is technically sound and appropriate for the geological and operational conditions described.

4. I accept professional responsibility for this blast plan and its implementation according to the specified parameters.

5. This certification is made in accordance with local mining regulations and professional engineering standards.

WARNING: This blast plan must be implemented exactly as specified. Any modifications require re-validation and new engineer certification.
`;

const REQUIRED_CERTIFICATIONS = [
  {
    id: 'safety_acknowledgment',
    title: 'Safety Standards Compliance',
    description: 'I confirm all safety constraints are met and within regulatory limits'
  },
  {
    id: 'regulatory_compliance',
    title: 'Regulatory Compliance',
    description: 'I confirm this plan complies with all applicable mining regulations'
  },
  {
    id: 'technical_review',
    title: 'Technical Review Complete',
    description: 'I have completed a thorough technical review of all blast parameters'
  }
];

export const EngineerSignOffDialog: React.FC<EngineerSignOffDialogProps> = ({
  open,
  onClose,
  onSignOff,
  blastPlan
}) => {
  const [signOffData, setSignOffData] = useState<SignOffData>({
    engineer_name: '',
    engineer_license: '',
    certification_statement: '',
    safety_acknowledgment: false,
    regulatory_compliance: false,
    technical_review: false,
    signature_timestamp: '',
    comments: ''
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmationStep, setConfirmationStep] = useState(false);
  const [typedConfirmation, setTypedConfirmation] = useState('');

  const handleInputChange = (field: keyof SignOffData, value: any) => {
    setSignOffData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleCertificationChange = (certificationId: string, checked: boolean) => {
    setSignOffData(prev => ({
      ...prev,
      [certificationId]: checked
    }));
  };

  const isFormValid = (): boolean => {
    return (
      signOffData.engineer_name.trim() !== '' &&
      signOffData.engineer_license.trim() !== '' &&
      signOffData.safety_acknowledgment &&
      signOffData.regulatory_compliance &&
      signOffData.technical_review &&
      signOffData.certification_statement.trim() !== ''
    );
  };

  const isConfirmationValid = (): boolean => {
    return typedConfirmation === signOffData.engineer_name;
  };

  const handleProceedToConfirmation = () => {
    if (isFormValid()) {
      setConfirmationStep(true);
    }
  };

  const handleSubmitSignOff = async () => {
    if (!isFormValid() || !isConfirmationValid()) return;
    
    setIsSubmitting(true);
    
    try {
      const finalSignOffData = {
        ...signOffData,
        signature_timestamp: new Date().toISOString()
      };
      
      await onSignOff(finalSignOffData);
      handleClose();
    } catch (error) {
      console.error('Sign-off failed:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setSignOffData({
      engineer_name: '',
      engineer_license: '',
      certification_statement: '',
      safety_acknowledgment: false,
      regulatory_compliance: false,
      technical_review: false,
      signature_timestamp: '',
      comments: ''
    });
    setConfirmationStep(false);
    setTypedConfirmation('');
    setIsSubmitting(false);
    onClose();
  };

  const canSignOff = blastPlan?.safety_status?.is_valid;

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      disableEscapeKeyDown={confirmationStep}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Assignment color="primary" />
          Engineer Sign-Off Certification
        </Box>
      </DialogTitle>

      <DialogContent>
        {!canSignOff ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Cannot Sign Off - Safety Violations Present
            </Typography>
            <Typography variant="body2">
              This blast plan has safety violations and cannot be signed off. 
              Please resolve all safety issues before attempting to certify this plan.
            </Typography>
          </Alert>
        ) : (
          <>
            {!confirmationStep ? (
              <>
                {/* Plan Summary */}
                <Card sx={{ mb: 3 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Blast Plan Summary
                    </Typography>
                    
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography variant="body2" color="text.secondary">
                          Total Holes:
                        </Typography>
                        <Typography variant="body1">
                          {blastPlan?.holes.length || 0}
                        </Typography>
                      </Grid>
                      
                      <Grid item xs={6}>
                        <Typography variant="body2" color="text.secondary">
                          Total Charge:
                        </Typography>
                        <Typography variant="body1">
                          {blastPlan?.holes.reduce((sum, hole) => sum + hole.charge_kg, 0).toFixed(1) || 0} kg
                        </Typography>
                      </Grid>
                      
                      <Grid item xs={6}>
                        <Typography variant="body2" color="text.secondary">
                          Safety Status:
                        </Typography>
                        <Chip
                          icon={<CheckCircle />}
                          label="VALIDATED"
                          color="success"
                          size="small"
                        />
                      </Grid>
                      
                      <Grid item xs={6}>
                        <Typography variant="body2" color="text.secondary">
                          Predicted P80:
                        </Typography>
                        <Typography variant="body1">
                          {blastPlan?.predicted_fragmentation?.p80.toFixed(1) || 'N/A'} mm
                        </Typography>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>

                {/* Engineer Information */}
                <Box mb={3}>
                  <Typography variant="h6" gutterBottom>
                    Engineer Information
                  </Typography>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Engineer Name"
                        value={signOffData.engineer_name}
                        onChange={(e) => handleInputChange('engineer_name', e.target.value)}
                        required
                        InputProps={{
                          startAdornment: <Person sx={{ mr: 1, color: 'text.secondary' }} />
                        }}
                      />
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Professional License Number"
                        value={signOffData.engineer_license}
                        onChange={(e) => handleInputChange('engineer_license', e.target.value)}
                        required
                        InputProps={{
                          startAdornment: <Gavel sx={{ mr: 1, color: 'text.secondary' }} />
                        }}
                      />
                    </Grid>
                  </Grid>
                </Box>

                {/* Required Certifications */}
                <Box mb={3}>
                  <Typography variant="h6" gutterBottom>
                    Required Certifications
                  </Typography>
                  
                  <List>
                    {REQUIRED_CERTIFICATIONS.map((cert) => (
                      <ListItem key={cert.id} sx={{ pl: 0 }}>
                        <ListItemIcon>
                          <FormControlLabel
                            control={
                              <Checkbox
                                checked={signOffData[cert.id as keyof SignOffData] as boolean}
                                onChange={(e) => handleCertificationChange(cert.id, e.target.checked)}
                                color="primary"
                              />
                            }
                            label=""
                          />
                        </ListItemIcon>
                        <ListItemText
                          primary={cert.title}
                          secondary={cert.description}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>

                {/* Legal Disclaimer */}
                <Box mb={3}>
                  <Typography variant="h6" gutterBottom>
                    Legal Certification Statement
                  </Typography>
                  
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    <Typography variant="body2">
                      Please read the following legal disclaimer carefully before proceeding.
                    </Typography>
                  </Alert>
                  
                  <Box
                    sx={{
                      p: 2,
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      bgcolor: 'grey.50',
                      maxHeight: 200,
                      overflow: 'auto'
                    }}
                  >
                    <Typography variant="body2" style={{ whiteSpace: 'pre-line' }}>
                      {LEGAL_DISCLAIMER}
                    </Typography>
                  </Box>
                </Box>

                {/* Certification Statement */}
                <Box mb={3}>
                  <TextField
                    fullWidth
                    multiline
                    rows={3}
                    label="Type 'I ACCEPT PROFESSIONAL RESPONSIBILITY' to confirm"
                    value={signOffData.certification_statement}
                    onChange={(e) => handleInputChange('certification_statement', e.target.value)}
                    required
                    helperText="You must type the exact phrase above to proceed"
                  />
                </Box>

                {/* Optional Comments */}
                <Box mb={2}>
                  <TextField
                    fullWidth
                    multiline
                    rows={3}
                    label="Additional Comments (Optional)"
                    value={signOffData.comments}
                    onChange={(e) => handleInputChange('comments', e.target.value)}
                    helperText="Any additional notes or conditions for this certification"
                  />
                </Box>
              </>
            ) : (
              /* Confirmation Step */
              <Box>
                <Alert severity="warning" sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    Final Confirmation Required
                  </Typography>
                  <Typography variant="body2">
                    You are about to certify this blast plan. This action creates a legal record 
                    and cannot be undone. Please confirm your identity by typing your name exactly 
                    as entered above.
                  </Typography>
                </Alert>

                <Box mb={3}>
                  <Typography variant="body1" gutterBottom>
                    Engineer: <strong>{signOffData.engineer_name}</strong>
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    License: <strong>{signOffData.engineer_license}</strong>
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    Timestamp: <strong>{new Date().toLocaleString()}</strong>
                  </Typography>
                </Box>

                <TextField
                  fullWidth
                  label="Type your name to confirm"
                  value={typedConfirmation}
                  onChange={(e) => setTypedConfirmation(e.target.value)}
                  required
                  error={typedConfirmation !== '' && !isConfirmationValid()}
                  helperText={
                    typedConfirmation !== '' && !isConfirmationValid()
                      ? 'Name must match exactly'
                      : `Type "${signOffData.engineer_name}" to confirm`
                  }
                />
              </Box>
            )}
          </>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={isSubmitting}>
          Cancel
        </Button>
        
        {canSignOff && (
          <>
            {!confirmationStep ? (
              <Button
                onClick={handleProceedToConfirmation}
                variant="contained"
                disabled={!isFormValid() || signOffData.certification_statement !== 'I ACCEPT PROFESSIONAL RESPONSIBILITY'}
                startIcon={<Security />}
              >
                Proceed to Confirmation
              </Button>
            ) : (
              <Button
                onClick={handleSubmitSignOff}
                variant="contained"
                color="primary"
                disabled={!isConfirmationValid() || isSubmitting}
                startIcon={isSubmitting ? <CircularProgress size={20} /> : <Assignment />}
              >
                {isSubmitting ? 'Signing Off...' : 'Sign Off Plan'}
              </Button>
            )}
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default EngineerSignOffDialog;