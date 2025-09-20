import React, { useState } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Typography,
    Box,
    Grid,
    Card,
    CardContent,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    Chip,
    Tabs,
    Tab,
    Alert,
    Divider
} from '@mui/material';
import {
    Compare,
    TrendingUp,
    TrendingDown,
    Remove,
    Star,
    Close
} from '@mui/icons-material';
import { OptimizationResult } from '../../types';
import { FragmentationCurveChart } from './FragmentationCurveChart';

interface PlanComparisonDialogProps {
    open: boolean;
    onClose: () => void;
    results: OptimizationResult[];
}

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
    <div hidden={value !== index}>
        {value === index && <Box sx={{ p: 2 }}>{children}</Box>}
    </div>
);

export const PlanComparisonDialog: React.FC<PlanComparisonDialogProps> = ({
    open,
    onClose,
    results
}) => {
    const [tabValue, setTabValue] = useState(0);

    const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
        setTabValue(newValue);
    };

    const getBestResult = (): OptimizationResult | null => {
        if (results.length === 0) return null;
        return results.reduce((best, current) =>
            current.objective_value < best.objective_value ? current : best
        );
    };

    const getComparisonTrend = (value: number, baseValue: number): 'up' | 'down' | 'neutral' => {
        const percentDiff = ((value - baseValue) / baseValue) * 100;
        return percentDiff > 1 ? 'up' : percentDiff < -1 ? 'down' : 'neutral';
    };

    const getTrendIcon = (trend: 'up' | 'down' | 'neutral') => {
        switch (trend) {
            case 'up': return <TrendingUp color="error" fontSize="small" />;
            case 'down': return <TrendingDown color="success" fontSize="small" />;
            default: return <Remove color="disabled" fontSize="small" />;
        }
    };

    const formatPercentDiff = (value: number, baseValue: number): string => {
        const percentDiff = ((value - baseValue) / baseValue) * 100;
        const sign = percentDiff >= 0 ? '+' : '';
        return `${sign}${percentDiff.toFixed(1)}%`;
    };

    const getAlgorithmColor = (algorithm: string) => {
        const colors: Record<string, any> = {
            'cp_sat': 'primary',
            'scipy_de': 'secondary',
            'scipy_slsqp': 'success',
            'genetic': 'warning'
        };
        return colors[algorithm] || 'default';
    };

    if (results.length < 2) {
        return (
            <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
                <DialogTitle>Plan Comparison</DialogTitle>
                <DialogContent>
                    <Alert severity="info">
                        Please select at least 2 optimization results to compare.
                    </Alert>
                </DialogContent>
                <DialogActions>
                    <Button onClick={onClose}>Close</Button>
                </DialogActions>
            </Dialog>
        );
    }

    const bestResult = getBestResult();

    return (
        <Dialog open={open} onClose={onClose} maxWidth="xl" fullWidth>
            <DialogTitle>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Box display="flex" alignItems="center" gap={1}>
                        <Compare color="primary" />
                        Plan Comparison ({results.length} plans)
                    </Box>
                    <Button onClick={onClose} startIcon={<Close />}>
                        Close
                    </Button>
                </Box>
            </DialogTitle>

            <DialogContent>
                <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
                    <Tab label="Overview Comparison" />
                    <Tab label="Fragmentation Analysis" />
                    <Tab label="Performance Metrics" />
                    <Tab label="Detailed Breakdown" />
                </Tabs>

                <TabPanel value={tabValue} index={0}>
                    {/* Overview Comparison */}
                    <Grid container spacing={3}>
                        {results.map((result, index) => (
                            <Grid item xs={12} md={6} lg={4} key={index}>
                                <Card
                                    variant={result === bestResult ? "elevation" : "outlined"}
                                    sx={{
                                        border: result === bestResult ? 2 : 1,
                                        borderColor: result === bestResult ? 'success.main' : 'divider'
                                    }}
                                >
                                    <CardContent>
                                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                                            <Chip
                                                label={result.solver_info.algorithm}
                                                color={getAlgorithmColor(result.solver_info.algorithm)}
                                                size="small"
                                            />
                                            {result === bestResult && (
                                                <Star color="warning" fontSize="small" />
                                            )}
                                        </Box>

                                        <Typography variant="h4" color="primary" gutterBottom>
                                            {result.objective_value.toFixed(2)}
                                        </Typography>

                                        {bestResult && result !== bestResult && (
                                            <Box display="flex" alignItems="center" gap={0.5} mb={1}>
                                                {getTrendIcon(getComparisonTrend(result.objective_value, bestResult.objective_value))}
                                                <Typography variant="body2" color="text.secondary">
                                                    {formatPercentDiff(result.objective_value, bestResult.objective_value)} vs best
                                                </Typography>
                                            </Box>
                                        )}

                                        <Divider sx={{ my: 1 }} />

                                        <Box display="flex" justifyContent="space-between" mb={1}>
                                            <Typography variant="body2" color="text.secondary">
                                                Runtime:
                                            </Typography>
                                            <Typography variant="body2">
                                                {result.solver_info.runtime_seconds.toFixed(1)}s
                                            </Typography>
                                        </Box>

                                        <Box display="flex" justifyContent="space-between" mb={1}>
                                            <Typography variant="body2" color="text.secondary">
                                                Holes:
                                            </Typography>
                                            <Typography variant="body2">
                                                {result.blast_plan.holes.length}
                                            </Typography>
                                        </Box>

                                        <Box display="flex" justifyContent="space-between" mb={1}>
                                            <Typography variant="body2" color="text.secondary">
                                                Total Charge:
                                            </Typography>
                                            <Typography variant="body2">
                                                {result.blast_plan.holes.reduce((sum, hole) => sum + hole.charge_kg, 0).toFixed(1)} kg
                                            </Typography>
                                        </Box>

                                        <Box display="flex" justifyContent="space-between" mb={1}>
                                            <Typography variant="body2" color="text.secondary">
                                                P80:
                                            </Typography>
                                            <Typography variant="body2">
                                                {result.blast_plan.predicted_fragmentation?.p80.toFixed(1) || 'N/A'} mm
                                            </Typography>
                                        </Box>

                                        <Box display="flex" justifyContent="space-between">
                                            <Typography variant="body2" color="text.secondary">
                                                Safety:
                                            </Typography>
                                            <Chip
                                                label={result.blast_plan.safety_status?.is_valid ? 'Valid' : 'Invalid'}
                                                color={result.blast_plan.safety_status?.is_valid ? 'success' : 'error'}
                                                size="small"
                                                variant="outlined"
                                            />
                                        </Box>
                                    </CardContent>
                                </Card>
                            </Grid>
                        ))}
                    </Grid>
                </TabPanel>

                <TabPanel value={tabValue} index={1}>
                    {/* Fragmentation Analysis */}
                    <Grid container spacing={3}>
                        <Grid item xs={12}>
                            <Typography variant="h6" gutterBottom>
                                Fragmentation Curve Comparison
                            </Typography>

                            {/* This would need to be enhanced to show multiple curves */}
                            {results[0]?.blast_plan.predicted_fragmentation && (
                                <FragmentationCurveChart
                                    fragmentationCurve={results[0].blast_plan.predicted_fragmentation}
                                    measuredCurve={results[1]?.blast_plan.predicted_fragmentation}
                                    title="Fragmentation Comparison"
                                    height={400}
                                />
                            )}
                        </Grid>

                        <Grid item xs={12}>
                            <Typography variant="h6" gutterBottom>
                                Fragmentation Metrics Comparison
                            </Typography>

                            <TableContainer component={Paper} variant="outlined">
                                <Table>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Algorithm</TableCell>
                                            <TableCell align="right">P10 (mm)</TableCell>
                                            <TableCell align="right">P50 (mm)</TableCell>
                                            <TableCell align="right">P80 (mm)</TableCell>
                                            <TableCell align="right">Mean (mm)</TableCell>
                                            <TableCell align="right">Uniformity Index</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {results.map((result, index) => {
                                            const frag = result.blast_plan.predicted_fragmentation;
                                            return (
                                                <TableRow key={index}>
                                                    <TableCell>
                                                        <Chip
                                                            label={result.solver_info.algorithm}
                                                            color={getAlgorithmColor(result.solver_info.algorithm)}
                                                            size="small"
                                                            variant="outlined"
                                                        />
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        {frag?.p10.toFixed(1) || 'N/A'}
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        {frag?.p50.toFixed(1) || 'N/A'}
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        <Typography
                                                            variant="body2"
                                                            fontWeight={result === bestResult ? "bold" : "normal"}
                                                        >
                                                            {frag?.p80.toFixed(1) || 'N/A'}
                                                        </Typography>
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        {frag?.mean.toFixed(1) || 'N/A'}
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        {frag?.uniformity_index.toFixed(2) || 'N/A'}
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </Grid>
                    </Grid>
                </TabPanel>

                <TabPanel value={tabValue} index={2}>
                    {/* Performance Metrics */}
                    <Grid container spacing={3}>
                        <Grid item xs={12} md={6}>
                            <Typography variant="h6" gutterBottom>
                                Optimization Performance
                            </Typography>

                            <TableContainer component={Paper} variant="outlined">
                                <Table>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Algorithm</TableCell>
                                            <TableCell align="right">Objective Value</TableCell>
                                            <TableCell align="right">Runtime (s)</TableCell>
                                            <TableCell align="right">Iterations</TableCell>
                                            <TableCell align="right">Efficiency</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {results.map((result, index) => (
                                            <TableRow
                                                key={index}
                                                sx={{
                                                    backgroundColor: result === bestResult ? 'success.light' : 'inherit'
                                                }}
                                            >
                                                <TableCell>
                                                    <Chip
                                                        label={result.solver_info.algorithm}
                                                        color={getAlgorithmColor(result.solver_info.algorithm)}
                                                        size="small"
                                                        variant="outlined"
                                                    />
                                                </TableCell>
                                                <TableCell align="right">
                                                    <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5}>
                                                        <Typography
                                                            variant="body2"
                                                            fontWeight={result === bestResult ? "bold" : "normal"}
                                                        >
                                                            {result.objective_value.toFixed(2)}
                                                        </Typography>
                                                        {bestResult && result !== bestResult &&
                                                            getTrendIcon(getComparisonTrend(result.objective_value, bestResult.objective_value))
                                                        }
                                                    </Box>
                                                </TableCell>
                                                <TableCell align="right">
                                                    {result.solver_info.runtime_seconds.toFixed(1)}
                                                </TableCell>
                                                <TableCell align="right">
                                                    {result.solver_info.iterations.toLocaleString()}
                                                </TableCell>
                                                <TableCell align="right">
                                                    {(result.objective_value / result.solver_info.runtime_seconds).toFixed(2)}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </Grid>

                        <Grid item xs={12} md={6}>
                            <Typography variant="h6" gutterBottom>
                                Solution Quality Metrics
                            </Typography>

                            <Box>
                                <Box mb={2}>
                                    <Typography variant="body2" color="text.secondary">
                                        Best Objective Value
                                    </Typography>
                                    <Typography variant="h4" color="success.main">
                                        {bestResult?.objective_value.toFixed(2) || 'N/A'}
                                    </Typography>
                                </Box>

                                <Box mb={2}>
                                    <Typography variant="body2" color="text.secondary">
                                        Average Objective Value
                                    </Typography>
                                    <Typography variant="h5">
                                        {(results.reduce((sum, r) => sum + r.objective_value, 0) / results.length).toFixed(2)}
                                    </Typography>
                                </Box>

                                <Box mb={2}>
                                    <Typography variant="body2" color="text.secondary">
                                        Standard Deviation
                                    </Typography>
                                    <Typography variant="body1">
                                        {(() => {
                                            const mean = results.reduce((sum, r) => sum + r.objective_value, 0) / results.length;
                                            const variance = results.reduce((sum, r) => sum + Math.pow(r.objective_value - mean, 2), 0) / results.length;
                                            return Math.sqrt(variance).toFixed(2);
                                        })()}
                                    </Typography>
                                </Box>

                                <Box>
                                    <Typography variant="body2" color="text.secondary">
                                        Range (Max - Min)
                                    </Typography>
                                    <Typography variant="body1">
                                        {(() => {
                                            const values = results.map(r => r.objective_value);
                                            return (Math.max(...values) - Math.min(...values)).toFixed(2);
                                        })()}
                                    </Typography>
                                </Box>
                            </Box>
                        </Grid>
                    </Grid>
                </TabPanel>

                <TabPanel value={tabValue} index={3}>
                    {/* Detailed Breakdown */}
                    <Typography variant="h6" gutterBottom>
                        Detailed Plan Comparison
                    </Typography>

                    <TableContainer component={Paper} variant="outlined">
                        <Table>
                            <TableHead>
                                <TableRow>
                                    <TableCell>Metric</TableCell>
                                    {results.map((result, index) => (
                                        <TableCell key={index} align="right">
                                            <Chip
                                                label={result.solver_info.algorithm}
                                                color={getAlgorithmColor(result.solver_info.algorithm)}
                                                size="small"
                                                variant="outlined"
                                            />
                                        </TableCell>
                                    ))}
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                <TableRow>
                                    <TableCell>Objective Value</TableCell>
                                    {results.map((result, index) => (
                                        <TableCell key={index} align="right">
                                            <Typography
                                                variant="body2"
                                                fontWeight={result === bestResult ? "bold" : "normal"}
                                                color={result === bestResult ? "success.main" : "inherit"}
                                            >
                                                {result.objective_value.toFixed(2)}
                                            </Typography>
                                        </TableCell>
                                    ))}
                                </TableRow>

                                <TableRow>
                                    <TableCell>Total Holes</TableCell>
                                    {results.map((result, index) => (
                                        <TableCell key={index} align="right">
                                            {result.blast_plan.holes.length}
                                        </TableCell>
                                    ))}
                                </TableRow>

                                <TableRow>
                                    <TableCell>Total Charge (kg)</TableCell>
                                    {results.map((result, index) => (
                                        <TableCell key={index} align="right">
                                            {result.blast_plan.holes.reduce((sum, hole) => sum + hole.charge_kg, 0).toFixed(1)}
                                        </TableCell>
                                    ))}
                                </TableRow>

                                <TableRow>
                                    <TableCell>Average Charge per Hole (kg)</TableCell>
                                    {results.map((result, index) => {
                                        const totalCharge = result.blast_plan.holes.reduce((sum, hole) => sum + hole.charge_kg, 0);
                                        const avgCharge = totalCharge / result.blast_plan.holes.length;
                                        return (
                                            <TableCell key={index} align="right">
                                                {avgCharge.toFixed(1)}
                                            </TableCell>
                                        );
                                    })}
                                </TableRow>

                                <TableRow>
                                    <TableCell>Predicted P80 (mm)</TableCell>
                                    {results.map((result, index) => (
                                        <TableCell key={index} align="right">
                                            {result.blast_plan.predicted_fragmentation?.p80.toFixed(1) || 'N/A'}
                                        </TableCell>
                                    ))}
                                </TableRow>

                                <TableRow>
                                    <TableCell>Runtime (seconds)</TableCell>
                                    {results.map((result, index) => (
                                        <TableCell key={index} align="right">
                                            {result.solver_info.runtime_seconds.toFixed(1)}
                                        </TableCell>
                                    ))}
                                </TableRow>

                                <TableRow>
                                    <TableCell>Iterations</TableCell>
                                    {results.map((result, index) => (
                                        <TableCell key={index} align="right">
                                            {result.solver_info.iterations.toLocaleString()}
                                        </TableCell>
                                    ))}
                                </TableRow>

                                <TableRow>
                                    <TableCell>Safety Status</TableCell>
                                    {results.map((result, index) => (
                                        <TableCell key={index} align="right">
                                            <Chip
                                                label={result.blast_plan.safety_status?.is_valid ? 'Valid' : 'Invalid'}
                                                color={result.blast_plan.safety_status?.is_valid ? 'success' : 'error'}
                                                size="small"
                                                variant="outlined"
                                            />
                                        </TableCell>
                                    ))}
                                </TableRow>
                            </TableBody>
                        </Table>
                    </TableContainer>
                </TabPanel>
            </DialogContent>

            <DialogActions>
                <Button onClick={onClose} variant="contained">
                    Close Comparison
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default PlanComparisonDialog;