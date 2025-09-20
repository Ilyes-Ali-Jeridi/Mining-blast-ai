# Optimization Interface Components

This directory contains the React components for the optimization interface and progress tracking functionality, implementing task 8.4 from the automated drill-blast system specification.

## Components Overview

### OptimizationInterface
The main component that orchestrates the entire optimization workflow. It provides:
- Tabbed interface for configuration, progress, results, and history
- Integration with WebSocket for real-time progress updates
- Optimization session management
- Result comparison and selection

### OptimizationConfig
Configuration component for setting optimization parameters:
- Algorithm selection (CP-SAT, SciPy DE, SLSQP, Genetic)
- Parameter tuning (iterations, timeout, convergence tolerance)
- Genetic algorithm specific parameters (population size, mutation rate, crossover rate)
- Preset management (save/load configurations)

### OptimizationProgress
Real-time progress tracking component:
- WebSocket connection status
- Overall optimization progress with progress bars
- Algorithm-specific progress tracking
- Elapsed time and performance metrics
- Cancel/restart controls

### OptimizationResults
Results comparison and management component:
- Tabbed view of results (summary, detailed comparison, performance metrics)
- Algorithm performance comparison
- Result selection and download
- Comparison mode for multiple results

## Features Implemented

### ✅ Optimization Parameter Configuration Interface
- Multi-algorithm selection with descriptions
- Parameter validation and safe ranges
- Preset system for saving/loading configurations
- Algorithm-specific parameter sections

### ✅ Real-time Progress Display with WebSocket Integration
- Live connection to optimization WebSocket endpoint
- Real-time progress updates with progress bars
- Algorithm switching notifications
- Connection health monitoring with ping/pong
- Automatic reconnection on connection loss

### ✅ Solution Comparison and Ranking Display
- Multi-result comparison tables
- Performance metrics visualization
- Best result highlighting
- Trend indicators (up/down arrows)
- Detailed comparison cards

### ✅ Optimization Cancellation and Restart Controls
- Cancel button during active optimization
- Restart functionality after completion/failure
- Session state management
- Error handling and user feedback

### ✅ Optimization History and Result Caching
- Historical session tracking
- Result persistence and retrieval
- Session metadata display
- Performance analytics across sessions

## WebSocket Integration

The optimization interface uses WebSocket connections for real-time updates:

```typescript
// WebSocket endpoint
ws://localhost:8000/api/v1/ws/optimization/{optimization_id}

// Message types handled:
- optimization_progress: Real-time progress updates
- optimization_completed: Final results
- optimization_failed: Error notifications
- optimization_cancelled: Cancellation confirmations
- ping/pong: Connection health checks
```

## API Integration

The components integrate with the following API endpoints:

```typescript
// Start optimization
POST /api/v1/optimization/{blast_id}/optimize-async

// Get status
GET /api/v1/optimization/status/{optimization_id}

// Cancel optimization
POST /api/v1/optimization/cancel/{optimization_id}

// List active optimizations
GET /api/v1/optimization/active

// Get history
GET /api/v1/blast-plans/{blast_id}/optimization-history

// Preset management
GET/POST/DELETE /api/v1/optimization/presets
```

## Usage Example

```tsx
import { OptimizationInterface } from './components/Optimization';

function BlastPlanOptimization({ blastPlan }) {
  const handleOptimizationComplete = (result) => {
    console.log('Optimization completed:', result);
    // Update blast plan with optimized parameters
  };

  const handleBlastPlanUpdate = (updatedPlan) => {
    // Save updated blast plan
  };

  return (
    <OptimizationInterface
      blastPlan={blastPlan}
      onOptimizationComplete={handleOptimizationComplete}
      onBlastPlanUpdate={handleBlastPlanUpdate}
    />
  );
}
```

## State Management

The optimization interface manages several types of state:

- **Configuration State**: Algorithm selection and parameters
- **Session State**: Current optimization session information
- **Progress State**: Real-time progress updates from WebSocket
- **Results State**: Historical and current optimization results
- **UI State**: Tab selection, dialogs, notifications

## Error Handling

Comprehensive error handling includes:
- WebSocket connection failures with automatic retry
- API request failures with user-friendly messages
- Optimization failures with detailed error information
- Network connectivity issues with graceful degradation

## Performance Considerations

- WebSocket connections are managed efficiently with proper cleanup
- Large result sets are paginated and virtualized
- Progress updates are throttled to prevent UI flooding
- Component re-renders are optimized with React.memo and useCallback

## Testing

The components include comprehensive tests covering:
- Component rendering and interaction
- WebSocket message handling
- API integration
- Error scenarios
- State management

Run tests with:
```bash
npm test -- --testPathPattern=Optimization
```

## Requirements Satisfied

This implementation satisfies the following requirements from the specification:

- **Requirement 8.2**: Real-time solver iterations and objective improvements via WebSocket
- **Requirement 8.7**: Optimization interface with parameter configuration and progress tracking
- **Task 8.4**: Complete optimization interface and progress tracking implementation

## Future Enhancements

Potential improvements for future iterations:
- Advanced visualization of optimization landscapes
- Machine learning-based parameter recommendations
- Integration with external optimization solvers
- Collaborative optimization sessions
- Advanced result analytics and reporting