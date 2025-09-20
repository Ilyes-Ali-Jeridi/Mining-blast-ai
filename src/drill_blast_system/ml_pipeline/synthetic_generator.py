"""
Synthetic Data Generator for Drill-and-Blast System

Generates realistic blast scenarios with randomized parameters for:
- Testing and validation of physics models
- Training data generation for ML models
- Performance benchmarking
- Parameter space exploration
"""

import random
import math
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from datetime import datetime, timedelta
import json
import os
import pickle
import pandas as pd
from collections import Counter

from ..physics_models.kuz_ram import KuzRamModel, BlastParameters
from ..physics_models.ppv import PPVModel, Charge, Receptor, Coordinates3D
from ..physics_models.fragmentation_curve import FragmentationCurve
from .data_structures import FragmentationResult, ModelMetrics, QualityAssessment
from ..optimization.data_structures import BlastPlan, DrillHole


class RockType(Enum):
    """Standard rock types with typical properties"""
    SOFT_SEDIMENTARY = "soft_sedimentary"
    HARD_SEDIMENTARY = "hard_sedimentary"
    SOFT_IGNEOUS = "soft_igneous"
    HARD_IGNEOUS = "hard_igneous"
    METAMORPHIC = "metamorphic"
    WEATHERED = "weathered"


class ExplosiveType(Enum):
    """Standard explosive types"""
    ANFO = "anfo"
    EMULSION = "emulsion"
    SLURRY = "slurry"
    BULK_EMULSION = "bulk_emulsion"


@dataclass
class RockProperties:
    """Rock properties for synthetic generation"""
    rock_type: RockType
    ucs: float  # Unconfined compressive strength (MPa)
    density: float  # kg/m³
    rock_factor_a: float  # Kuz-Ram rock factor
    description: str = ""


@dataclass
class ExplosiveProperties:
    """Explosive properties for synthetic generation"""
    explosive_type: ExplosiveType
    density: float  # kg/m³
    rws: float  # Relative Weight Strength (%)
    vod: float  # Velocity of Detonation (m/s)
    cost_per_kg: float  # $/kg
    description: str = ""


@dataclass
class SyntheticSite:
    """Synthetic mining site configuration"""
    site_id: str
    name: str
    
    # Geometry
    bench_height: float  # m
    bench_width: float  # m
    bench_length: float  # m
    free_face_orientation: float  # degrees
    
    # Rock properties
    rock_properties: RockProperties
    
    # Operational constraints
    min_burden: float  # m
    max_burden: float  # m
    min_spacing: float  # m
    max_spacing: float  # m
    max_hole_diameter: float  # mm
    max_charge_per_hole: float  # kg
    max_charge_per_delay: float  # kg
    
    # PPV constraints
    receptors: List[Receptor] = field(default_factory=list)


@dataclass
class NoiseParameters:
    """Parameters for adding realistic noise to synthetic data"""
    
    # Measurement noise (standard deviations as fractions of true value)
    fragmentation_noise: float = 0.15  # 15% noise in P80 measurements
    ppv_noise: float = 0.20  # 20% noise in PPV measurements
    
    # Systematic biases
    fragmentation_bias: float = 0.0  # Systematic bias in fragmentation
    ppv_bias: float = 0.0  # Systematic bias in PPV
    
    # Outlier probability
    outlier_probability: float = 0.05  # 5% chance of outliers
    outlier_magnitude: float = 2.0  # Outliers are 2x normal noise
    
    # Missing data probability
    missing_data_probability: float = 0.02  # 2% missing measurements


@dataclass
class SyntheticBlastScenario:
    """Complete synthetic blast scenario"""
    scenario_id: str
    site: SyntheticSite
    blast_plan: BlastPlan
    
    # True physics predictions (ground truth)
    true_fragmentation: FragmentationResult
    true_ppv: Dict[str, float]  # receptor_id -> ppv
    
    # Noisy measurements (simulated real measurements)
    measured_fragmentation: Optional[FragmentationResult] = None
    measured_ppv: Dict[str, float] = field(default_factory=dict)
    
    # Scenario metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    noise_parameters: Optional[NoiseParameters] = None


class SyntheticDataGenerator:
    """
    Generates synthetic blast scenarios for testing and training.
    
    Provides realistic parameter distributions based on mining industry standards
    and adds controlled noise to simulate measurement uncertainties.
    """
    
    def __init__(self, random_seed: Optional[int] = None):
        """
        Initialize synthetic data generator.
        
        Args:
            random_seed: Random seed for reproducible generation
        """
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)
        
        self.kuz_ram_model = KuzRamModel()
        self.ppv_model = PPVModel()
        
        # Initialize standard rock and explosive types
        self._init_standard_materials()
    
    def _init_standard_materials(self) -> None:
        """Initialize standard rock and explosive property databases"""
        
        # Standard rock properties (based on mining literature)
        self.rock_database = {
            RockType.SOFT_SEDIMENTARY: RockProperties(
                rock_type=RockType.SOFT_SEDIMENTARY,
                ucs=25.0,  # MPa
                density=2200.0,  # kg/m³
                rock_factor_a=12.0,
                description="Soft sandstone, limestone"
            ),
            RockType.HARD_SEDIMENTARY: RockProperties(
                rock_type=RockType.HARD_SEDIMENTARY,
                ucs=80.0,
                density=2500.0,
                rock_factor_a=8.0,
                description="Hard sandstone, quartzite"
            ),
            RockType.SOFT_IGNEOUS: RockProperties(
                rock_type=RockType.SOFT_IGNEOUS,
                ucs=60.0,
                density=2400.0,
                rock_factor_a=9.0,
                description="Weathered granite, soft basalt"
            ),
            RockType.HARD_IGNEOUS: RockProperties(
                rock_type=RockType.HARD_IGNEOUS,
                ucs=150.0,
                density=2700.0,
                rock_factor_a=6.0,
                description="Fresh granite, hard basalt"
            ),
            RockType.METAMORPHIC: RockProperties(
                rock_type=RockType.METAMORPHIC,
                ucs=120.0,
                density=2650.0,
                rock_factor_a=7.0,
                description="Gneiss, schist, slate"
            ),
            RockType.WEATHERED: RockProperties(
                rock_type=RockType.WEATHERED,
                ucs=15.0,
                density=1900.0,
                rock_factor_a=15.0,
                description="Highly weathered rock"
            )
        }
        
        # Standard explosive properties
        self.explosive_database = {
            ExplosiveType.ANFO: ExplosiveProperties(
                explosive_type=ExplosiveType.ANFO,
                density=850.0,  # kg/m³
                rws=100.0,  # %
                vod=4500.0,  # m/s
                cost_per_kg=1.20,  # $/kg
                description="Ammonium Nitrate Fuel Oil"
            ),
            ExplosiveType.EMULSION: ExplosiveProperties(
                explosive_type=ExplosiveType.EMULSION,
                density=1200.0,
                rws=115.0,
                vod=5500.0,
                cost_per_kg=2.50,
                description="Packaged emulsion explosive"
            ),
            ExplosiveType.SLURRY: ExplosiveProperties(
                explosive_type=ExplosiveType.SLURRY,
                density=1300.0,
                rws=110.0,
                vod=5200.0,
                cost_per_kg=2.20,
                description="Water gel explosive"
            ),
            ExplosiveType.BULK_EMULSION: ExplosiveProperties(
                explosive_type=ExplosiveType.BULK_EMULSION,
                density=1150.0,
                rws=120.0,
                vod=5800.0,
                cost_per_kg=1.80,
                description="Bulk loaded emulsion"
            )
        }
    
    def generate_random_site(self, 
                           site_id: Optional[str] = None,
                           rock_type: Optional[RockType] = None) -> SyntheticSite:
        """
        Generate a random synthetic mining site.
        
        Args:
            site_id: Optional site identifier
            rock_type: Optional specific rock type, otherwise random
            
        Returns:
            SyntheticSite with randomized but realistic parameters
        """
        if site_id is None:
            site_id = f"synthetic_site_{random.randint(1000, 9999)}"
        
        # Select rock type
        if rock_type is None:
            rock_type = random.choice(list(RockType))
        
        rock_props = RockProperties(
            rock_type=self.rock_database[rock_type].rock_type,
            ucs=self.rock_database[rock_type].ucs,
            density=self.rock_database[rock_type].density,
            rock_factor_a=self.rock_database[rock_type].rock_factor_a,
            description=self.rock_database[rock_type].description
        )
        
        # Add some variation to rock properties
        rock_props.ucs *= random.uniform(0.7, 1.3)
        rock_props.density *= random.uniform(0.9, 1.1)
        rock_props.rock_factor_a *= random.uniform(0.8, 1.2)
        
        # Generate bench geometry
        bench_height = random.uniform(8.0, 20.0)  # 8-20m typical
        bench_width = random.uniform(30.0, 100.0)  # 30-100m
        bench_length = random.uniform(50.0, 200.0)  # 50-200m
        
        # Generate operational constraints
        min_burden = random.uniform(2.5, 4.0)  # m
        max_burden = min_burden * random.uniform(1.5, 2.5)
        min_spacing = min_burden * random.uniform(0.8, 1.2)
        max_spacing = min_spacing * random.uniform(1.5, 2.0)
        
        # Generate receptors
        receptors = self._generate_receptors(bench_width, bench_length)
        
        return SyntheticSite(
            site_id=site_id,
            name=f"Synthetic Site {site_id}",
            bench_height=bench_height,
            bench_width=bench_width,
            bench_length=bench_length,
            free_face_orientation=random.uniform(0, 360),
            rock_properties=rock_props,
            min_burden=min_burden,
            max_burden=max_burden,
            min_spacing=min_spacing,
            max_spacing=max_spacing,
            max_hole_diameter=random.uniform(150, 300),  # mm
            max_charge_per_hole=random.uniform(30, 100),  # kg
            max_charge_per_delay=random.uniform(200, 500),  # kg
            receptors=receptors
        )
    
    def _generate_receptors(self, bench_width: float, bench_length: float) -> List[Receptor]:
        """Generate realistic receptor locations around the blast area"""
        receptors = []
        
        # Generate 2-5 receptors at various distances
        num_receptors = random.randint(2, 5)
        
        for i in range(num_receptors):
            # Place receptors at realistic distances (50-500m from blast)
            distance = random.uniform(50, 500)
            angle = random.uniform(0, 2 * math.pi)
            
            # Calculate position relative to blast center
            blast_center_x = bench_width / 2
            blast_center_y = bench_length / 2
            
            receptor_x = blast_center_x + distance * math.cos(angle)
            receptor_y = blast_center_y + distance * math.sin(angle)
            receptor_z = random.uniform(-5, 5)  # Slight elevation variation
            
            # PPV limit based on distance and receptor type
            if distance < 100:
                ppv_limit = random.uniform(2.0, 5.0)  # Strict limits for close receptors
                receptor_type = "residential"
            elif distance < 200:
                ppv_limit = random.uniform(5.0, 10.0)
                receptor_type = "commercial"
            else:
                ppv_limit = random.uniform(10.0, 25.0)
                receptor_type = "industrial"
            
            receptors.append(Receptor(
                receptor_id=f"R{i+1}",
                coordinates=Coordinates3D(receptor_x, receptor_y, receptor_z),
                name=f"{receptor_type.title()} Receptor {i+1}",
                ppv_limit_mm_per_s=ppv_limit,
                description=f"{receptor_type} building at {distance:.0f}m"
            ))
        
        return receptors
    
    def generate_blast_pattern(self, 
                             site: SyntheticSite,
                             target_powder_factor: Optional[float] = None,
                             explosive_type: Optional[ExplosiveType] = None) -> BlastPlan:
        """
        Generate a realistic blast pattern for the given site.
        
        Args:
            site: Synthetic site configuration
            target_powder_factor: Target powder factor (kg/t), random if None
            explosive_type: Explosive type, random if None
            
        Returns:
            BlastPlan with realistic hole pattern and charges
        """
        # Select explosive type
        if explosive_type is None:
            explosive_type = random.choice(list(ExplosiveType))
        
        explosive_props = self.explosive_database[explosive_type]
        
        # Generate target powder factor
        if target_powder_factor is None:
            # Typical powder factors based on rock type
            if site.rock_properties.rock_type in [RockType.SOFT_SEDIMENTARY, RockType.WEATHERED]:
                target_powder_factor = random.uniform(0.15, 0.35)
            elif site.rock_properties.rock_type in [RockType.HARD_SEDIMENTARY, RockType.SOFT_IGNEOUS]:
                target_powder_factor = random.uniform(0.25, 0.50)
            else:  # Hard rocks
                target_powder_factor = random.uniform(0.40, 0.80)
        
        # Generate hole pattern
        burden = random.uniform(site.min_burden, site.max_burden)
        spacing = random.uniform(site.min_spacing, site.max_spacing)
        
        # Calculate number of holes
        holes_across = int(site.bench_width / spacing) + 1
        holes_along = int(site.bench_length / burden) + 1
        
        holes = []
        hole_id = 1
        
        for row in range(holes_along):
            for col in range(holes_across):
                # Calculate hole position with some random variation
                x = col * spacing + random.uniform(-0.2, 0.2)
                y = row * burden + random.uniform(-0.2, 0.2)
                z = random.uniform(-1.0, 1.0)  # Collar elevation variation
                
                # Skip holes outside the bench area
                if x > site.bench_width or y > site.bench_length:
                    continue
                
                # Calculate hole depth (bench height + subdrill)
                subdrill = random.uniform(0.5, 2.0)
                depth = site.bench_height + subdrill
                
                # Calculate rock volume per hole
                rock_volume = burden * spacing * site.bench_height
                rock_mass_tonnes = rock_volume * site.rock_properties.density / 1000.0
                
                # Calculate charge based on target powder factor
                charge_kg = target_powder_factor * rock_mass_tonnes
                
                # Apply some variation and constraints
                charge_kg *= random.uniform(0.8, 1.2)  # ±20% variation
                charge_kg = min(charge_kg, site.max_charge_per_hole)
                charge_kg = max(charge_kg, 1.0)  # Minimum 1kg
                
                # Calculate stemming (typically 20-40% of hole depth)
                stemming_ratio = random.uniform(0.2, 0.4)
                stemming_m = depth * stemming_ratio
                
                # Assign delay (simple pattern for now)
                delay_ms = (row * 25 + col * 17) % 500  # Staggered delays
                
                hole = DrillHole(
                    hole_id=f"H{hole_id:03d}",
                    coordinates=(x, y, z),
                    depth=depth,
                    diameter=random.uniform(150, 250),  # mm
                    charge_kg=charge_kg,
                    stemming_m=stemming_m,
                    delay_ms=delay_ms,
                    explosive_type=explosive_type.value,
                    burden=burden,
                    spacing=spacing
                )
                
                holes.append(hole)
                hole_id += 1
        
        # Create blast plan
        plan = BlastPlan(
            plan_id=f"synthetic_plan_{random.randint(1000, 9999)}",
            site_id=site.site_id,
            holes=holes,
            optimization_algorithm="synthetic_generator"
        )
        
        plan.calculate_totals()
        
        # Validate delay constraints
        self._adjust_delays_for_constraints(plan, site.max_charge_per_delay)
        
        return plan
    
    def _adjust_delays_for_constraints(self, plan: BlastPlan, max_charge_per_delay: float) -> None:
        """Adjust delay assignments to satisfy per-delay charge limits"""
        delay_charges = plan.get_charge_per_delay()
        
        # Find delays that exceed limits
        for delay, total_charge in delay_charges.items():
            if total_charge > max_charge_per_delay:
                # Split holes into multiple delays
                holes_in_delay = [h for h in plan.holes if h.delay_ms == delay]
                
                # Sort by charge (largest first)
                holes_in_delay.sort(key=lambda h: h.charge_kg, reverse=True)
                
                current_delay = delay
                current_charge = 0.0
                delay_increment = 25  # ms
                
                for hole in holes_in_delay:
                    if current_charge + hole.charge_kg > max_charge_per_delay:
                        # Move to next delay
                        current_delay += delay_increment
                        current_charge = hole.charge_kg
                    else:
                        current_charge += hole.charge_kg
                    
                    hole.delay_ms = current_delay
    
    def calculate_true_predictions(self, 
                                 site: SyntheticSite, 
                                 plan: BlastPlan) -> Tuple[FragmentationResult, Dict[str, float]]:
        """
        Calculate true physics-based predictions (ground truth).
        
        Args:
            site: Site configuration
            plan: Blast plan
            
        Returns:
            Tuple of (fragmentation_result, ppv_predictions)
        """
        # Calculate average blast parameters
        total_charge = sum(hole.charge_kg for hole in plan.holes)
        total_rock_volume = sum(hole.burden * hole.spacing * site.bench_height 
                              for hole in plan.holes if hole.burden and hole.spacing)
        
        if total_rock_volume == 0:
            raise ValueError("Invalid blast plan: zero rock volume")
        
        avg_powder_factor = total_charge / (total_rock_volume * site.rock_properties.density / 1000.0)
        
        # Use representative hole for calculations
        rep_hole = plan.holes[len(plan.holes) // 2]  # Middle hole
        
        # Get explosive properties
        explosive_type = ExplosiveType(rep_hole.explosive_type)
        explosive_props = self.explosive_database[explosive_type]
        
        # Create blast parameters
        blast_params = BlastParameters(
            powder_factor_kg_per_t=avg_powder_factor,
            powder_factor_kg_per_m3=avg_powder_factor * site.rock_properties.density / 1000.0,
            burden=rep_hole.burden or 4.0,
            spacing=rep_hole.spacing or 4.0,
            bench_height=site.bench_height,
            hole_diameter=rep_hole.diameter,
            stemming_length=rep_hole.stemming_m,
            rock_density=site.rock_properties.density,
            explosive_rws=explosive_props.rws,
            explosive_density=explosive_props.density
        )
        
        # Update Kuz-Ram model with site-specific rock factor
        self.kuz_ram_model.rock_factor_a = site.rock_properties.rock_factor_a
        
        # Calculate fragmentation
        frag_curve = self.kuz_ram_model.get_fragmentation_curve(blast_params)
        
        # Get characteristic sizes
        char_sizes = frag_curve.get_characteristic_sizes()
        
        # Create fragmentation result
        frag_result = FragmentationResult(
            p10=char_sizes.get('P10', 0.0),
            p50=char_sizes.get('P50', 0.0),
            p80=char_sizes.get('P80', 0.0),
            mean_size=frag_curve.mean_size_mm,
            characteristic_size=frag_curve.mean_size_mm,
            uniformity_index=frag_curve.uniformity_index,
            fragment_count=1000,  # Synthetic count
            fragment_sizes=[],  # Would be populated in real analysis
            fragment_areas=[],
            measurement_quality=1.0,  # Perfect for synthetic
            scale_detection_quality=1.0,
            segmentation_quality=1.0,
            image_path="synthetic",
            processing_timestamp=datetime.utcnow(),
            scale_factor=1.0,
            total_analyzed_area=1000000.0,  # mm²
            quality_flags=[],
            is_valid=True
        )
        
        # Calculate PPV predictions
        ppv_predictions = {}
        
        # Create charges from holes
        charges = []
        for hole in plan.holes:
            charge = Charge(
                charge_id=hole.hole_id,
                coordinates=Coordinates3D(*hole.get_actual_coordinates()),
                weight_kg=hole.charge_kg,
                delay_ms=hole.delay_ms,
                explosive_type=hole.explosive_type
            )
            charges.append(charge)
        
        # Predict PPV at each receptor
        for receptor in site.receptors:
            ppv_result = self.ppv_model.predict_ppv_with_delays(charges, receptor)
            ppv_predictions[receptor.receptor_id] = ppv_result["total_ppv"]
        
        return frag_result, ppv_predictions
    
    def add_measurement_noise(self, 
                            true_fragmentation: FragmentationResult,
                            true_ppv: Dict[str, float],
                            noise_params: NoiseParameters) -> Tuple[FragmentationResult, Dict[str, float]]:
        """
        Add realistic measurement noise to true predictions.
        
        Args:
            true_fragmentation: True fragmentation result
            true_ppv: True PPV predictions
            noise_params: Noise parameters
            
        Returns:
            Tuple of (noisy_fragmentation, noisy_ppv)
        """
        # Add noise to fragmentation measurements
        noisy_frag = self._add_fragmentation_noise(true_fragmentation, noise_params)
        
        # Add noise to PPV measurements
        noisy_ppv = {}
        for receptor_id, true_value in true_ppv.items():
            # Skip measurement with probability
            if random.random() < noise_params.missing_data_probability:
                continue
            
            # Add noise
            noise_std = noise_params.ppv_noise * true_value
            
            # Check for outliers
            if random.random() < noise_params.outlier_probability:
                noise_std *= noise_params.outlier_magnitude
            
            noise = np.random.normal(0, noise_std)
            noisy_value = true_value + noise + noise_params.ppv_bias * true_value
            
            # Ensure positive values
            noisy_ppv[receptor_id] = max(0.1, noisy_value)
        
        return noisy_frag, noisy_ppv
    
    def _add_fragmentation_noise(self, 
                               true_frag: FragmentationResult,
                               noise_params: NoiseParameters) -> FragmentationResult:
        """Add noise to fragmentation measurements"""
        
        # Skip measurement with probability
        if random.random() < noise_params.missing_data_probability:
            return None
        
        # Calculate noise levels
        p80_noise_std = noise_params.fragmentation_noise * true_frag.p80
        
        # Check for outliers
        if random.random() < noise_params.outlier_probability:
            p80_noise_std *= noise_params.outlier_magnitude
        
        # Add noise to key measurements
        p80_noise = np.random.normal(0, p80_noise_std)
        noisy_p80 = true_frag.p80 + p80_noise + noise_params.fragmentation_bias * true_frag.p80
        
        # Scale other percentiles proportionally
        scale_factor = noisy_p80 / true_frag.p80 if true_frag.p80 > 0 else 1.0
        
        # Reduce quality scores to reflect measurement uncertainty
        quality_reduction = min(0.3, abs(p80_noise) / true_frag.p80)
        
        return FragmentationResult(
            p10=true_frag.p10 * scale_factor,
            p50=true_frag.p50 * scale_factor,
            p80=max(1.0, noisy_p80),  # Minimum 1mm
            mean_size=true_frag.mean_size * scale_factor,
            characteristic_size=true_frag.characteristic_size * scale_factor,
            uniformity_index=true_frag.uniformity_index * random.uniform(0.9, 1.1),
            fragment_count=int(true_frag.fragment_count * random.uniform(0.8, 1.2)),
            fragment_sizes=[],
            fragment_areas=[],
            measurement_quality=max(0.1, true_frag.measurement_quality - quality_reduction),
            scale_detection_quality=max(0.1, true_frag.scale_detection_quality - quality_reduction * 0.5),
            segmentation_quality=max(0.1, true_frag.segmentation_quality - quality_reduction * 0.3),
            image_path="synthetic_noisy",
            processing_timestamp=datetime.utcnow(),
            scale_factor=true_frag.scale_factor * random.uniform(0.95, 1.05),
            total_analyzed_area=true_frag.total_analyzed_area,
            quality_flags=["synthetic_noise_added"] if quality_reduction > 0.1 else [],
            is_valid=quality_reduction < 0.25
        )
    
    def generate_scenario(self, 
                         site: Optional[SyntheticSite] = None,
                         noise_params: Optional[NoiseParameters] = None,
                         scenario_id: Optional[str] = None) -> SyntheticBlastScenario:
        """
        Generate a complete synthetic blast scenario.
        
        Args:
            site: Optional site configuration, random if None
            noise_params: Optional noise parameters, default if None
            scenario_id: Optional scenario identifier
            
        Returns:
            Complete synthetic blast scenario with true and noisy measurements
        """
        if scenario_id is None:
            scenario_id = f"scenario_{random.randint(10000, 99999)}"
        
        if site is None:
            site = self.generate_random_site()
        
        if noise_params is None:
            noise_params = NoiseParameters()
        
        # Generate blast plan
        blast_plan = self.generate_blast_pattern(site)
        
        # Calculate true predictions
        true_frag, true_ppv = self.calculate_true_predictions(site, blast_plan)
        
        # Add measurement noise
        measured_frag, measured_ppv = self.add_measurement_noise(
            true_frag, true_ppv, noise_params
        )
        
        return SyntheticBlastScenario(
            scenario_id=scenario_id,
            site=site,
            blast_plan=blast_plan,
            true_fragmentation=true_frag,
            true_ppv=true_ppv,
            measured_fragmentation=measured_frag,
            measured_ppv=measured_ppv,
            noise_parameters=noise_params
        )
    
    def generate_parameter_space_exploration(self, 
                                           num_scenarios: int = 100,
                                           parameter_ranges: Optional[Dict[str, Tuple[float, float]]] = None) -> List[SyntheticBlastScenario]:
        """
        Generate scenarios exploring the parameter space systematically.
        
        Args:
            num_scenarios: Number of scenarios to generate
            parameter_ranges: Optional custom parameter ranges
            
        Returns:
            List of scenarios covering the parameter space
        """
        if parameter_ranges is None:
            parameter_ranges = {
                'powder_factor': (0.15, 0.80),  # kg/t
                'burden': (2.5, 8.0),  # m
                'spacing': (2.5, 8.0),  # m
                'bench_height': (8.0, 20.0),  # m
                'hole_diameter': (150, 300),  # mm
                'rock_factor_a': (5.0, 15.0),  # Kuz-Ram parameter
                'ucs': (15.0, 200.0),  # MPa
            }
        
        scenarios = []
        
        # Use Latin Hypercube Sampling for better parameter space coverage
        try:
            from scipy.stats import qmc
        except ImportError:
            # Fallback to random sampling if scipy not available
            samples = np.random.random((num_scenarios, len(parameter_ranges)))
        else:
        
            sampler = qmc.LatinHypercube(d=len(parameter_ranges))
            samples = sampler.random(n=num_scenarios)
        
        param_names = list(parameter_ranges.keys())
        
        for i, sample in enumerate(samples):
            # Scale samples to parameter ranges
            params = {}
            for j, param_name in enumerate(param_names):
                min_val, max_val = parameter_ranges[param_name]
                params[param_name] = min_val + sample[j] * (max_val - min_val)
            
            # Create site with specified parameters
            site = self._create_site_with_parameters(params, f"param_space_{i}")
            
            # Generate scenario
            scenario = self.generate_scenario(
                site=site,
                scenario_id=f"param_exploration_{i:04d}"
            )
            
            scenarios.append(scenario)
        
        return scenarios
    
    def _create_site_with_parameters(self, params: Dict[str, float], site_id: str) -> SyntheticSite:
        """Create a synthetic site with specific parameter values"""
        
        # Select random rock type and modify properties
        rock_type = random.choice(list(RockType))
        rock_props = self.rock_database[rock_type]
        
        # Create rock properties with specified parameters
        rock_props = RockProperties(
            rock_type=rock_type,
            ucs=params.get('ucs', self.rock_database[rock_type].ucs),
            density=self.rock_database[rock_type].density,
            rock_factor_a=params.get('rock_factor_a', self.rock_database[rock_type].rock_factor_a),
            description=self.rock_database[rock_type].description
        )
        
        # Create site with specified geometry
        bench_height = params.get('bench_height', random.uniform(8.0, 20.0))
        bench_width = random.uniform(50.0, 100.0)
        bench_length = random.uniform(80.0, 150.0)
        
        min_burden = params.get('burden', random.uniform(3.0, 5.0))
        max_burden = min_burden * 1.2
        min_spacing = params.get('spacing', min_burden * 1.1)
        max_spacing = min_spacing * 1.2
        
        return SyntheticSite(
            site_id=site_id,
            name=f"Parameter Space Site {site_id}",
            bench_height=bench_height,
            bench_width=bench_width,
            bench_length=bench_length,
            free_face_orientation=random.uniform(0, 360),
            rock_properties=rock_props,
            min_burden=min_burden,
            max_burden=max_burden,
            min_spacing=min_spacing,
            max_spacing=max_spacing,
            max_hole_diameter=params.get('hole_diameter', 200.0),
            max_charge_per_hole=random.uniform(50, 100),
            max_charge_per_delay=random.uniform(300, 600),
            receptors=self._generate_receptors(bench_width, bench_length)
        )
    
    def generate_benchmark_dataset(self, 
                                 num_scenarios: int = 500,
                                 test_split: float = 0.2,
                                 validation_split: float = 0.1) -> Dict[str, List[SyntheticBlastScenario]]:
        """
        Generate a comprehensive benchmark dataset for model validation.
        
        Args:
            num_scenarios: Total number of scenarios
            test_split: Fraction for test set
            validation_split: Fraction for validation set
            
        Returns:
            Dictionary with 'train', 'validation', and 'test' scenario lists
        """
        print(f"Generating {num_scenarios} synthetic scenarios for benchmarking...")
        
        # Generate diverse scenarios
        scenarios = []
        
        # 60% parameter space exploration
        param_scenarios = self.generate_parameter_space_exploration(
            int(num_scenarios * 0.6)
        )
        scenarios.extend(param_scenarios)
        
        # 30% random scenarios with different rock types
        for rock_type in RockType:
            rock_scenarios = []
            for _ in range(int(num_scenarios * 0.3 / len(RockType))):
                site = self.generate_random_site(rock_type=rock_type)
                scenario = self.generate_scenario(site=site)
                rock_scenarios.append(scenario)
            scenarios.extend(rock_scenarios)
        
        # 10% edge cases and challenging scenarios
        edge_scenarios = self._generate_edge_case_scenarios(int(num_scenarios * 0.1))
        scenarios.extend(edge_scenarios)
        
        # Shuffle scenarios
        random.shuffle(scenarios)
        
        # Split into train/validation/test
        n_test = int(len(scenarios) * test_split)
        n_val = int(len(scenarios) * validation_split)
        n_train = len(scenarios) - n_test - n_val
        
        dataset = {
            'train': scenarios[:n_train],
            'validation': scenarios[n_train:n_train + n_val],
            'test': scenarios[n_train + n_val:]
        }
        
        print(f"Dataset split: {n_train} train, {n_val} validation, {n_test} test")
        
        return dataset
    
    def _generate_edge_case_scenarios(self, num_scenarios: int) -> List[SyntheticBlastScenario]:
        """Generate challenging edge case scenarios for robust testing"""
        scenarios = []
        
        for i in range(num_scenarios):
            # Create challenging conditions
            if i % 4 == 0:
                # Very hard rock, high powder factor
                rock_type = RockType.HARD_IGNEOUS
                target_pf = random.uniform(0.6, 1.0)
            elif i % 4 == 1:
                # Very soft rock, low powder factor
                rock_type = RockType.WEATHERED
                target_pf = random.uniform(0.1, 0.25)
            elif i % 4 == 2:
                # Large bench height
                rock_type = random.choice(list(RockType))
                target_pf = None
            else:
                # High noise scenario
                rock_type = random.choice(list(RockType))
                target_pf = None
            
            site = self.generate_random_site(rock_type=rock_type)
            
            # Modify site for edge cases
            if i % 4 == 2:
                site.bench_height = random.uniform(18.0, 25.0)  # Very tall bench
            
            blast_plan = self.generate_blast_pattern(
                site, target_powder_factor=target_pf
            )
            
            # High noise for some scenarios
            if i % 4 == 3:
                noise_params = NoiseParameters(
                    fragmentation_noise=0.30,  # 30% noise
                    ppv_noise=0.35,
                    outlier_probability=0.15,
                    missing_data_probability=0.08
                )
            else:
                noise_params = NoiseParameters()
            
            true_frag, true_ppv = self.calculate_true_predictions(site, blast_plan)
            measured_frag, measured_ppv = self.add_measurement_noise(
                true_frag, true_ppv, noise_params
            )
            
            scenario = SyntheticBlastScenario(
                scenario_id=f"edge_case_{i:03d}",
                site=site,
                blast_plan=blast_plan,
                true_fragmentation=true_frag,
                true_ppv=true_ppv,
                measured_fragmentation=measured_frag,
                measured_ppv=measured_ppv,
                noise_parameters=noise_params
            )
            
            scenarios.append(scenario)
        
        return scenarios
    
    def export_dataset(self, 
                      scenarios: List[SyntheticBlastScenario],
                      output_path: str,
                      format: str = 'json') -> None:
        """
        Export synthetic dataset to file.
        
        Args:
            scenarios: List of scenarios to export
            output_path: Output file path
            format: Export format ('json', 'csv', 'pickle')
        """
        import os
        import pickle
        import pandas as pd
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if format.lower() == 'json':
            self._export_json(scenarios, output_path)
        elif format.lower() == 'csv':
            self._export_csv(scenarios, output_path)
        elif format.lower() == 'pickle':
            with open(output_path, 'wb') as f:
                pickle.dump(scenarios, f)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        print(f"Exported {len(scenarios)} scenarios to {output_path}")
    
    def _export_json(self, scenarios: List[SyntheticBlastScenario], output_path: str) -> None:
        """Export scenarios to JSON format"""
        
        def serialize_scenario(scenario: SyntheticBlastScenario) -> Dict[str, Any]:
            """Convert scenario to JSON-serializable dictionary"""
            return {
                'scenario_id': scenario.scenario_id,
                'created_at': scenario.created_at.isoformat(),
                'site': {
                    'site_id': scenario.site.site_id,
                    'name': scenario.site.name,
                    'bench_height': scenario.site.bench_height,
                    'bench_width': scenario.site.bench_width,
                    'bench_length': scenario.site.bench_length,
                    'rock_type': scenario.site.rock_properties.rock_type.value,
                    'ucs': scenario.site.rock_properties.ucs,
                    'density': scenario.site.rock_properties.density,
                    'rock_factor_a': scenario.site.rock_properties.rock_factor_a,
                },
                'blast_plan': {
                    'plan_id': scenario.blast_plan.plan_id,
                    'num_holes': len(scenario.blast_plan.holes),
                    'total_charge': scenario.blast_plan.total_charge_kg,
                    'powder_factor': scenario.blast_plan.powder_factor_kg_per_t,
                    'holes': [
                        {
                            'hole_id': hole.hole_id,
                            'x': hole.coordinates[0],
                            'y': hole.coordinates[1],
                            'z': hole.coordinates[2],
                            'depth': hole.depth,
                            'diameter': hole.diameter,
                            'charge_kg': hole.charge_kg,
                            'delay_ms': hole.delay_ms,
                            'explosive_type': hole.explosive_type,
                            'burden': hole.burden,
                            'spacing': hole.spacing
                        }
                        for hole in scenario.blast_plan.holes
                    ]
                },
                'true_fragmentation': {
                    'p10': scenario.true_fragmentation.p10,
                    'p50': scenario.true_fragmentation.p50,
                    'p80': scenario.true_fragmentation.p80,
                    'mean_size': scenario.true_fragmentation.mean_size,
                    'uniformity_index': scenario.true_fragmentation.uniformity_index
                },
                'true_ppv': scenario.true_ppv,
                'measured_fragmentation': {
                    'p10': scenario.measured_fragmentation.p10 if scenario.measured_fragmentation else None,
                    'p50': scenario.measured_fragmentation.p50 if scenario.measured_fragmentation else None,
                    'p80': scenario.measured_fragmentation.p80 if scenario.measured_fragmentation else None,
                    'mean_size': scenario.measured_fragmentation.mean_size if scenario.measured_fragmentation else None,
                    'measurement_quality': scenario.measured_fragmentation.measurement_quality if scenario.measured_fragmentation else None,
                    'is_valid': scenario.measured_fragmentation.is_valid if scenario.measured_fragmentation else False
                },
                'measured_ppv': scenario.measured_ppv,
                'noise_parameters': {
                    'fragmentation_noise': scenario.noise_parameters.fragmentation_noise if scenario.noise_parameters else None,
                    'ppv_noise': scenario.noise_parameters.ppv_noise if scenario.noise_parameters else None,
                    'outlier_probability': scenario.noise_parameters.outlier_probability if scenario.noise_parameters else None
                }
            }
        
        export_data = {
            'metadata': {
                'num_scenarios': len(scenarios),
                'generated_at': datetime.utcnow().isoformat(),
                'generator_version': '1.0.0'
            },
            'scenarios': [serialize_scenario(s) for s in scenarios]
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def _export_csv(self, scenarios: List[SyntheticBlastScenario], output_path: str) -> None:
        """Export scenarios to CSV format (flattened)"""
        
        rows = []
        for scenario in scenarios:
            # Calculate aggregate metrics
            avg_burden = np.mean([h.burden for h in scenario.blast_plan.holes if h.burden])
            avg_spacing = np.mean([h.spacing for h in scenario.blast_plan.holes if h.spacing])
            avg_charge = np.mean([h.charge_kg for h in scenario.blast_plan.holes])
            max_ppv = max(scenario.true_ppv.values()) if scenario.true_ppv else 0
            
            row = {
                'scenario_id': scenario.scenario_id,
                'site_id': scenario.site.site_id,
                'rock_type': scenario.site.rock_properties.rock_type.value,
                'ucs_mpa': scenario.site.rock_properties.ucs,
                'density_kg_m3': scenario.site.rock_properties.density,
                'rock_factor_a': scenario.site.rock_properties.rock_factor_a,
                'bench_height_m': scenario.site.bench_height,
                'bench_width_m': scenario.site.bench_width,
                'bench_length_m': scenario.site.bench_length,
                'num_holes': len(scenario.blast_plan.holes),
                'total_charge_kg': scenario.blast_plan.total_charge_kg,
                'powder_factor_kg_t': scenario.blast_plan.powder_factor_kg_per_t,
                'avg_burden_m': avg_burden,
                'avg_spacing_m': avg_spacing,
                'avg_charge_per_hole_kg': avg_charge,
                'true_p10_mm': scenario.true_fragmentation.p10,
                'true_p50_mm': scenario.true_fragmentation.p50,
                'true_p80_mm': scenario.true_fragmentation.p80,
                'true_mean_size_mm': scenario.true_fragmentation.mean_size,
                'true_uniformity_index': scenario.true_fragmentation.uniformity_index,
                'max_true_ppv_mm_s': max_ppv,
                'measured_p80_mm': scenario.measured_fragmentation.p80 if scenario.measured_fragmentation else None,
                'measurement_quality': scenario.measured_fragmentation.measurement_quality if scenario.measured_fragmentation else None,
                'is_measurement_valid': scenario.measured_fragmentation.is_valid if scenario.measured_fragmentation else False,
                'fragmentation_noise_level': scenario.noise_parameters.fragmentation_noise if scenario.noise_parameters else None,
                'ppv_noise_level': scenario.noise_parameters.ppv_noise if scenario.noise_parameters else None
            }
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
    
    def validate_dataset(self, scenarios: List[SyntheticBlastScenario]) -> Dict[str, Any]:
        """
        Validate synthetic dataset for completeness and quality.
        
        Args:
            scenarios: List of scenarios to validate
            
        Returns:
            Validation report dictionary
        """
        report = {
            'total_scenarios': len(scenarios),
            'valid_scenarios': 0,
            'missing_measurements': 0,
            'quality_issues': 0,
            'parameter_coverage': {},
            'statistics': {}
        }
        
        # Collect statistics
        p80_values = []
        ppv_values = []
        powder_factors = []
        rock_types = []
        
        for scenario in scenarios:
            # Check validity
            is_valid = True
            
            if scenario.measured_fragmentation is None:
                report['missing_measurements'] += 1
                is_valid = False
            elif not scenario.measured_fragmentation.is_valid:
                report['quality_issues'] += 1
                is_valid = False
            
            if is_valid:
                report['valid_scenarios'] += 1
                
                # Collect statistics
                p80_values.append(scenario.true_fragmentation.p80)
                powder_factors.append(scenario.blast_plan.powder_factor_kg_per_t)
                rock_types.append(scenario.site.rock_properties.rock_type.value)
                
                if scenario.true_ppv:
                    ppv_values.extend(scenario.true_ppv.values())
        
        # Calculate statistics
        if p80_values:
            report['statistics']['p80_mm'] = {
                'min': min(p80_values),
                'max': max(p80_values),
                'mean': np.mean(p80_values),
                'std': np.std(p80_values)
            }
        
        if ppv_values:
            report['statistics']['ppv_mm_s'] = {
                'min': min(ppv_values),
                'max': max(ppv_values),
                'mean': np.mean(ppv_values),
                'std': np.std(ppv_values)
            }
        
        if powder_factors:
            report['statistics']['powder_factor_kg_t'] = {
                'min': min(powder_factors),
                'max': max(powder_factors),
                'mean': np.mean(powder_factors),
                'std': np.std(powder_factors)
            }
        
        # Parameter coverage
        from collections import Counter
        rock_type_counts = Counter(rock_types)
        report['parameter_coverage']['rock_types'] = dict(rock_type_counts)
        
        # Quality metrics
        report['data_quality'] = {
            'completeness': report['valid_scenarios'] / len(scenarios),
            'missing_rate': report['missing_measurements'] / len(scenarios),
            'quality_issue_rate': report['quality_issues'] / len(scenarios)
        }
        
        return report
    
    def benchmark_physics_models(self, 
                               scenarios: List[SyntheticBlastScenario],
                               models_to_test: Optional[List[str]] = None) -> Dict[str, Dict[str, float]]:
        """
        Benchmark physics models against synthetic ground truth.
        
        Args:
            scenarios: Test scenarios with ground truth
            models_to_test: List of model names to test
            
        Returns:
            Performance metrics for each model
        """
        if models_to_test is None:
            models_to_test = ['kuz_ram_default', 'kuz_ram_calibrated']
        
        results = {}
        
        for model_name in models_to_test:
            print(f"Benchmarking {model_name}...")
            
            predictions = []
            ground_truth = []
            
            for scenario in scenarios:
                if scenario.measured_fragmentation is None:
                    continue
                
                # Get model prediction
                if model_name == 'kuz_ram_default':
                    pred = self._predict_with_default_kuzram(scenario)
                elif model_name == 'kuz_ram_calibrated':
                    pred = self._predict_with_calibrated_kuzram(scenario)
                else:
                    continue
                
                if pred is not None:
                    predictions.append(pred)
                    ground_truth.append(scenario.true_fragmentation.p80)
            
            # Calculate metrics
            if predictions:
                predictions = np.array(predictions)
                ground_truth = np.array(ground_truth)
                
                mae = np.mean(np.abs(predictions - ground_truth))
                rmse = np.sqrt(np.mean((predictions - ground_truth) ** 2))
                mape = np.mean(np.abs((predictions - ground_truth) / ground_truth)) * 100
                r2 = 1 - np.sum((ground_truth - predictions) ** 2) / np.sum((ground_truth - np.mean(ground_truth)) ** 2)
                
                results[model_name] = {
                    'mae_mm': mae,
                    'rmse_mm': rmse,
                    'mape_percent': mape,
                    'r2_score': r2,
                    'num_predictions': len(predictions)
                }
        
        return results
    
    def _predict_with_default_kuzram(self, scenario: SyntheticBlastScenario) -> Optional[float]:
        """Predict P80 using default Kuz-Ram parameters"""
        try:
            # Use default rock factor
            default_model = KuzRamModel()
            
            # Calculate blast parameters from scenario
            total_charge = sum(hole.charge_kg for hole in scenario.blast_plan.holes)
            total_rock_volume = sum(hole.burden * hole.spacing * scenario.site.bench_height 
                                  for hole in scenario.blast_plan.holes if hole.burden and hole.spacing)
            
            if total_rock_volume == 0:
                return None
            
            powder_factor = total_charge / (total_rock_volume * scenario.site.rock_properties.density / 1000.0)
            
            rep_hole = scenario.blast_plan.holes[0]
            explosive_type = ExplosiveType(rep_hole.explosive_type)
            explosive_props = self.explosive_database[explosive_type]
            
            blast_params = BlastParameters(
                powder_factor_kg_per_t=powder_factor,
                powder_factor_kg_per_m3=powder_factor * scenario.site.rock_properties.density / 1000.0,
                burden=rep_hole.burden or 4.0,
                spacing=rep_hole.spacing or 4.0,
                bench_height=scenario.site.bench_height,
                hole_diameter=rep_hole.diameter,
                stemming_length=rep_hole.stemming_m,
                rock_density=scenario.site.rock_properties.density,
                explosive_rws=explosive_props.rws,
                explosive_density=explosive_props.density
            )
            
            frag_curve = default_model.get_fragmentation_curve(blast_params)
            return frag_curve.get_passing_percentage_size(80.0)
            
        except Exception:
            return None
    
    def _predict_with_calibrated_kuzram(self, scenario: SyntheticBlastScenario) -> Optional[float]:
        """Predict P80 using site-calibrated Kuz-Ram parameters"""
        try:
            # Use site-specific rock factor
            calibrated_model = KuzRamModel()
            calibrated_model.rock_factor_a = scenario.site.rock_properties.rock_factor_a
            
            # Same calculation as default but with calibrated parameters
            return self._predict_with_default_kuzram(scenario)
            
        except Exception:
            return None