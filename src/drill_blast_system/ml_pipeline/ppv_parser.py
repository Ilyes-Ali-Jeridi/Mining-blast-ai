"""
PPV sensor data parser for extracting peak particle velocity measurements.
Implements requirement 5.2: PPV sensor data parsing and validation.
"""

import csv
import re
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PPVParsingResult:
    """Result from PPV data file parsing"""
    
    # Core PPV measurements
    peak_ppv: float  # mm/s
    dominant_frequency: Optional[float]  # Hz
    duration: Optional[float]  # seconds
    vector_sum: Optional[float]  # mm/s (if 3-component)
    
    # Component data (if available)
    components: Optional[Dict[str, float]]  # vertical, longitudinal, transverse
    
    # Frequency analysis
    frequency_spectrum: Optional[Dict[str, List[float]]]  # frequencies and amplitudes
    
    # Data quality metrics
    data_completeness: float  # 0-1 score
    signal_quality: str  # excellent, good, fair, poor
    interference_detected: bool
    
    # Processing metadata
    sampling_rate: Optional[float]  # Hz
    channels: List[str]  # Channel names
    preprocessing_applied: List[str]  # Applied filters/corrections
    parsing_parameters: Dict[str, Any]
    processing_timestamp: datetime
    processing_time: float  # seconds
    
    # Validation results
    validation_checks: List[Dict[str, Any]]
    
    # Raw data (optional, for debugging)
    raw_time_series: Optional[np.ndarray] = None
    raw_timestamps: Optional[np.ndarray] = None


class PPVDataParser:
    """
    Parser for various PPV sensor data formats.
    
    Supports:
    - CSV files with time series data
    - Text files with tabular data
    - Binary data files (basic support)
    - Multiple sensor formats (Instantel, Geosonics, etc.)
    """
    
    def __init__(self):
        self.supported_formats = {'.csv', '.txt', '.dat', '.log'}
        self.common_delimiters = [',', '\t', ';', ' ']
        self.ppv_column_patterns = [
            r'ppv|velocity|vel',
            r'vertical|vert|v',
            r'longitudinal|long|l', 
            r'transverse|trans|t',
            r'radial|rad|r'
        ]
        self.time_column_patterns = [
            r'time|timestamp|t',
            r'sample|samp|s',
            r'index|idx|i'
        ]
        
        # Processing parameters
        self.min_sampling_rate = 100  # Hz
        self.max_reasonable_ppv = 1000  # mm/s
        self.min_signal_duration = 0.1  # seconds
        self.frequency_analysis_window = 1024  # samples for FFT
    
    def parse_ppv_file(self, file_path: str) -> PPVParsingResult:
        """
        Parse PPV data file and extract measurements.
        
        Args:
            file_path: Path to PPV data file
            
        Returns:
            PPVParsingResult with extracted measurements and quality assessment
        """
        start_time = datetime.utcnow()
        file_path = Path(file_path)
        
        logger.info(f"Parsing PPV file: {file_path.name}")
        
        try:
            # Determine file format and parse
            if file_path.suffix.lower() == '.csv':
                result = self._parse_csv_file(file_path)
            elif file_path.suffix.lower() in {'.txt', '.dat', '.log'}:
                result = self._parse_text_file(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            result.processing_time = processing_time
            result.processing_timestamp = start_time
            
            logger.info(f"PPV parsing completed: peak={result.peak_ppv:.2f}mm/s, "
                       f"quality={result.signal_quality}, duration={processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"PPV parsing failed for {file_path.name}: {e}")
            raise
    
    def _parse_csv_file(self, file_path: Path) -> PPVParsingResult:
        """Parse CSV format PPV data"""
        
        # Try to detect delimiter and structure
        delimiter = self._detect_csv_delimiter(file_path)
        
        # Read CSV data
        try:
            df = pd.read_csv(file_path, delimiter=delimiter, low_memory=False)
        except Exception as e:
            # Try alternative parsing methods
            df = self._parse_csv_alternative(file_path)
        
        # Clean column names
        df.columns = [col.strip().lower() for col in df.columns]
        
        # Identify columns
        time_col, ppv_cols = self._identify_columns(df.columns)
        
        if not ppv_cols:
            raise ValueError("No PPV data columns found in CSV file")
        
        # Extract time series data
        time_data = df[time_col].values if time_col else np.arange(len(df))
        ppv_data = {}
        
        for col_name, col_key in ppv_cols.items():
            ppv_data[col_key] = df[col_name].values
        
        # Process the extracted data
        return self._process_ppv_data(time_data, ppv_data, file_path.name)
    
    def _parse_text_file(self, file_path: Path) -> PPVParsingResult:
        """Parse text format PPV data"""
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Try to detect structure
        lines = content.strip().split('\n')
        
        # Look for header information
        header_info = self._extract_header_info(lines)
        
        # Find data section
        data_start_idx = self._find_data_start(lines)
        data_lines = lines[data_start_idx:]
        
        # Parse data section
        delimiter = self._detect_text_delimiter(data_lines[:10])
        
        # Convert to DataFrame
        data_rows = []
        for line in data_lines:
            if line.strip() and not line.startswith('#'):
                try:
                    row = [float(x.strip()) for x in line.split(delimiter) if x.strip()]
                    if row:  # Only add non-empty rows
                        data_rows.append(row)
                except ValueError:
                    continue  # Skip non-numeric lines
        
        if not data_rows:
            raise ValueError("No numeric data found in text file")
        
        # Create DataFrame
        max_cols = max(len(row) for row in data_rows)
        padded_rows = [row + [np.nan] * (max_cols - len(row)) for row in data_rows]
        
        df = pd.DataFrame(padded_rows)
        
        # Generate column names based on detected structure
        if max_cols >= 4:  # Time + 3 components
            df.columns = ['time', 'vertical', 'longitudinal', 'transverse'] + [f'col_{i}' for i in range(4, max_cols)]
        elif max_cols >= 2:  # Time + PPV
            df.columns = ['time', 'ppv'] + [f'col_{i}' for i in range(2, max_cols)]
        else:
            df.columns = [f'col_{i}' for i in range(max_cols)]
        
        # Identify columns
        time_col, ppv_cols = self._identify_columns(df.columns)
        
        # Extract data
        time_data = df[time_col].values if time_col else np.arange(len(df))
        ppv_data = {}
        
        for col_name, col_key in ppv_cols.items():
            ppv_data[col_key] = df[col_name].values
        
        # Merge header info into parsing parameters
        parsing_params = {
            'file_format': 'text',
            'delimiter': delimiter,
            'header_info': header_info,
            'data_start_line': data_start_idx
        }
        
        # Process the extracted data
        result = self._process_ppv_data(time_data, ppv_data, file_path.name)
        result.parsing_parameters.update(parsing_params)
        
        return result
    
    def _process_ppv_data(
        self, 
        time_data: np.ndarray, 
        ppv_data: Dict[str, np.ndarray], 
        filename: str
    ) -> PPVParsingResult:
        """Process extracted PPV time series data"""
        
        # Clean and validate data
        time_data, ppv_data = self._clean_data(time_data, ppv_data)
        
        # Calculate sampling rate
        sampling_rate = self._calculate_sampling_rate(time_data)
        
        # Calculate peak PPV (vector sum if multiple components)
        peak_ppv, vector_sum, components = self._calculate_peak_ppv(ppv_data)
        
        # Calculate duration
        duration = (time_data[-1] - time_data[0]) if len(time_data) > 1 else 0
        
        # Perform frequency analysis
        dominant_freq, freq_spectrum = self._analyze_frequency(ppv_data, sampling_rate)
        
        # Assess data quality
        quality_metrics = self._assess_data_quality(time_data, ppv_data, sampling_rate)
        
        # Perform validation checks
        validation_checks = self._validate_ppv_data(
            peak_ppv, duration, sampling_rate, quality_metrics
        )
        
        # Determine preprocessing applied
        preprocessing = []
        if quality_metrics['noise_level'] > 0.1:
            preprocessing.append('noise_filtering')
        if quality_metrics['baseline_drift'] > 0.05:
            preprocessing.append('baseline_correction')
        
        return PPVParsingResult(
            peak_ppv=peak_ppv,
            dominant_frequency=dominant_freq,
            duration=duration,
            vector_sum=vector_sum,
            components=components,
            frequency_spectrum=freq_spectrum,
            data_completeness=quality_metrics['completeness'],
            signal_quality=quality_metrics['overall_quality'],
            interference_detected=quality_metrics['interference_detected'],
            sampling_rate=sampling_rate,
            channels=list(ppv_data.keys()),
            preprocessing_applied=preprocessing,
            parsing_parameters={
                'filename': filename,
                'file_format': 'csv' if filename.endswith('.csv') else 'text',
                'original_samples': len(time_data),
                'channels_detected': len(ppv_data)
            },
            processing_timestamp=datetime.utcnow(),
            processing_time=0,  # Will be set by caller
            validation_checks=validation_checks,
            raw_time_series=np.column_stack([time_data] + list(ppv_data.values())),
            raw_timestamps=time_data
        )
    
    def _detect_csv_delimiter(self, file_path: Path) -> str:
        """Detect CSV delimiter"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(1024)
        
        # Count occurrences of common delimiters
        delimiter_counts = {}
        for delimiter in self.common_delimiters:
            delimiter_counts[delimiter] = sample.count(delimiter)
        
        # Return most common delimiter
        return max(delimiter_counts, key=delimiter_counts.get)
    
    def _parse_csv_alternative(self, file_path: Path) -> pd.DataFrame:
        """Alternative CSV parsing for problematic files"""
        
        # Try different encodings and delimiters
        encodings = ['utf-8', 'latin-1', 'cp1252']
        delimiters = [',', '\t', ';', ' ']
        
        for encoding in encodings:
            for delimiter in delimiters:
                try:
                    df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding, 
                                   error_bad_lines=False, warn_bad_lines=False)
                    if len(df.columns) > 1 and len(df) > 10:
                        return df
                except Exception:
                    continue
        
        raise ValueError("Could not parse CSV file with any standard method")
    
    def _identify_columns(self, column_names: List[str]) -> Tuple[Optional[str], Dict[str, str]]:
        """Identify time and PPV columns from column names"""
        
        time_col = None
        ppv_cols = {}
        
        # Find time column
        for col in column_names:
            for pattern in self.time_column_patterns:
                if re.search(pattern, col, re.IGNORECASE):
                    time_col = col
                    break
            if time_col:
                break
        
        # Find PPV columns
        for col in column_names:
            if col == time_col:
                continue
                
            # Check for specific component patterns
            if re.search(r'vertical|vert|v', col, re.IGNORECASE):
                ppv_cols[col] = 'vertical'
            elif re.search(r'longitudinal|long|l', col, re.IGNORECASE):
                ppv_cols[col] = 'longitudinal'
            elif re.search(r'transverse|trans|t', col, re.IGNORECASE):
                ppv_cols[col] = 'transverse'
            elif re.search(r'radial|rad|r', col, re.IGNORECASE):
                ppv_cols[col] = 'radial'
            elif re.search(r'ppv|velocity|vel', col, re.IGNORECASE):
                ppv_cols[col] = 'ppv'
            elif col.replace('_', '').replace('-', '').isdigit():
                # Numeric column names (common in sensor data)
                ppv_cols[col] = f'channel_{col}'
        
        # If no specific PPV columns found, use numeric columns
        if not ppv_cols:
            for col in column_names:
                if col != time_col:
                    try:
                        # Check if column contains numeric data
                        float(col.replace('col_', '').replace('channel_', ''))
                        ppv_cols[col] = f'channel_{col}'
                    except ValueError:
                        pass
        
        return time_col, ppv_cols
    
    def _extract_header_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extract header information from text file"""
        header_info = {}
        
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                # Look for key-value pairs in comments
                if ':' in line:
                    parts = line.split(':', 1)
                    key = parts[0].strip('#/ ').lower()
                    value = parts[1].strip()
                    
                    # Try to convert to appropriate type
                    try:
                        if '.' in value:
                            header_info[key] = float(value)
                        else:
                            header_info[key] = int(value)
                    except ValueError:
                        header_info[key] = value
        
        return header_info
    
    def _find_data_start(self, lines: List[str]) -> int:
        """Find where numeric data starts in text file"""
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            # Check if line contains numeric data
            try:
                parts = line.split()
                if len(parts) >= 2:
                    # Try to convert first few parts to numbers
                    for part in parts[:3]:
                        float(part)
                    return i  # Found numeric data
            except ValueError:
                continue
        
        return 0  # Default to start of file
    
    def _detect_text_delimiter(self, sample_lines: List[str]) -> str:
        """Detect delimiter in text data lines"""
        
        delimiter_counts = {}
        for delimiter in self.common_delimiters:
            count = sum(line.count(delimiter) for line in sample_lines)
            delimiter_counts[delimiter] = count
        
        # Return most common delimiter
        return max(delimiter_counts, key=delimiter_counts.get)
    
    def _clean_data(
        self, 
        time_data: np.ndarray, 
        ppv_data: Dict[str, np.ndarray]
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Clean and validate time series data"""
        
        # Remove NaN values
        valid_indices = ~np.isnan(time_data)
        for channel_data in ppv_data.values():
            valid_indices &= ~np.isnan(channel_data)
        
        time_data = time_data[valid_indices]
        cleaned_ppv_data = {}
        
        for channel, data in ppv_data.items():
            cleaned_data = data[valid_indices]
            
            # Remove outliers (values > 10x median)
            median_val = np.median(np.abs(cleaned_data))
            if median_val > 0:
                outlier_mask = np.abs(cleaned_data) < 10 * median_val
                if np.sum(outlier_mask) > len(cleaned_data) * 0.8:  # Keep if >80% data remains
                    time_data = time_data[outlier_mask]
                    cleaned_data = cleaned_data[outlier_mask]
            
            cleaned_ppv_data[channel] = cleaned_data
        
        return time_data, cleaned_ppv_data
    
    def _calculate_sampling_rate(self, time_data: np.ndarray) -> Optional[float]:
        """Calculate sampling rate from time data"""
        
        if len(time_data) < 2:
            return None
        
        # Calculate time differences
        dt = np.diff(time_data)
        
        # Remove zero or negative differences
        dt = dt[dt > 0]
        
        if len(dt) == 0:
            return None
        
        # Use median time difference for robustness
        median_dt = np.median(dt)
        
        return 1.0 / median_dt if median_dt > 0 else None
    
    def _calculate_peak_ppv(
        self, 
        ppv_data: Dict[str, np.ndarray]
    ) -> Tuple[float, Optional[float], Optional[Dict[str, float]]]:
        """Calculate peak PPV and component information"""
        
        components = {}
        max_values = []
        
        # Calculate peak for each component
        for channel, data in ppv_data.items():
            peak_val = np.max(np.abs(data))
            components[channel] = peak_val
            max_values.append(peak_val)
        
        # Calculate vector sum if multiple components
        if len(components) >= 3:
            # Assume 3-component data: find peak vector sum
            component_arrays = list(ppv_data.values())[:3]
            vector_sums = np.sqrt(sum(arr**2 for arr in component_arrays))
            vector_sum = np.max(vector_sums)
            peak_ppv = vector_sum
        else:
            # Use maximum single component
            peak_ppv = max(max_values) if max_values else 0.0
            vector_sum = None
        
        return peak_ppv, vector_sum, components
    
    def _analyze_frequency(
        self, 
        ppv_data: Dict[str, np.ndarray], 
        sampling_rate: Optional[float]
    ) -> Tuple[Optional[float], Optional[Dict[str, List[float]]]]:
        """Perform frequency analysis on PPV data"""
        
        if not sampling_rate or sampling_rate < self.min_sampling_rate:
            return None, None
        
        # Use first channel for frequency analysis
        first_channel = next(iter(ppv_data.values()))
        
        if len(first_channel) < self.frequency_analysis_window:
            return None, None
        
        # Perform FFT
        try:
            fft_result = np.fft.fft(first_channel[:self.frequency_analysis_window])
            frequencies = np.fft.fftfreq(self.frequency_analysis_window, 1/sampling_rate)
            
            # Take positive frequencies only
            positive_freq_mask = frequencies > 0
            frequencies = frequencies[positive_freq_mask]
            amplitudes = np.abs(fft_result[positive_freq_mask])
            
            # Find dominant frequency
            dominant_freq_idx = np.argmax(amplitudes)
            dominant_frequency = frequencies[dominant_freq_idx]
            
            # Prepare frequency spectrum (limit to reasonable range)
            freq_mask = (frequencies >= 1) & (frequencies <= 100)  # 1-100 Hz
            freq_spectrum = {
                'frequencies': frequencies[freq_mask].tolist(),
                'amplitudes': amplitudes[freq_mask].tolist()
            }
            
            return dominant_frequency, freq_spectrum
            
        except Exception as e:
            logger.warning(f"Frequency analysis failed: {e}")
            return None, None
    
    def _assess_data_quality(
        self, 
        time_data: np.ndarray, 
        ppv_data: Dict[str, np.ndarray], 
        sampling_rate: Optional[float]
    ) -> Dict[str, Any]:
        """Assess quality of PPV data"""
        
        quality_metrics = {
            'completeness': 1.0,
            'noise_level': 0.0,
            'baseline_drift': 0.0,
            'interference_detected': False,
            'overall_quality': 'good'
        }
        
        # Check data completeness
        total_expected_samples = len(time_data)
        actual_samples = sum(len(data) for data in ppv_data.values()) / len(ppv_data)
        quality_metrics['completeness'] = min(1.0, actual_samples / total_expected_samples)
        
        # Assess noise level (using first channel)
        if ppv_data:
            first_channel = next(iter(ppv_data.values()))
            
            # Estimate noise as high-frequency content
            if len(first_channel) > 100:
                # Simple noise estimation using high-pass filtering
                diff_signal = np.diff(first_channel)
                noise_level = np.std(diff_signal) / (np.std(first_channel) + 1e-10)
                quality_metrics['noise_level'] = min(1.0, noise_level)
            
            # Check for baseline drift
            if len(first_channel) > 1000:
                # Estimate baseline drift using low-frequency trend
                window_size = len(first_channel) // 10
                windowed_means = []
                for i in range(0, len(first_channel) - window_size, window_size):
                    windowed_means.append(np.mean(first_channel[i:i+window_size]))
                
                if len(windowed_means) > 2:
                    drift = np.std(windowed_means) / (np.std(first_channel) + 1e-10)
                    quality_metrics['baseline_drift'] = min(1.0, drift)
        
        # Check for interference (sudden spikes or periodic patterns)
        if ppv_data and sampling_rate:
            first_channel = next(iter(ppv_data.values()))
            
            # Look for sudden spikes
            if len(first_channel) > 10:
                median_val = np.median(np.abs(first_channel))
                max_val = np.max(np.abs(first_channel))
                
                if median_val > 0 and max_val > 20 * median_val:
                    quality_metrics['interference_detected'] = True
        
        # Determine overall quality
        completeness = quality_metrics['completeness']
        noise = quality_metrics['noise_level']
        interference = quality_metrics['interference_detected']
        
        if completeness > 0.95 and noise < 0.1 and not interference:
            quality_metrics['overall_quality'] = 'excellent'
        elif completeness > 0.9 and noise < 0.2 and not interference:
            quality_metrics['overall_quality'] = 'good'
        elif completeness > 0.8 and noise < 0.4:
            quality_metrics['overall_quality'] = 'fair'
        else:
            quality_metrics['overall_quality'] = 'poor'
        
        return quality_metrics
    
    def _validate_ppv_data(
        self, 
        peak_ppv: float, 
        duration: float, 
        sampling_rate: Optional[float],
        quality_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate PPV data and create validation checks"""
        
        checks = []
        
        # Check peak PPV range
        if 0 < peak_ppv <= self.max_reasonable_ppv:
            checks.append({
                'check_name': 'peak_ppv_range',
                'status': 'PASS',
                'details': f'Peak PPV {peak_ppv:.2f} mm/s within reasonable range'
            })
        else:
            status = 'FAIL' if peak_ppv > self.max_reasonable_ppv else 'WARNING'
            checks.append({
                'check_name': 'peak_ppv_range',
                'status': status,
                'details': f'Peak PPV {peak_ppv:.2f} mm/s outside expected range (0-{self.max_reasonable_ppv})'
            })
        
        # Check signal duration
        if duration >= self.min_signal_duration:
            checks.append({
                'check_name': 'signal_duration',
                'status': 'PASS',
                'details': f'Signal duration {duration:.2f}s sufficient for analysis'
            })
        else:
            checks.append({
                'check_name': 'signal_duration',
                'status': 'WARNING',
                'details': f'Signal duration {duration:.2f}s may be too short'
            })
        
        # Check sampling rate
        if sampling_rate and sampling_rate >= self.min_sampling_rate:
            checks.append({
                'check_name': 'sampling_rate',
                'status': 'PASS',
                'details': f'Sampling rate {sampling_rate:.1f}Hz adequate for analysis'
            })
        else:
            checks.append({
                'check_name': 'sampling_rate',
                'status': 'WARNING',
                'details': f'Sampling rate {sampling_rate or "unknown"}Hz may be insufficient'
            })
        
        # Check data quality
        if quality_metrics['overall_quality'] in ['excellent', 'good']:
            checks.append({
                'check_name': 'data_quality',
                'status': 'PASS',
                'details': f'Data quality: {quality_metrics["overall_quality"]}'
            })
        else:
            checks.append({
                'check_name': 'data_quality',
                'status': 'WARNING',
                'details': f'Data quality: {quality_metrics["overall_quality"]}'
            })
        
        return checks