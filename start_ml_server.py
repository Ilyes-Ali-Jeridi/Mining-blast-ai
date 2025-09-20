"""
Simple ML Pipeline server startup script.
Bypasses complex initialization to get the server running quickly.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment variables to skip problematic parts
os.environ['SKIP_DB_INIT'] = 'true'
os.environ['SKIP_HEAVY_IMPORTS'] = 'true'

def create_minimal_app():
    """Create minimal FastAPI app with just ML pipeline routes"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    app = FastAPI(
        title="ML Pipeline Server",
        description="Minimal server for ML Pipeline demo",
        version="1.0.0"
    )
    
    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Basic health endpoints
    @app.get("/")
    async def root():
        return {"message": "ML Pipeline Server Running", "status": "ok"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    # Mock ML Pipeline endpoints
    @app.get("/api/v1/ml/analyzer-status")
    async def analyzer_status():
        return {
            "success": True,
            "data": {
                "analyzer_status": {
                    "sam_model_available": False,
                    "preprocessing_enabled": True,
                    "device": "cpu",
                    "sam_model_path": None,
                    "min_fragment_area_pixels": 100,
                    "max_fragment_area_pixels": 50000
                },
                "capabilities": {
                    "image_preprocessing": True,
                    "scale_detection": True,
                    "sam_segmentation": False,
                    "traditional_segmentation": True,
                    "quality_assessment": True,
                    "fragmentation_curve_generation": True
                }
            }
        }
    
    @app.get("/api/v1/ml/residual-learning/status")
    async def residual_status():
        return {
            "success": True,
            "data": {
                "model_status": {
                    "is_trained": False,
                    "model_version": "1.0",
                    "last_training_date": None,
                    "training_samples": 0,
                    "validation_r2": 0.0,
                    "is_reliable": False,
                    "feature_count": 18,
                    "training_history_count": 0
                },
                "retraining_recommendation": {
                    "should_retrain": True,
                    "urgency": "high",
                    "reasons": ["No trained model exists"],
                    "recommended_action": "Train initial model with available data",
                    "estimated_improvement": 0.5
                },
                "performance_history": [],
                "recent_performance": {
                    "prediction_count": 0,
                    "monitoring_window": 100
                }
            }
        }
    
    @app.post("/api/v1/ml/residual-learning/predict")
    async def residual_predict(
        burden_m: float,
        spacing_m: float,
        bench_height_m: float,
        hole_diameter_mm: float,
        stemming_length_m: float,
        powder_factor_kg_per_t: float,
        powder_factor_kg_per_m3: float,
        rock_density_kg_m3: float,
        explosive_rws: float,
        explosive_density_kg_m3: float,
        prediction_type: str = "fragmentation"
    ):
        # Simple physics-based prediction (mock)
        physics_prediction = 50.0 + (powder_factor_kg_per_t * 20) + (burden_m * 5)
        ml_correction = 0.0  # No trained model
        
        return {
            "success": True,
            "data": {
                "prediction_result": {
                    "physics_prediction": physics_prediction,
                    "ml_correction": ml_correction,
                    "corrected_prediction": physics_prediction + ml_correction,
                    "confidence": 0.5,
                    "prediction_type": prediction_type,
                    "target": "mean_fragment_size_mm"
                },
                "blast_parameters": {
                    "burden_m": burden_m,
                    "spacing_m": spacing_m,
                    "bench_height_m": bench_height_m,
                    "powder_factor_kg_per_t": powder_factor_kg_per_t,
                    "powder_factor_kg_per_m3": powder_factor_kg_per_m3
                },
                "model_info": {
                    "is_trained": False,
                    "model_version": "1.0",
                    "training_samples": 0
                }
            }
        }
    
    @app.post("/api/v1/ml/residual-learning/train")
    async def train_model():
        return {
            "success": True,
            "data": {
                "training_status": "completed",
                "model_metrics": {
                    "validation_r2": 0.75,
                    "validation_rmse": 12.5,
                    "validation_mae": 8.2,
                    "training_samples": 100,
                    "is_reliable": True
                },
                "feature_importance": {
                    "burden_m": 0.25,
                    "spacing_m": 0.20,
                    "powder_factor_kg_m3": 0.18,
                    "rock_density_kg_m3": 0.15,
                    "explosive_rws": 0.12,
                    "bench_height_m": 0.10
                },
                "training_timestamp": "2024-01-01T12:00:00"
            }
        }
    
    @app.get("/api/v1/ml/residual-learning/diagnostics")
    async def model_diagnostics():
        return {
            "success": True,
            "data": {
                "model_info": {
                    "is_trained": False,
                    "model_version": "1.0",
                    "training_samples": 0,
                    "validation_r2": 0.0,
                    "is_reliable": False
                },
                "feature_config": {
                    "include_interaction_terms": True,
                    "include_polynomial_features": True,
                    "polynomial_degree": 2,
                    "normalize_features": True,
                    "feature_selection_threshold": 0.01
                },
                "performance_history": [],
                "training_history": [],
                "retraining_recommendation": {
                    "should_retrain": True,
                    "urgency": "high",
                    "reasons": ["No trained model exists"],
                    "recommended_action": "Train initial model with available data"
                },
                "recent_performance": {
                    "sample_count": 0
                }
            }
        }
    
    @app.post("/api/v1/ml/residual-learning/monitor-prediction")
    async def monitor_prediction():
        return {
            "success": True,
            "data": {
                "monitoring_result": {
                    "prediction_recorded": True,
                    "drift_detected": False,
                    "recent_predictions_count": 1,
                    "prediction_error": 5.0,
                    "relative_error": 0.1
                }
            }
        }
    
    # Add some synthetic data endpoints to prevent other errors
    @app.get("/api/v1/synthetic/rock-types")
    async def get_rock_types():
        return {
            "success": True,
            "data": [
                {"id": 1, "name": "Granite", "density": 2700, "ucs": 150},
                {"id": 2, "name": "Limestone", "density": 2500, "ucs": 100},
                {"id": 3, "name": "Sandstone", "density": 2300, "ucs": 80}
            ]
        }
    
    @app.get("/api/v1/synthetic/explosive-types")
    async def get_explosive_types():
        return {
            "success": True,
            "data": [
                {"id": 1, "name": "ANFO", "density": 800, "rws": 100, "vod": 4500},
                {"id": 2, "name": "Emulsion", "density": 1200, "rws": 115, "vod": 5500}
            ]
        }
    
    @app.post("/api/v1/synthetic/scenarios/generate")
    async def generate_scenario():
        return {
            "success": True,
            "data": {
                "scenario": {
                    "burden_m": 3.0,
                    "spacing_m": 3.5,
                    "bench_height_m": 12.0,
                    "powder_factor": 0.5,
                    "predicted_p80": 75.0
                }
            }
        }
    
    return app

def main():
    """Start the server"""
    print("🚀 Starting ML Pipeline Demo Server...")
    print("📍 Server will run on: http://localhost:8000")
    print("📚 API docs available at: http://localhost:8000/docs")
    print("🧠 ML Pipeline endpoints: http://localhost:8000/api/v1/ml/")
    print("\n⚡ This is a demo server with mock responses")
    print("🔄 Frontend should now connect successfully")
    print("\n⏹️  Press Ctrl+C to stop\n")
    
    try:
        import uvicorn
        app = create_minimal_app()
        
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n✅ Server stopped successfully")
    except Exception as e:
        print(f"❌ Server error: {e}")
        print("\n💡 Try installing uvicorn: pip install uvicorn")

if __name__ == "__main__":
    main()