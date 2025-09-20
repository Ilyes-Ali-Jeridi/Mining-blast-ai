import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  TooltipItem
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Alert,
  Chip,
  Grid
} from '@mui/material';
import { FragmentationCurve } from '../../types';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface FragmentationCurveChartProps {
  fragmentationCurve?: FragmentationCurve;
  targetP80?: number;
  measuredCurve?: FragmentationCurve;
  title?: string;
  height?: number;
  showSieveAnalysis?: boolean;
}

export const FragmentationCurveChart: React.FC<FragmentationCurveChartProps> = ({
  fragmentationCurve,
  targetP80,
  measuredCurve,
  title = "Fragmentation Curve",
  height = 400,
  showSieveAnalysis = true
}) => {
  // Generate fragmentation curve data points
  const generateCurveData = (curve: FragmentationCurve) => {
    const sizes = [];
    const passingPercentages = [];
    
    // Generate size range from 1mm to 1000mm (logarithmic scale)
    for (let i = 0; i <= 100; i++) {
      const size = Math.pow(10, (i / 100) * 3); // 1mm to 1000mm
      sizes.push(size);
      
      // Calculate passing percentage based on distribution type
      let passingPercent: number;
      
      if (curve.distribution_type === 'rosin_rammler') {
        // Rosin-Rammler distribution: P(x) = 1 - exp(-(x/xc)^n)
        const xc = curve.p50 / Math.pow(Math.log(2), 1/curve.uniformity_index);
        passingPercent = (1 - Math.exp(-Math.pow(size / xc, curve.uniformity_index))) * 100;
      } else {
        // Swebrec distribution (simplified approximation)
        const b = curve.uniformity_index;
        const x50 = curve.p50;
        passingPercent = 100 / (1 + Math.pow(size / x50, -b));
      }
      
      passingPercentages.push(Math.min(100, Math.max(0, passingPercent)));
    }
    
    return { sizes, passingPercentages };
  };

  // Generate standard sieve sizes for analysis
  const standardSieveSizes = [
    0.075, 0.15, 0.3, 0.6, 1.18, 2.36, 4.75, 9.5, 12.5, 19, 25, 37.5, 50, 75, 100, 150, 200, 300
  ];

  const chartData = useMemo(() => {
    const datasets = [];
    
    if (fragmentationCurve) {
      const { sizes, passingPercentages } = generateCurveData(fragmentationCurve);
      
      datasets.push({
        label: 'Predicted Fragmentation',
        data: sizes.map((size, index) => ({
          x: size,
          y: passingPercentages[index]
        })),
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.1)',
        borderWidth: 2,
        fill: false,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 5
      });
    }
    
    if (measuredCurve) {
      const { sizes, passingPercentages } = generateCurveData(measuredCurve);
      
      datasets.push({
        label: 'Measured Fragmentation',
        data: sizes.map((size, index) => ({
          x: size,
          y: passingPercentages[index]
        })),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.1)',
        borderWidth: 2,
        borderDash: [5, 5],
        fill: false,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 5
      });
    }
    
    // Add target P80 line if specified
    if (targetP80) {
      datasets.push({
        label: `Target P80 (${targetP80}mm)`,
        data: [
          { x: targetP80, y: 0 },
          { x: targetP80, y: 100 }
        ],
        borderColor: 'rgb(255, 159, 64)',
        backgroundColor: 'rgba(255, 159, 64, 0.1)',
        borderWidth: 2,
        borderDash: [10, 5],
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 0
      });
    }
    
    // Add P80 line for predicted curve
    if (fragmentationCurve) {
      datasets.push({
        label: `Predicted P80 (${fragmentationCurve.p80.toFixed(1)}mm)`,
        data: [
          { x: fragmentationCurve.p80, y: 0 },
          { x: fragmentationCurve.p80, y: 100 }
        ],
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.1)',
        borderWidth: 1,
        borderDash: [3, 3],
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 0
      });
    }
    
    return { datasets };
  }, [fragmentationCurve, measuredCurve, targetP80]);

  const chartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: title,
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: function(context: TooltipItem<'line'>) {
            const label = context.dataset.label || '';
            if (label.includes('P80')) {
              return `${label}`;
            }
            return `${label}: ${context.parsed.y.toFixed(1)}% passing ${context.parsed.x.toFixed(1)}mm`;
          }
        }
      }
    },
    scales: {
      x: {
        type: 'logarithmic',
        position: 'bottom',
        title: {
          display: true,
          text: 'Particle Size (mm)'
        },
        min: 1,
        max: 1000,
        ticks: {
          callback: function(value) {
            const sizes = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000];
            if (sizes.includes(Number(value))) {
              return value.toString();
            }
            return '';
          }
        }
      },
      y: {
        title: {
          display: true,
          text: 'Cumulative Passing (%)'
        },
        min: 0,
        max: 100,
        ticks: {
          stepSize: 10
        }
      }
    },
    interaction: {
      mode: 'index',
      intersect: false,
    },
    elements: {
      point: {
        radius: 0,
        hoverRadius: 5
      }
    }
  };

  // Calculate sieve analysis data
  const sieveAnalysis = useMemo(() => {
    if (!fragmentationCurve || !showSieveAnalysis) return null;
    
    const analysis = standardSieveSizes.map(size => {
      let passingPercent: number;
      
      if (fragmentationCurve.distribution_type === 'rosin_rammler') {
        const xc = fragmentationCurve.p50 / Math.pow(Math.log(2), 1/fragmentationCurve.uniformity_index);
        passingPercent = (1 - Math.exp(-Math.pow(size, fragmentationCurve.uniformity_index) / Math.pow(xc, fragmentationCurve.uniformity_index))) * 100;
      } else {
        const b = fragmentationCurve.uniformity_index;
        const x50 = fragmentationCurve.p50;
        passingPercent = 100 / (1 + Math.pow(size / x50, -b));
      }
      
      return {
        size,
        passing: Math.min(100, Math.max(0, passingPercent))
      };
    });
    
    // Calculate retained percentages
    const retainedAnalysis = analysis.map((item, index) => {
      const nextPassing = index < analysis.length - 1 ? analysis[index + 1].passing : 100;
      const retained = nextPassing - item.passing;
      
      return {
        ...item,
        retained: Math.max(0, retained)
      };
    });
    
    return retainedAnalysis;
  }, [fragmentationCurve, showSieveAnalysis]);

  if (!fragmentationCurve) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {title}
          </Typography>
          <Alert severity="info">
            No fragmentation data available. Run an optimization to see fragmentation predictions.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box>
      <Card>
        <CardContent>
          <Box sx={{ height: height }}>
            <Line data={chartData} options={chartOptions} />
          </Box>
          
          {/* Key Metrics */}
          <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip
              label={`P10: ${fragmentationCurve.p10.toFixed(1)}mm`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={`P50: ${fragmentationCurve.p50.toFixed(1)}mm`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={`P80: ${fragmentationCurve.p80.toFixed(1)}mm`}
              size="small"
              color="primary"
              variant="outlined"
            />
            <Chip
              label={`Mean: ${fragmentationCurve.mean.toFixed(1)}mm`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={`n: ${fragmentationCurve.uniformity_index.toFixed(2)}`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={fragmentationCurve.distribution_type.replace('_', '-').toUpperCase()}
              size="small"
              color="secondary"
              variant="outlined"
            />
          </Box>
        </CardContent>
      </Card>
      
      {/* Sieve Analysis Table */}
      {sieveAnalysis && showSieveAnalysis && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Sieve Analysis
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Coarse Fractions
                </Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 1, fontSize: '0.875rem' }}>
                  <Typography variant="body2" fontWeight="bold">Size (mm)</Typography>
                  <Typography variant="body2" fontWeight="bold">Passing (%)</Typography>
                  <Typography variant="body2" fontWeight="bold">Retained (%)</Typography>
                  
                  {sieveAnalysis.slice(10).map((item, index) => (
                    <React.Fragment key={index}>
                      <Typography variant="body2">{item.size}</Typography>
                      <Typography variant="body2">{item.passing.toFixed(1)}</Typography>
                      <Typography variant="body2">{item.retained.toFixed(1)}</Typography>
                    </React.Fragment>
                  ))}
                </Box>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Fine Fractions
                </Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 1, fontSize: '0.875rem' }}>
                  <Typography variant="body2" fontWeight="bold">Size (mm)</Typography>
                  <Typography variant="body2" fontWeight="bold">Passing (%)</Typography>
                  <Typography variant="body2" fontWeight="bold">Retained (%)</Typography>
                  
                  {sieveAnalysis.slice(0, 10).map((item, index) => (
                    <React.Fragment key={index}>
                      <Typography variant="body2">{item.size}</Typography>
                      <Typography variant="body2">{item.passing.toFixed(1)}</Typography>
                      <Typography variant="body2">{item.retained.toFixed(1)}</Typography>
                    </React.Fragment>
                  ))}
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default FragmentationCurveChart;