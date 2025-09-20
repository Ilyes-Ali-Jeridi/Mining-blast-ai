"""
Visualization utilities for blast plan data.
Implements requirement 7.3: 2D map generation, fragmentation curves, color-coding, and interactive visualization.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import json
import base64
import io
from datetime import datetime
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.cm import ScalarMappable
import matplotlib.gridspec as gridspec

from ..models.blast_record import BlastRecord
from ..core.logging import get_logger

logger = get_logger(__name__)


class BlastVisualization:
    """Creates visualizations for blast plan data."""
    
    def __init__(self):
        """Initialize visualization utilities."""
        # Set up matplotlib style
        plt.style.use('default')
        
        # Define color schemes
        self.color_schemes = {
            'charge': 'viridis',
            'delay': 'tab10',
            'ppv': 'Reds',
            'safety': ['green', 'yellow', 'red'],
            'fragmentation': 'plasma'
        }
        
        # Default figure settings
        self.default_dpi = 150
        self.default_figsize = (10, 8)
    
    def create_blast_plan_map(
        self,
        blast_record: BlastRecord,
        color_by: str = 'charge',
        include_labels: bool = True,
        include_legend: bool = True,
        include_scale: bool = True,
        include_north_arrow: bool = True,
        output_format: str = 'png'
    ) -> Union[bytes, str]:
        """
        Create 2D blast plan map visualization.
        
        Args:
            blast_record: Blast record to visualize
            color_by: Color holes by ('charge', 'delay', 'explosive_type')
            include_labels: Include hole ID labels
            include_legend: Include color legend
            include_scale: Include scale bar
            include_north_arrow: Include north arrow
            output_format: Output format ('png', 'svg', 'base64')
            
        Returns:
            Visualization as bytes or base64 string
        """
        try:
            if not blast_record.plan_data or 'holes' not in blast_record.plan_data:
                raise ValueError("No hole data available for visualization")
            
            holes = blast_record.plan_data['holes']
            if not holes:
                raise ValueError("Empty hole data")
            
            # Extract coordinates and color data
            x_coords, y_coords, color_values, hole_ids = self._extract_hole_data(holes, color_by)
            
            # Create figure
            fig, ax = plt.subplots(figsize=self.default_figsize, dpi=self.default_dpi)
            
            # Create scatter plot
            scatter = self._create_hole_scatter(ax, x_coords, y_coords, color_values, color_by)
            
            # Add hole labels
            if include_labels and len(holes) <= 100:  # Limit labels for readability
                self._add_hole_labels(ax, x_coords, y_coords, hole_ids)
            
            # Add legend
            if include_legend:
                self._add_color_legend(fig, scatter, color_by, color_values)
            
            # Add scale bar
            if include_scale:
                self._add_scale_bar(ax, x_coords, y_coords)
            
            # Add north arrow
            if include_north_arrow:
                self._add_north_arrow(ax)
            
            # Format axes
            self._format_map_axes(ax, blast_record)
            
            # Add title and metadata
            self._add_map_title(ax, blast_record, color_by)
            
            plt.tight_layout()
            
            # Return in requested format
            return self._save_figure(fig, output_format)
            
        except Exception as e:
            logger.error(
                "Failed to create blast plan map",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
        finally:
            plt.close('all')
    
    def create_fragmentation_curve(
        self,
        blast_record: BlastRecord,
        include_measured: bool = True,
        include_targets: bool = True,
        sieve_sizes: Optional[List[float]] = None,
        output_format: str = 'png'
    ) -> Union[bytes, str]:
        """
        Create fragmentation curve visualization.
        
        Args:
            blast_record: Blast record with fragmentation data
            include_measured: Include measured fragmentation if available
            include_targets: Include target fragmentation lines
            sieve_sizes: Custom sieve sizes for plotting
            output_format: Output format ('png', 'svg', 'base64')
            
        Returns:
            Visualization as bytes or base64 string
        """
        try:
            if sieve_sizes is None:
                sieve_sizes = np.logspace(0, 3, 100)  # 1mm to 1000mm
            
            fig, ax = plt.subplots(figsize=(10, 6), dpi=self.default_dpi)
            
            # Plot predicted fragmentation curve
            if blast_record.predicted_results and 'fragmentation' in blast_record.predicted_results:
                frag_data = blast_record.predicted_results['fragmentation']
                predicted_curve = self._calculate_fragmentation_curve(frag_data, sieve_sizes)
                
                ax.semilogx(sieve_sizes, predicted_curve, 'b-', linewidth=2, 
                           label='Predicted', alpha=0.8)
                
                # Mark key percentiles
                p50 = frag_data.get('p50')
                p80 = frag_data.get('p80')
                
                if p50:
                    ax.axvline(x=p50, color='blue', linestyle='--', alpha=0.7, 
                              label=f'P50 Predicted ({p50:.1f}mm)')
                if p80:
                    ax.axvline(x=p80, color='blue', linestyle=':', alpha=0.7, 
                              label=f'P80 Predicted ({p80:.1f}mm)')
            
            # Plot measured fragmentation curve
            if include_measured and blast_record.measured_results:
                measured_frag = blast_record.measured_results.get('fragmentation_measurements', [])
                if measured_frag:
                    # Use the most recent measurement
                    latest_measurement = measured_frag[-1]
                    measured_curve = self._calculate_measured_fragmentation_curve(
                        latest_measurement, sieve_sizes
                    )
                    
                    ax.semilogx(sieve_sizes, measured_curve, 'r-', linewidth=2, 
                               label='Measured', alpha=0.8)
                    
                    # Mark measured percentiles
                    measured_p80 = latest_measurement.get('measured_p80')
                    if measured_p80:
                        ax.axvline(x=measured_p80, color='red', linestyle=':', alpha=0.7, 
                                  label=f'P80 Measured ({measured_p80:.1f}mm)')
            
            # Add target lines
            if include_targets:
                # Add common target sizes
                target_sizes = [50, 100, 200]  # mm
                for target in target_sizes:
                    ax.axvline(x=target, color='gray', linestyle='-', alpha=0.3)
                    ax.text(target, 95, f'{target}mm', rotation=90, 
                           verticalalignment='top', alpha=0.7)
            
            # Format plot
            ax.set_xlabel('Fragment Size (mm)')
            ax.set_ylabel('Cumulative Passing (%)')
            ax.set_title(f'Fragmentation Curve - {blast_record.blast_name}')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.set_xlim(1, 1000)
            ax.set_ylim(0, 100)
            
            # Add statistics text box
            self._add_fragmentation_stats(ax, blast_record)
            
            plt.tight_layout()
            
            return self._save_figure(fig, output_format)
            
        except Exception as e:
            logger.error(
                "Failed to create fragmentation curve",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
        finally:
            plt.close('all')
    
    def create_delay_sequence_visualization(
        self,
        blast_record: BlastRecord,
        show_timing: bool = True,
        show_charge_flow: bool = True,
        output_format: str = 'png'
    ) -> Union[bytes, str]:
        """
        Create delay sequence visualization.
        
        Args:
            blast_record: Blast record with delay data
            show_timing: Show timing information
            show_charge_flow: Show charge progression
            output_format: Output format ('png', 'svg', 'base64')
            
        Returns:
            Visualization as bytes or base64 string
        """
        try:
            if not blast_record.plan_data or 'holes' not in blast_record.plan_data:
                raise ValueError("No hole data available")
            
            holes = blast_record.plan_data['holes']
            
            # Group holes by delay
            holes_by_delay = {}
            for hole in holes:
                delay = hole.get('delay_ms', 0)
                if delay not in holes_by_delay:
                    holes_by_delay[delay] = []
                holes_by_delay[delay].append(hole)
            
            # Create figure with subplots
            if show_timing and show_charge_flow:
                fig = plt.figure(figsize=(15, 10), dpi=self.default_dpi)
                gs = gridspec.GridSpec(2, 2, height_ratios=[2, 1], width_ratios=[3, 1])
                ax_map = fig.add_subplot(gs[0, :])
                ax_timing = fig.add_subplot(gs[1, 0])
                ax_charge = fig.add_subplot(gs[1, 1])
            else:
                fig, ax_map = plt.subplots(figsize=self.default_figsize, dpi=self.default_dpi)
                ax_timing = ax_charge = None
            
            # Create delay sequence map
            self._create_delay_map(ax_map, holes_by_delay)
            
            # Add timing chart
            if show_timing and ax_timing:
                self._create_timing_chart(ax_timing, holes_by_delay)
            
            # Add charge flow chart
            if show_charge_flow and ax_charge:
                self._create_charge_flow_chart(ax_charge, holes_by_delay)
            
            plt.tight_layout()
            
            return self._save_figure(fig, output_format)
            
        except Exception as e:
            logger.error(
                "Failed to create delay sequence visualization",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
        finally:
            plt.close('all')
    
    def create_ppv_contour_map(
        self,
        blast_record: BlastRecord,
        contour_levels: Optional[List[float]] = None,
        include_receptors: bool = True,
        output_format: str = 'png'
    ) -> Union[bytes, str]:
        """
        Create PPV contour map visualization.
        
        Args:
            blast_record: Blast record with PPV data
            contour_levels: PPV contour levels (mm/s)
            include_receptors: Include receptor locations
            output_format: Output format ('png', 'svg', 'base64')
            
        Returns:
            Visualization as bytes or base64 string
        """
        try:
            if contour_levels is None:
                contour_levels = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
            
            fig, ax = plt.subplots(figsize=self.default_figsize, dpi=self.default_dpi)
            
            # Calculate blast center
            blast_center = self._calculate_blast_center(blast_record)
            if not blast_center:
                raise ValueError("Cannot calculate blast center")
            
            # Create PPV contours
            self._create_ppv_contours(ax, blast_center, blast_record, contour_levels)
            
            # Add hole locations
            if blast_record.plan_data and 'holes' in blast_record.plan_data:
                holes = blast_record.plan_data['holes']
                x_coords = [h.get('coordinates', {}).get('x', 0) for h in holes]
                y_coords = [h.get('coordinates', {}).get('y', 0) for h in holes]
                
                ax.scatter(x_coords, y_coords, c='black', s=20, marker='o', 
                          alpha=0.7, label='Blast Holes')
            
            # Add receptors
            if include_receptors and blast_record.predicted_results:
                ppv_data = blast_record.predicted_results.get('ppv_predictions', {})
                receptors = ppv_data.get('receptor_predictions', [])
                
                for receptor in receptors:
                    coords = receptor.get('coordinates', {})
                    x, y = coords.get('x', 0), coords.get('y', 0)
                    ppv = receptor.get('predicted_ppv', 0)
                    
                    # Color code by PPV level
                    color = 'green' if ppv < 5 else 'orange' if ppv < 10 else 'red'
                    ax.scatter(x, y, c=color, s=100, marker='^', 
                              edgecolors='black', linewidth=1)
                    ax.annotate(f"{receptor.get('receptor_name', '')}\n{ppv:.1f}mm/s", 
                               (x, y), xytext=(5, 5), textcoords='offset points',
                               fontsize=8, ha='left')
            
            # Format plot
            ax.set_xlabel('X Coordinate (m)')
            ax.set_ylabel('Y Coordinate (m)')
            ax.set_title(f'PPV Contours - {blast_record.blast_name}')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.set_aspect('equal')
            
            # Add north arrow
            self._add_north_arrow(ax)
            
            plt.tight_layout()
            
            return self._save_figure(fig, output_format)
            
        except Exception as e:
            logger.error(
                "Failed to create PPV contour map",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
        finally:
            plt.close('all')
    
    def create_interactive_visualization_data(
        self,
        blast_record: BlastRecord
    ) -> Dict[str, Any]:
        """
        Create data structure for interactive visualization.
        
        Args:
            blast_record: Blast record to process
            
        Returns:
            Dictionary with visualization data for frontend
        """
        try:
            viz_data = {
                "blast_info": {
                    "id": blast_record.id,
                    "name": blast_record.blast_name,
                    "total_holes": blast_record.total_holes,
                    "total_explosive": blast_record.total_explosive
                },
                "holes": [],
                "boundaries": {},
                "contours": {},
                "statistics": {}
            }
            
            # Process hole data
            if blast_record.plan_data and 'holes' in blast_record.plan_data:
                holes = blast_record.plan_data['holes']
                
                for hole in holes:
                    coords = hole.get('coordinates', {})
                    hole_data = {
                        "id": hole.get('hole_id', ''),
                        "coordinates": [coords.get('x', 0), coords.get('y', 0)],
                        "properties": {
                            "depth": hole.get('depth', 0),
                            "diameter": hole.get('diameter', 0),
                            "charge_kg": hole.get('charge_kg', 0),
                            "delay_ms": hole.get('delay_ms', 0),
                            "explosive_type": hole.get('explosive_type', ''),
                            "stemming_m": hole.get('stemming_m', 0)
                        }
                    }
                    viz_data["holes"].append(hole_data)
                
                # Calculate boundaries
                viz_data["boundaries"] = self._calculate_visualization_boundaries(holes)
            
            # Add fragmentation curve data
            if blast_record.predicted_results and 'fragmentation' in blast_record.predicted_results:
                frag_data = blast_record.predicted_results['fragmentation']
                viz_data["fragmentation_curve"] = self._prepare_fragmentation_curve_data(frag_data)
            
            # Add PPV contour data
            if blast_record.predicted_results and 'ppv_predictions' in blast_record.predicted_results:
                ppv_data = blast_record.predicted_results['ppv_predictions']
                viz_data["ppv_contours"] = self._prepare_ppv_contour_data(ppv_data, blast_record)
            
            # Add statistics
            viz_data["statistics"] = {
                "powder_factor": blast_record.powder_factor,
                "predicted_p80": blast_record.predicted_p80,
                "measured_p80": blast_record.measured_p80,
                "safety_status": blast_record.safety_status
            }
            
            logger.info(
                "Interactive visualization data created",
                blast_id=blast_record.id,
                hole_count=len(viz_data["holes"])
            )
            
            return viz_data
            
        except Exception as e:
            logger.error(
                "Failed to create interactive visualization data",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def _extract_hole_data(self, holes: List[Dict], color_by: str) -> Tuple[List, List, List, List]:
        """Extract coordinates and color values from hole data."""
        x_coords = []
        y_coords = []
        color_values = []
        hole_ids = []
        
        for hole in holes:
            coords = hole.get('coordinates', {})
            x_coords.append(coords.get('x', 0))
            y_coords.append(coords.get('y', 0))
            hole_ids.append(hole.get('hole_id', ''))
            
            if color_by == 'charge':
                color_values.append(hole.get('charge_kg', 0))
            elif color_by == 'delay':
                color_values.append(hole.get('delay_ms', 0))
            elif color_by == 'explosive_type':
                # Convert explosive type to numeric for coloring
                explosive_types = list(set(h.get('explosive_type', '') for h in holes))
                color_values.append(explosive_types.index(hole.get('explosive_type', '')))
            else:
                color_values.append(1)  # Default color
        
        return x_coords, y_coords, color_values, hole_ids
    
    def _create_hole_scatter(self, ax, x_coords, y_coords, color_values, color_by):
        """Create scatter plot for holes."""
        cmap = self.color_schemes.get(color_by, 'viridis')
        
        scatter = ax.scatter(
            x_coords, y_coords, c=color_values, cmap=cmap,
            s=60, alpha=0.8, edgecolors='black', linewidth=0.5
        )
        
        return scatter
    
    def _add_hole_labels(self, ax, x_coords, y_coords, hole_ids):
        """Add hole ID labels to the plot."""
        for x, y, hole_id in zip(x_coords, y_coords, hole_ids):
            ax.annotate(hole_id, (x, y), xytext=(3, 3), 
                       textcoords='offset points', fontsize=6, alpha=0.8)
    
    def _add_color_legend(self, fig, scatter, color_by, color_values):
        """Add color legend to the plot."""
        if color_by in ['charge', 'delay']:
            cbar = fig.colorbar(scatter, ax=fig.axes[0], shrink=0.8)
            if color_by == 'charge':
                cbar.set_label('Charge (kg)')
            elif color_by == 'delay':
                cbar.set_label('Delay (ms)')
    
    def _add_scale_bar(self, ax, x_coords, y_coords):
        """Add scale bar to the plot."""
        x_range = max(x_coords) - min(x_coords)
        scale_length = 10 ** int(np.log10(x_range * 0.2))  # 20% of range, rounded
        
        # Position scale bar in bottom left
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        
        scale_x = x_min + 0.05 * (x_max - x_min)
        scale_y = y_min + 0.05 * (y_max - y_min)
        
        # Draw scale bar
        ax.plot([scale_x, scale_x + scale_length], [scale_y, scale_y], 
               'k-', linewidth=3)
        ax.text(scale_x + scale_length/2, scale_y + 0.02 * (y_max - y_min), 
               f'{scale_length:.0f}m', ha='center', va='bottom', fontweight='bold')
    
    def _add_north_arrow(self, ax):
        """Add north arrow to the plot."""
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        
        arrow_x = x_max - 0.05 * (x_max - x_min)
        arrow_y = y_max - 0.05 * (y_max - y_min)
        
        ax.annotate('N', xy=(arrow_x, arrow_y), xytext=(arrow_x, arrow_y - 0.05 * (y_max - y_min)),
                   arrowprops=dict(arrowstyle='->', lw=2, color='black'),
                   fontsize=12, fontweight='bold', ha='center', va='center')
    
    def _format_map_axes(self, ax, blast_record):
        """Format map axes."""
        ax.set_xlabel('X Coordinate (m)')
        ax.set_ylabel('Y Coordinate (m)')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
    
    def _add_map_title(self, ax, blast_record, color_by):
        """Add title to map."""
        title = f'Blast Plan: {blast_record.blast_name}'
        if color_by:
            title += f' (Colored by {color_by.replace("_", " ").title()})'
        ax.set_title(title)
    
    def _calculate_fragmentation_curve(self, frag_data: Dict, sizes: np.ndarray) -> np.ndarray:
        """Calculate fragmentation curve from fragmentation data."""
        # Simplified Rosin-Rammler calculation
        p80 = frag_data.get('p80', 100)
        uniformity = frag_data.get('uniformity_index', 1.25)
        
        # Rosin-Rammler equation: P = 100 * (1 - exp(-(x/xc)^n))
        # Where xc is characteristic size, n is uniformity index
        xc = p80 / ((-np.log(0.2)) ** (1/uniformity))  # Calculate xc from P80
        
        passing = 100 * (1 - np.exp(-(sizes / xc) ** uniformity))
        return passing
    
    def _calculate_measured_fragmentation_curve(self, measurement: Dict, sizes: np.ndarray) -> np.ndarray:
        """Calculate fragmentation curve from measurement data."""
        # Simplified - in practice would use actual measurement data
        measured_p80 = measurement.get('measured_p80', 100)
        
        # Use similar calculation as predicted but with measured P80
        uniformity = 1.25  # Default uniformity
        xc = measured_p80 / ((-np.log(0.2)) ** (1/uniformity))
        
        passing = 100 * (1 - np.exp(-(sizes / xc) ** uniformity))
        return passing
    
    def _add_fragmentation_stats(self, ax, blast_record):
        """Add fragmentation statistics text box."""
        stats_text = []
        
        if blast_record.predicted_p80:
            stats_text.append(f'Predicted P80: {blast_record.predicted_p80:.1f}mm')
        
        if blast_record.measured_p80:
            stats_text.append(f'Measured P80: {blast_record.measured_p80:.1f}mm')
            
            if blast_record.predicted_p80:
                accuracy = blast_record.calculate_fragmentation_accuracy()
                if accuracy is not None:
                    stats_text.append(f'Accuracy: {accuracy:.1f}%')
        
        if stats_text:
            ax.text(0.02, 0.98, '\n'.join(stats_text), transform=ax.transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    def _create_delay_map(self, ax, holes_by_delay):
        """Create delay sequence map."""
        # Color holes by delay sequence
        colors = plt.cm.tab10(np.linspace(0, 1, len(holes_by_delay)))
        
        for i, (delay, holes) in enumerate(sorted(holes_by_delay.items())):
            x_coords = [h.get('coordinates', {}).get('x', 0) for h in holes]
            y_coords = [h.get('coordinates', {}).get('y', 0) for h in holes]
            
            ax.scatter(x_coords, y_coords, c=[colors[i]], s=60, 
                      label=f'Delay {delay}ms', alpha=0.8, edgecolors='black')
        
        ax.set_xlabel('X Coordinate (m)')
        ax.set_ylabel('Y Coordinate (m)')
        ax.set_title('Delay Sequence')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
    
    def _create_timing_chart(self, ax, holes_by_delay):
        """Create timing chart."""
        delays = sorted(holes_by_delay.keys())
        hole_counts = [len(holes_by_delay[delay]) for delay in delays]
        
        ax.bar(delays, hole_counts, alpha=0.7)
        ax.set_xlabel('Delay (ms)')
        ax.set_ylabel('Number of Holes')
        ax.set_title('Holes per Delay')
        ax.grid(True, alpha=0.3)
    
    def _create_charge_flow_chart(self, ax, holes_by_delay):
        """Create charge flow chart."""
        delays = sorted(holes_by_delay.keys())
        charges = []
        
        for delay in delays:
            total_charge = sum(h.get('charge_kg', 0) for h in holes_by_delay[delay])
            charges.append(total_charge)
        
        ax.plot(delays, charges, 'o-', linewidth=2, markersize=6)
        ax.set_xlabel('Delay (ms)')
        ax.set_ylabel('Charge (kg)')
        ax.set_title('Charge per Delay')
        ax.grid(True, alpha=0.3)
    
    def _create_ppv_contours(self, ax, blast_center, blast_record, contour_levels):
        """Create PPV contours."""
        # Simplified circular contours
        total_charge = blast_record.total_explosive
        k, a, b = 1.4, 1/3, 1.6  # Default PPV constants
        
        for ppv_level in contour_levels:
            try:
                radius = ((k * (total_charge ** a)) / ppv_level) ** (1/b)
                
                circle = patches.Circle(blast_center, radius, fill=False, 
                                      edgecolor='red', alpha=0.7, linewidth=1)
                ax.add_patch(circle)
                
                # Add label
                ax.text(blast_center[0] + radius * 0.7, blast_center[1] + radius * 0.7,
                       f'{ppv_level}mm/s', fontsize=8, alpha=0.8)
                
            except (ZeroDivisionError, ValueError):
                continue
    
    def _calculate_blast_center(self, blast_record):
        """Calculate blast center coordinates."""
        if not blast_record.plan_data or 'holes' not in blast_record.plan_data:
            return None
        
        holes = blast_record.plan_data['holes']
        if not holes:
            return None
        
        # Calculate weighted center by charge
        total_charge = 0
        weighted_x = 0
        weighted_y = 0
        
        for hole in holes:
            coords = hole.get('coordinates', {})
            charge = hole.get('charge_kg', 0)
            
            if charge > 0:
                weighted_x += coords.get('x', 0) * charge
                weighted_y += coords.get('y', 0) * charge
                total_charge += charge
        
        if total_charge > 0:
            return (weighted_x / total_charge, weighted_y / total_charge)
        else:
            # Geometric center
            x_coords = [h.get('coordinates', {}).get('x', 0) for h in holes]
            y_coords = [h.get('coordinates', {}).get('y', 0) for h in holes]
            return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))
    
    def _calculate_visualization_boundaries(self, holes):
        """Calculate boundaries for visualization."""
        x_coords = [h.get('coordinates', {}).get('x', 0) for h in holes]
        y_coords = [h.get('coordinates', {}).get('y', 0) for h in holes]
        
        return {
            "x_min": min(x_coords),
            "x_max": max(x_coords),
            "y_min": min(y_coords),
            "y_max": max(y_coords),
            "center_x": sum(x_coords) / len(x_coords),
            "center_y": sum(y_coords) / len(y_coords)
        }
    
    def _prepare_fragmentation_curve_data(self, frag_data):
        """Prepare fragmentation curve data for interactive visualization."""
        sizes = np.logspace(0, 3, 50)  # 1mm to 1000mm
        curve = self._calculate_fragmentation_curve(frag_data, sizes)
        
        return {
            "sizes": sizes.tolist(),
            "passing_percentages": curve.tolist(),
            "p50": frag_data.get('p50'),
            "p80": frag_data.get('p80'),
            "mean_size": frag_data.get('mean_fragment_size'),
            "uniformity_index": frag_data.get('uniformity_index')
        }
    
    def _prepare_ppv_contour_data(self, ppv_data, blast_record):
        """Prepare PPV contour data for interactive visualization."""
        blast_center = self._calculate_blast_center(blast_record)
        contour_levels = [1.0, 2.0, 5.0, 10.0, 20.0]
        
        contours = []
        total_charge = blast_record.total_explosive
        k, a, b = 1.4, 1/3, 1.6
        
        for ppv_level in contour_levels:
            try:
                radius = ((k * (total_charge ** a)) / ppv_level) ** (1/b)
                contours.append({
                    "ppv_level": ppv_level,
                    "radius": radius,
                    "center": blast_center
                })
            except (ZeroDivisionError, ValueError):
                continue
        
        return {
            "contours": contours,
            "receptors": ppv_data.get('receptor_predictions', []),
            "max_ppv": ppv_data.get('max_predicted_ppv', 0)
        }
    
    def _save_figure(self, fig, output_format):
        """Save figure in specified format."""
        buffer = io.BytesIO()
        
        if output_format.lower() == 'png':
            fig.savefig(buffer, format='png', dpi=self.default_dpi, bbox_inches='tight')
            buffer.seek(0)
            return buffer.getvalue()
        
        elif output_format.lower() == 'svg':
            fig.savefig(buffer, format='svg', bbox_inches='tight')
            buffer.seek(0)
            return buffer.getvalue()
        
        elif output_format.lower() == 'base64':
            fig.savefig(buffer, format='png', dpi=self.default_dpi, bbox_inches='tight')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{img_base64}"
        
        else:
            raise ValueError(f"Unsupported output format: {output_format}")