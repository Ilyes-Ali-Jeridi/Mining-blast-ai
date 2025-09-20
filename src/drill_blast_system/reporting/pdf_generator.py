"""
PDF report generator for blast plans.
Implements requirement 7.1: PDF report generation with maps, hole tables, and safety checklists.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import io
import base64

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, KeepTogether
    )
    from reportlab.graphics.shapes import Drawing, Rect, Circle, Line, String
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.charts.legends import Legend
    from reportlab.graphics.widgets.markers import makeMarker
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

from ..models.blast_record import BlastRecord
from ..core.logging import get_logger

logger = get_logger(__name__)


class PDFReportGenerator:
    """Generates comprehensive PDF reports for blast plans."""
    
    def __init__(self):
        """Initialize PDF report generator."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is required for PDF generation. "
                "Install with: pip install reportlab"
            )
        
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles for reports."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.darkblue,
            borderPadding=5
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.darkgreen
        ))
        
        # Safety warning style
        self.styles.add(ParagraphStyle(
            name='SafetyWarning',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.red,
            backColor=colors.lightyellow,
            borderWidth=2,
            borderColor=colors.red,
            borderPadding=10,
            spaceBefore=10,
            spaceAfter=10
        ))
        
        # Safety pass style
        self.styles.add(ParagraphStyle(
            name='SafetyPass',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.darkgreen,
            backColor=colors.lightgreen,
            borderWidth=1,
            borderColor=colors.darkgreen,
            borderPadding=5
        ))
    
    def generate_blast_plan_report(
        self,
        blast_record: BlastRecord,
        include_safety_report: bool = True,
        include_hole_details: bool = True,
        include_predictions: bool = True,
        include_measurements: bool = False,
        output_path: Optional[Path] = None
    ) -> bytes:
        """
        Generate comprehensive PDF report for blast plan.
        
        Args:
            blast_record: Blast record to generate report for
            include_safety_report: Include safety validation report
            include_hole_details: Include detailed hole information
            include_predictions: Include prediction results
            include_measurements: Include measurement data if available
            output_path: Optional file path to save PDF
            
        Returns:
            PDF content as bytes
        """
        try:
            # Create PDF buffer
            buffer = io.BytesIO()
            
            # Create document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=30*mm,
                bottomMargin=30*mm,
                title=f"Blast Plan Report - {blast_record.blast_name}"
            )
            
            # Build report content
            story = []
            
            # Title page
            story.extend(self._build_title_page(blast_record))
            story.append(PageBreak())
            
            # Executive summary
            story.extend(self._build_executive_summary(blast_record))
            story.append(PageBreak())
            
            # Blast plan overview
            story.extend(self._build_blast_overview(blast_record))
            
            # Safety validation report
            if include_safety_report:
                story.append(PageBreak())
                story.extend(self._build_safety_report(blast_record))
            
            # Hole details table
            if include_hole_details:
                story.append(PageBreak())
                story.extend(self._build_hole_details(blast_record))
            
            # Predictions
            if include_predictions:
                story.append(PageBreak())
                story.extend(self._build_predictions_section(blast_record))
            
            # Measurements (if available)
            if include_measurements and blast_record.measured_results:
                story.append(PageBreak())
                story.extend(self._build_measurements_section(blast_record))
            
            # Sign-off section
            story.append(PageBreak())
            story.extend(self._build_signoff_section(blast_record))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF content
            pdf_content = buffer.getvalue()
            buffer.close()
            
            # Save to file if path provided
            if output_path:
                output_path.write_bytes(pdf_content)
                logger.info(f"PDF report saved to {output_path}")
            
            logger.info(
                "PDF report generated successfully",
                blast_id=blast_record.id,
                blast_name=blast_record.blast_name,
                size_bytes=len(pdf_content)
            )
            
            return pdf_content
            
        except Exception as e:
            logger.error(
                "Failed to generate PDF report",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def _build_title_page(self, blast_record: BlastRecord) -> List:
        """Build title page content."""
        content = []
        
        # Main title
        content.append(Paragraph(
            "BLAST PLAN REPORT",
            self.styles['CustomTitle']
        ))
        content.append(Spacer(1, 20))
        
        # Blast information table
        blast_info = [
            ['Blast Name:', blast_record.blast_name],
            ['Blast ID:', str(blast_record.id)],
            ['Site ID:', str(blast_record.site_id)],
            ['Status:', blast_record.blast_status.value.upper()],
            ['Created:', blast_record.created_at.strftime('%Y-%m-%d %H:%M:%S')],
            ['Report Generated:', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        if blast_record.planned_execution_date:
            blast_info.append(['Planned Execution:', blast_record.planned_execution_date.strftime('%Y-%m-%d')])
        
        if blast_record.blast_operator:
            blast_info.append(['Blast Operator:', blast_record.blast_operator])
        
        info_table = Table(blast_info, colWidths=[3*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(info_table)
        content.append(Spacer(1, 40))
        
        # Safety disclaimer
        disclaimer = """
        <b>SAFETY DISCLAIMER:</b><br/>
        This blast plan has been generated using physics-based models and safety validation systems.
        All safety constraints have been verified according to applicable regulations.
        This plan must be reviewed and approved by a qualified engineer before execution.
        The operator assumes full responsibility for safe execution of this blast plan.
        """
        
        content.append(Paragraph(disclaimer, self.styles['SafetyWarning']))
        
        return content
    
    def _build_executive_summary(self, blast_record: BlastRecord) -> List:
        """Build executive summary section."""
        content = []
        
        content.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        
        # Blast metrics summary
        summary_data = []
        
        if blast_record.plan_data:
            geometry = blast_record.plan_data.get('blast_geometry', {})
            explosives = blast_record.plan_data.get('explosive_summary', {})
            
            summary_data = [
                ['Total Holes:', str(blast_record.total_holes)],
                ['Total Explosive:', f"{blast_record.total_explosive:.1f} kg"],
                ['Blast Area:', f"{geometry.get('blast_area', 0):.0f} m²"],
                ['Rock Tonnage:', f"{geometry.get('rock_tonnage', 0):.0f} tonnes"],
                ['Powder Factor:', f"{explosives.get('powder_factor_kg_t', 0):.2f} kg/t"],
                ['Max Charge/Hole:', f"{explosives.get('max_charge_per_hole', 0):.1f} kg"],
                ['Max Charge/Delay:', f"{explosives.get('max_charge_per_delay', 0):.1f} kg"]
            ]
        
        if summary_data:
            summary_table = Table(summary_data, colWidths=[2.5*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(summary_table)
        
        content.append(Spacer(1, 20))
        
        # Safety status
        safety_status = blast_record.safety_status
        if safety_status == "VALID":
            content.append(Paragraph(
                f"<b>Safety Status:</b> {safety_status} - All safety constraints satisfied",
                self.styles['SafetyPass']
            ))
        else:
            content.append(Paragraph(
                f"<b>Safety Status:</b> {safety_status} - Safety violations detected",
                self.styles['SafetyWarning']
            ))
        
        # Sign-off status
        signoff_status = "SIGNED OFF" if blast_record.is_signed_off else "PENDING SIGN-OFF"
        content.append(Paragraph(f"<b>Engineer Sign-off:</b> {signoff_status}", self.styles['Normal']))
        
        return content
    
    def _build_blast_overview(self, blast_record: BlastRecord) -> List:
        """Build blast plan overview section."""
        content = []
        
        content.append(Paragraph("Blast Plan Overview", self.styles['SectionHeader']))
        
        if blast_record.blast_description:
            content.append(Paragraph(f"<b>Description:</b> {blast_record.blast_description}", self.styles['Normal']))
            content.append(Spacer(1, 12))
        
        # Blast geometry details
        if blast_record.plan_data and 'blast_geometry' in blast_record.plan_data:
            content.append(Paragraph("Blast Geometry", self.styles['SubsectionHeader']))
            
            geometry = blast_record.plan_data['blast_geometry']
            geometry_data = [
                ['Parameter', 'Value', 'Units'],
                ['Total Holes', str(geometry.get('total_holes', 0)), 'holes'],
                ['Total Drilling', f"{geometry.get('total_depth', 0):.1f}", 'meters'],
                ['Blast Area', f"{geometry.get('blast_area', 0):.0f}", 'm²'],
                ['Blast Volume', f"{geometry.get('blast_volume', 0):.0f}", 'm³'],
                ['Rock Tonnage', f"{geometry.get('rock_tonnage', 0):.0f}", 'tonnes'],
                ['Average Burden', f"{geometry.get('average_burden', 0):.1f}", 'meters'],
                ['Average Spacing', f"{geometry.get('average_spacing', 0):.1f}", 'meters'],
                ['Hole Pattern', geometry.get('hole_pattern', 'Unknown'), '']
            ]
            
            geometry_table = Table(geometry_data, colWidths=[2*inch, 1.5*inch, 1*inch])
            geometry_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(geometry_table)
            content.append(Spacer(1, 15))
        
        # Explosive summary
        if blast_record.plan_data and 'explosive_summary' in blast_record.plan_data:
            content.append(Paragraph("Explosive Summary", self.styles['SubsectionHeader']))
            
            explosives = blast_record.plan_data['explosive_summary']
            explosive_data = [
                ['Parameter', 'Value', 'Units'],
                ['Total Explosive', f"{explosives.get('total_explosive', 0):.1f}", 'kg'],
                ['Powder Factor (mass)', f"{explosives.get('powder_factor_kg_t', 0):.2f}", 'kg/tonne'],
                ['Powder Factor (volume)', f"{explosives.get('powder_factor_kg_m3', 0):.2f}", 'kg/m³'],
                ['Max Charge/Hole', f"{explosives.get('max_charge_per_hole', 0):.1f}", 'kg'],
                ['Max Charge/Delay', f"{explosives.get('max_charge_per_delay', 0):.1f}", 'kg']
            ]
            
            if explosives.get('total_cost'):
                explosive_data.append(['Total Cost', f"${explosives['total_cost']:.2f}", 'USD'])
            
            explosive_table = Table(explosive_data, colWidths=[2*inch, 1.5*inch, 1*inch])
            explosive_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(explosive_table)
            content.append(Spacer(1, 15))
        
        # Add blast plan map
        blast_map = self._create_blast_plan_map(blast_record)
        if blast_map:
            content.append(Paragraph("Blast Plan Layout", self.styles['SubsectionHeader']))
            content.append(blast_map)
        
        return content
    
    def _build_safety_report(self, blast_record: BlastRecord) -> List:
        """Build safety validation report section."""
        content = []
        
        content.append(Paragraph("Safety Validation Report", self.styles['SectionHeader']))
        
        if not blast_record.safety_validation:
            content.append(Paragraph("No safety validation data available.", self.styles['Normal']))
            return content
        
        safety_data = blast_record.safety_validation
        
        # Overall status
        is_valid = safety_data.get('is_valid', False)
        status_text = "VALID - All safety constraints satisfied" if is_valid else "INVALID - Safety violations detected"
        status_style = self.styles['SafetyPass'] if is_valid else self.styles['SafetyWarning']
        
        content.append(Paragraph(f"<b>Overall Status:</b> {status_text}", status_style))
        content.append(Spacer(1, 15))
        
        # Safety checks table
        safety_checks = safety_data.get('safety_checks', [])
        if safety_checks:
            content.append(Paragraph("Safety Checks", self.styles['SubsectionHeader']))
            
            check_data = [['Check Name', 'Status', 'Limit', 'Actual', 'Margin', 'Description']]
            
            for check in safety_checks:
                status = check.get('status', 'UNKNOWN')
                status_color = colors.green if status == 'PASS' else colors.red if status == 'FAIL' else colors.orange
                
                check_data.append([
                    check.get('check_name', ''),
                    status,
                    f"{check.get('limit_value', 0):.2f}",
                    f"{check.get('actual_value', 0):.2f}",
                    f"{check.get('safety_margin', 0):.2f}",
                    check.get('description', '')[:50] + ('...' if len(check.get('description', '')) > 50 else '')
                ])
            
            check_table = Table(check_data, colWidths=[1.2*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 1.8*inch])
            check_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(check_table)
            content.append(Spacer(1, 15))
        
        # Violations (if any)
        violations = safety_data.get('violations', [])
        if violations:
            content.append(Paragraph("Safety Violations", self.styles['SubsectionHeader']))
            
            for i, violation in enumerate(violations, 1):
                violation_text = f"""
                <b>Violation {i}:</b> {violation.get('violation_type', 'Unknown')}<br/>
                <b>Severity:</b> {violation.get('severity', 'Unknown')}<br/>
                <b>Description:</b> {violation.get('description', 'No description')}<br/>
                <b>Mitigation:</b> {violation.get('suggested_mitigation', 'No mitigation suggested')}
                """
                content.append(Paragraph(violation_text, self.styles['SafetyWarning']))
                content.append(Spacer(1, 10))
        
        return content
    
    def _build_hole_details(self, blast_record: BlastRecord) -> List:
        """Build hole details table section."""
        content = []
        
        content.append(Paragraph("Drill Hole Details", self.styles['SectionHeader']))
        
        if not blast_record.plan_data or 'holes' not in blast_record.plan_data:
            content.append(Paragraph("No hole data available.", self.styles['Normal']))
            return content
        
        holes = blast_record.plan_data['holes']
        
        # Create hole table
        hole_data = [[
            'Hole ID', 'X (m)', 'Y (m)', 'Z (m)', 'Depth (m)', 
            'Diameter (mm)', 'Charge (kg)', 'Stemming (m)', 'Delay (ms)', 'Explosive'
        ]]
        
        for hole in holes:
            coords = hole.get('coordinates', {})
            hole_data.append([
                hole.get('hole_id', ''),
                f"{coords.get('x', 0):.1f}",
                f"{coords.get('y', 0):.1f}",
                f"{coords.get('z', 0):.1f}",
                f"{hole.get('depth', 0):.1f}",
                f"{hole.get('diameter', 0):.0f}",
                f"{hole.get('charge_kg', 0):.1f}",
                f"{hole.get('stemming_m', 0):.1f}",
                f"{hole.get('delay_ms', 0)}",
                hole.get('explosive_type', '')[:10]  # Truncate long names
            ])
        
        # Split into multiple tables if too many holes
        max_rows_per_table = 25
        
        for i in range(0, len(hole_data), max_rows_per_table):
            table_data = hole_data[0:1] + hole_data[i+1:i+max_rows_per_table+1]  # Include header
            
            hole_table = Table(table_data, colWidths=[
                0.6*inch, 0.5*inch, 0.5*inch, 0.5*inch, 0.6*inch,
                0.7*inch, 0.6*inch, 0.7*inch, 0.6*inch, 0.8*inch
            ])
            
            hole_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(hole_table)
            
            if i + max_rows_per_table < len(hole_data) - 1:
                content.append(PageBreak())
        
        return content
    
    def _build_predictions_section(self, blast_record: BlastRecord) -> List:
        """Build predictions section."""
        content = []
        
        content.append(Paragraph("Prediction Results", self.styles['SectionHeader']))
        
        if not blast_record.predicted_results:
            content.append(Paragraph("No prediction data available.", self.styles['Normal']))
            return content
        
        predictions = blast_record.predicted_results
        
        # Fragmentation predictions
        if 'fragmentation' in predictions:
            content.append(Paragraph("Fragmentation Predictions", self.styles['SubsectionHeader']))
            
            frag = predictions['fragmentation']
            frag_data = [
                ['Parameter', 'Value', 'Units'],
                ['Mean Fragment Size', f"{frag.get('mean_fragment_size', 0):.1f}", 'mm'],
                ['P10', f"{frag.get('p10', 0):.1f}", 'mm'],
                ['P50', f"{frag.get('p50', 0):.1f}", 'mm'],
                ['P80', f"{frag.get('p80', 0):.1f}", 'mm'],
                ['Uniformity Index', f"{frag.get('uniformity_index', 0):.2f}", ''],
                ['Characteristic Size', f"{frag.get('characteristic_size', 0):.1f}", 'mm']
            ]
            
            frag_table = Table(frag_data, colWidths=[2*inch, 1.5*inch, 1*inch])
            frag_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(frag_table)
            content.append(Spacer(1, 15))
            
            # Add fragmentation curve plot
            frag_plot = self._create_fragmentation_curve_plot(frag)
            if frag_plot:
                content.append(frag_plot)
                content.append(Spacer(1, 15))
        
        # PPV predictions
        if 'ppv_predictions' in predictions:
            content.append(Paragraph("PPV Predictions", self.styles['SubsectionHeader']))
            
            ppv_data = predictions['ppv_predictions']
            max_ppv = ppv_data.get('max_predicted_ppv', 0)
            
            content.append(Paragraph(f"<b>Maximum Predicted PPV:</b> {max_ppv:.2f} mm/s", self.styles['Normal']))
            
            # Receptor predictions table
            receptors = ppv_data.get('receptor_predictions', [])
            if receptors:
                receptor_data = [['Receptor', 'Distance (m)', 'Predicted PPV (mm/s)', 'Safety Margin']]
                
                for receptor in receptors:
                    receptor_data.append([
                        receptor.get('receptor_name', ''),
                        f"{receptor.get('distance_to_blast', 0):.0f}",
                        f"{receptor.get('predicted_ppv', 0):.2f}",
                        f"{receptor.get('safety_margin', 0):.2f}"
                    ])
                
                receptor_table = Table(receptor_data, colWidths=[1.5*inch, 1*inch, 1.5*inch, 1*inch])
                receptor_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                content.append(receptor_table)
        
        return content
    
    def _build_measurements_section(self, blast_record: BlastRecord) -> List:
        """Build measurements section (if available)."""
        content = []
        
        content.append(Paragraph("Measurement Results", self.styles['SectionHeader']))
        
        if not blast_record.measured_results:
            content.append(Paragraph("No measurement data available.", self.styles['Normal']))
            return content
        
        measurements = blast_record.measured_results
        
        # Fragmentation measurements
        frag_measurements = measurements.get('fragmentation_measurements', [])
        if frag_measurements:
            content.append(Paragraph("Fragmentation Measurements", self.styles['SubsectionHeader']))
            
            for measurement in frag_measurements:
                measurement_text = f"""
                <b>Measurement ID:</b> {measurement.get('measurement_id', 'Unknown')}<br/>
                <b>Method:</b> {measurement.get('measurement_method', 'Unknown')}<br/>
                <b>Date:</b> {measurement.get('measurement_date', 'Unknown')}<br/>
                <b>Measured P80:</b> {measurement.get('measured_p80', 0):.1f} mm<br/>
                <b>Quality Score:</b> {measurement.get('measurement_quality', 0):.2f}
                """
                content.append(Paragraph(measurement_text, self.styles['Normal']))
                content.append(Spacer(1, 10))
        
        # Performance comparison
        if blast_record.predicted_p80 and blast_record.measured_p80:
            accuracy = blast_record.calculate_fragmentation_accuracy()
            if accuracy is not None:
                content.append(Paragraph("Prediction Accuracy", self.styles['SubsectionHeader']))
                content.append(Paragraph(
                    f"<b>Fragmentation Prediction Error:</b> {accuracy:.1f}%",
                    self.styles['Normal']
                ))
        
        return content
    
    def _build_signoff_section(self, blast_record: BlastRecord) -> List:
        """Build engineer sign-off section."""
        content = []
        
        content.append(Paragraph("Engineer Sign-off", self.styles['SectionHeader']))
        
        if blast_record.engineer_signoff:
            signoff = blast_record.engineer_signoff
            
            signoff_text = f"""
            <b>Engineer Name:</b> {signoff.get('engineer_name', 'Unknown')}<br/>
            <b>Engineer ID:</b> {signoff.get('engineer_id', 'Unknown')}<br/>
            <b>Sign-off Date:</b> {signoff.get('signoff_timestamp', 'Unknown')}<br/>
            <b>Certification:</b> {signoff.get('certification_statement', 'No statement')}<br/>
            """
            
            if signoff.get('review_notes'):
                signoff_text += f"<b>Review Notes:</b> {signoff['review_notes']}<br/>"
            
            content.append(Paragraph(signoff_text, self.styles['SafetyPass']))
        else:
            content.append(Paragraph(
                "<b>WARNING:</b> This blast plan has not been signed off by a qualified engineer. "
                "Engineer approval is required before execution.",
                self.styles['SafetyWarning']
            ))
            
            # Sign-off template
            content.append(Spacer(1, 30))
            content.append(Paragraph("Engineer Sign-off (To be completed)", self.styles['SubsectionHeader']))
            
            signoff_template = """
            Engineer Name: _________________________________<br/><br/>
            Engineer License/ID: ___________________________<br/><br/>
            Date: _________________________________________<br/><br/>
            Signature: ____________________________________<br/><br/>
            
            I certify that I have reviewed this blast plan and confirm that it complies with all
            applicable safety regulations and engineering standards. I approve this plan for execution
            subject to the conditions and recommendations noted above.
            """
            
            content.append(Paragraph(signoff_template, self.styles['Normal']))
        
        return content
    
    def _create_fragmentation_curve_plot(self, fragmentation_data: Dict[str, Any]) -> Optional[Image]:
        """Create fragmentation curve plot for PDF report."""
        try:
            # Extract data
            sizes = fragmentation_data.get('size_distribution', {})
            if not sizes:
                return None
            
            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(6, 4))
            
            # Sort sizes for plotting
            size_values = sorted([float(k) for k in sizes.keys() if k.replace('.', '').isdigit()])
            passing_percentages = [sizes[str(size)] for size in size_values]
            
            # Plot fragmentation curve
            ax.semilogx(size_values, passing_percentages, 'b-', linewidth=2, label='Predicted')
            
            # Mark key percentiles
            p50 = fragmentation_data.get('p50')
            p80 = fragmentation_data.get('p80')
            
            if p50:
                ax.axvline(x=p50, color='red', linestyle='--', alpha=0.7, label=f'P50 ({p50:.1f}mm)')
            if p80:
                ax.axvline(x=p80, color='orange', linestyle='--', alpha=0.7, label=f'P80 ({p80:.1f}mm)')
            
            # Formatting
            ax.set_xlabel('Fragment Size (mm)')
            ax.set_ylabel('Cumulative Passing (%)')
            ax.set_title('Fragmentation Curve')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.set_xlim(1, 1000)
            ax.set_ylim(0, 100)
            
            # Save to bytes
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            plt.close(fig)
            img_buffer.seek(0)
            
            # Create ReportLab image
            img = Image(img_buffer, width=5*inch, height=3.3*inch)
            return img
            
        except Exception as e:
            logger.warning(f"Failed to create fragmentation curve plot: {e}")
            return None
    
    def _create_blast_plan_map(self, blast_record: BlastRecord) -> Optional[Image]:
        """Create 2D blast plan map visualization."""
        try:
            if not blast_record.plan_data or 'holes' not in blast_record.plan_data:
                return None
            
            holes = blast_record.plan_data['holes']
            if not holes:
                return None
            
            # Extract coordinates and charges
            x_coords = []
            y_coords = []
            charges = []
            
            for hole in holes:
                coords = hole.get('coordinates', {})
                if 'x' in coords and 'y' in coords:
                    x_coords.append(coords['x'])
                    y_coords.append(coords['y'])
                    charges.append(hole.get('charge_kg', 0))
            
            if not x_coords:
                return None
            
            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(6, 6))
            
            # Create scatter plot with color-coded charges
            scatter = ax.scatter(x_coords, y_coords, c=charges, cmap='viridis', 
                               s=50, alpha=0.8, edgecolors='black', linewidth=0.5)
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Charge (kg)')
            
            # Add hole labels for small datasets
            if len(holes) <= 50:
                for i, hole in enumerate(holes):
                    coords = hole.get('coordinates', {})
                    if 'x' in coords and 'y' in coords:
                        ax.annotate(hole.get('hole_id', f'H{i+1}'), 
                                  (coords['x'], coords['y']), 
                                  xytext=(5, 5), textcoords='offset points',
                                  fontsize=6, alpha=0.7)
            
            # Formatting
            ax.set_xlabel('X Coordinate (m)')
            ax.set_ylabel('Y Coordinate (m)')
            ax.set_title('Blast Plan Layout')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
            
            # Add scale and orientation
            x_range = max(x_coords) - min(x_coords)
            y_range = max(y_coords) - min(y_coords)
            
            # Add north arrow
            ax.annotate('N', xy=(0.95, 0.95), xycoords='axes fraction',
                       fontsize=12, fontweight='bold', ha='center', va='center')
            ax.annotate('↑', xy=(0.95, 0.90), xycoords='axes fraction',
                       fontsize=16, ha='center', va='center')
            
            # Save to bytes
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            plt.close(fig)
            img_buffer.seek(0)
            
            # Create ReportLab image
            img = Image(img_buffer, width=5*inch, height=5*inch)
            return img
            
        except Exception as e:
            logger.warning(f"Failed to create blast plan map: {e}")
            return None