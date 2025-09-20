"""
Test ML Pipeline components without requiring full server.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_residual_learner():
    """Test the residual learner component"""
    print("=== Testing Residual Learner ===")
    
    try:
        from src.drill_blast_system.ml_pipeline.residual_learner import (
            ResidualLearner, 
            FeatureEngineeringConfig
        )
        from src.drill_blast_system.physics_models import KuzRamModel, PPVModel, BlastParameters
        
        print("✓ Imports successful")
        
        # Create feature config
        feature_config = FeatureEngineeringConfig(
            include_interaction_terms=True,
            include_polynomial_features=False,  # Skip to avoid sklearn dependency
            normalize_features=True
        )
        
        # Create residual learner
        learner = ResidualLearner(feature_config=feature_config)
        print("✓ ResidualLearner created")
        
        # Integrate physics models
        kuz_ram = KuzRamModel(rock_factor_a=7.0)
        ppv_model = PPVModel(k=1.4, a=1/3, b=1.6)
        learner.integrate_physics_models(kuz_ram, ppv_model)
        print("✓ Physics models integrated")
        
        # Test feature extraction
        blast_data = {
            "burden_m": 3.0,
            "spacing_m": 3.5,
            "bench_height_m": 12.0,
            "hole_diameter_mm": 165.0,
            "stemming_length_m": 3.0,
            "powder_factor_kg_per_t": 0.5,
            "powder_factor_kg_m3": 1.35,
            "rock_density_kg_m3": 2700.0,
            "explosive_rws": 100.0,
            "explosive_density_kg_m3": 1200.0,
            "ucs_mpa": 100.0
        }
        
        features = learner.extract_blast_features(blast_data)
        print(f"✓ Feature extraction: {features.shape[1]} features generated")
        
        # Test physics prediction
        blast_params = BlastParameters(
            powder_factor_kg_per_t=0.5,
            powder_factor_kg_per_m3=1.35,
            burden=3.0,
            spacing=3.5,
            bench_height=12.0,
            hole_diameter=165.0,
            stemming_length=3.0,
            rock_density=2700.0,
            explosive_rws=100.0,
            explosive_density=1200.0
        )
        
        result = learner.predict_with_physics_correction(blast_params, "fragmentation")
        print(f"✓ Physics prediction: {result['physics_prediction']:.2f} mm")
        print(f"✓ ML correction: {result['ml_correction']:.2f} mm")
        print(f"✓ Final prediction: {result['corrected_prediction']:.2f} mm")
        
        # Test model info
        info = learner.get_model_info()
        print(f"✓ Model info: trained={info['is_trained']}")
        
        # Test retraining recommendation
        rec = learner.get_retraining_recommendation()
        print(f"✓ Retraining recommendation: {rec.recommended_action}")
        
        print("✓ All residual learner tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error testing residual learner: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fragmentation_analyzer():
    """Test the fragmentation analyzer component"""
    print("\n=== Testing Fragmentation Analyzer ===")
    
    try:
        from src.drill_blast_system.ml_pipeline.fragmentation_analyzer import FragmentationAnalyzer
        
        print("✓ Import successful")
        
        # Create analyzer
        analyzer = FragmentationAnalyzer(
            sam_model_path=None,  # Skip SAM for testing
            device="cpu",
            enable_preprocessing=True
        )
        print("✓ FragmentationAnalyzer created")
        
        # Test analyzer info
        print(f"✓ Preprocessing enabled: {analyzer.enable_preprocessing}")
        print(f"✓ Device: {analyzer.device}")
        
        print("✓ Fragmentation analyzer tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error testing fragmentation analyzer: {e}")
        return False

def test_ml_service():
    """Test the ML pipeline service components"""
    print("\n=== Testing ML Pipeline Service ===")
    
    try:
        # Test data structures
        from src.drill_blast_system.ml_pipeline.data_structures import (
            FragmentationResult, ModelMetrics, QualityAssessment
        )
        print("✓ Data structures imported")
        
        # Test data ingestion
        from src.drill_blast_system.ml_pipeline.data_ingestion import DataIngestionService
        print("✓ Data ingestion service imported")
        
        # Test batch processor
        from src.drill_blast_system.ml_pipeline.batch_processor import BatchProcessor
        print("✓ Batch processor imported")
        
        print("✓ ML pipeline service tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error testing ML pipeline service: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing ML Pipeline Components")
    print("=" * 50)
    
    results = []
    
    # Test components
    results.append(test_residual_learner())
    results.append(test_fragmentation_analyzer())
    results.append(test_ml_service())
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(results)
    total = len(results)
    
    print(f"✓ Passed: {passed}/{total}")
    if passed == total:
        print("🎉 All tests passed! ML Pipeline components are working correctly.")
        print("\nYou can now:")
        print("1. Start the frontend: cd frontend && npm run dev")
        print("2. Start the backend: python run_simple_server.py")
        print("3. Visit http://localhost:3000 and navigate to ML Pipeline")
    else:
        print(f"⚠ {total - passed} tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)