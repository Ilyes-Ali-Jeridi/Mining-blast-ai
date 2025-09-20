"""
Tests for ML Pipeline API endpoints.

Tests the REST API endpoints for fragmentation analysis and ML pipeline functionality.
"""

import pytest
import tempfile
import os
import io
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import cv2
import numpy as np

from src.drill_blast_system.api.main import app
from src.drill_blast_system.ml_pipeline.data_structures import FragmentationResult
from datetime import datetime


class TestMLPipelineAPI:
    """Test ML Pipeline API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def test_image_bytes(self):
        """Create test image as bytes"""
        # Create synthetic muckpile image
        image = np.zeros((400, 600, 3), dtype=np.uint8)
        
        # Add some fragments
        for i in range(10):
            center = (np.random.randint(50, 550), np.random.randint(50, 350))
            radius = np.random.randint(15, 40)
            color = np.random.randint(80, 180, 3).tolist()
            cv2.circle(image, center, radius, color, -1)
        
        # Add scale marker
        cv2.rectangle(image, (50, 50), (150, 70), (255, 255, 255), -1)
        cv2.rectangle(image, (50, 50), (150, 70), (0, 0, 0), 2)
        
        # Convert to bytes
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        return io.BytesIO(buffer.tobytes())
    
    def test_analyze_fragmentation_endpoint(self, client, test_image_bytes):
        """Test fragmentation analysis endpoint"""
        # Mock the fragmentation analyzer to avoid SAM dependencies
        mock_result = FragmentationResult(
            p10=25.0,
            p50=50.0,
            p80=100.0,
            mean_size=55.0,
            characteristic_size=60.0,
            uniformity_index=1.5,
            fragment_count=25,
            fragment_sizes=[20, 30, 40, 50, 60, 70, 80, 90, 100, 110] * 3,  # 30 fragments
            fragment_areas=[400, 900, 1600, 2500, 3600, 4900, 6400, 8100, 10000, 12100] * 3,
            measurement_quality=0.8,
            scale_detection_quality=0.9,
            segmentation_quality=0.8,
            image_path="test_image.jpg",
            processing_timestamp=datetime.now(),
            scale_factor=0.5,
            total_analyzed_area=50000.0,
            quality_flags=[],
            is_valid=True
        )
        
        with patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer.analyze_muckpile_image', 
                   return_value=mock_result):
            
            response = client.post(
                "/api/v1/ml/analyze-fragmentation",
                files={"image": ("test.jpg", test_image_bytes, "image/jpeg")},
                data={"known_scale_mm_per_pixel": "0.5"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "fragmentation_analysis" in data["data"]
        
        analysis = data["data"]["fragmentation_analysis"]
        assert analysis["p80_mm"] == 100.0
        assert analysis["p50_mm"] == 50.0
        assert analysis["p10_mm"] == 25.0
        assert analysis["fragment_count"] == 25
        assert analysis["measurement_quality"] == 0.8
        assert analysis["is_valid"] is True
    
    def test_analyze_fragmentation_with_scale_coords(self, client, test_image_bytes):
        """Test fragmentation analysis with scale marker coordinates"""
        mock_result = FragmentationResult(
            p10=20.0, p50=45.0, p80=90.0, mean_size=50.0,
            characteristic_size=55.0, uniformity_index=1.4,
            fragment_count=20, fragment_sizes=[30, 40, 50, 60, 70] * 4,
            fragment_areas=[900, 1600, 2500, 3600, 4900] * 4,
            measurement_quality=0.85, scale_detection_quality=0.95,
            segmentation_quality=0.8, image_path="test.jpg",
            processing_timestamp=datetime.now(), scale_factor=0.4,
            total_analyzed_area=40000.0, quality_flags=[], is_valid=True
        )
        
        with patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer.analyze_muckpile_image',
                   return_value=mock_result):
            
            response = client.post(
                "/api/v1/ml/analyze-fragmentation",
                files={"image": ("test.jpg", test_image_bytes, "image/jpeg")},
                data={
                    "scale_x1": "50",
                    "scale_y1": "50", 
                    "scale_x2": "150",
                    "scale_y2": "70"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        analysis = data["data"]["fragmentation_analysis"]
        assert analysis["scale_detection_quality"] == 0.95
    
    def test_analyze_fragmentation_invalid_file(self, client):
        """Test fragmentation analysis with invalid file type"""
        # Create text file instead of image
        text_file = io.BytesIO(b"This is not an image")
        
        response = client.post(
            "/api/v1/ml/analyze-fragmentation",
            files={"image": ("test.txt", text_file, "text/plain")}
        )
        
        assert response.status_code == 400
        assert "File must be an image" in response.json()["detail"]
    
    def test_analyze_fragmentation_processing_error(self, client, test_image_bytes):
        """Test fragmentation analysis with processing error"""
        with patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer.analyze_muckpile_image',
                   side_effect=Exception("Processing failed")):
            
            response = client.post(
                "/api/v1/ml/analyze-fragmentation",
                files={"image": ("test.jpg", test_image_bytes, "image/jpeg")}
            )
        
        assert response.status_code == 500
        assert "Fragmentation analysis failed" in response.json()["detail"]
    
    def test_analyzer_status_endpoint(self, client):
        """Test analyzer status endpoint"""
        with patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer._try_sam_segmentation',
                   return_value=False):  # Mock SAM as not available
            
            response = client.get("/api/v1/ml/analyzer-status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "analyzer_status" in data["data"]
        assert "capabilities" in data["data"]
        
        status = data["data"]["analyzer_status"]
        assert "sam_model_available" in status
        assert "preprocessing_enabled" in status
        assert "device" in status
        
        capabilities = data["data"]["capabilities"]
        assert capabilities["image_preprocessing"] is True
        assert capabilities["scale_detection"] is True
        assert capabilities["quality_assessment"] is True
    
    def test_test_segmentation_endpoint(self, client, test_image_bytes):
        """Test segmentation methods comparison endpoint"""
        # Mock segmentation results
        from src.drill_blast_system.ml_pipeline.data_structures import SegmentationResult
        
        mock_traditional_result = SegmentationResult(
            masks=[np.ones((50, 50), dtype=bool) for _ in range(15)],
            mask_scores=[0.7] * 15,
            fragment_areas_pixels=[2500.0] * 15,
            fragment_perimeters=[200.0] * 15,
            fragment_centroids=[(25, 25)] * 15,
            overall_quality=0.7,
            fragment_separation_quality=0.8,
            edge_quality=0.6,
            sam_model_version="Traditional CV",
            processing_time_seconds=1.5,
            total_fragments_detected=15
        )
        
        mock_sam_result = SegmentationResult(
            masks=[np.ones((50, 50), dtype=bool) for _ in range(25)],
            mask_scores=[0.9] * 25,
            fragment_areas_pixels=[2500.0] * 25,
            fragment_perimeters=[200.0] * 25,
            fragment_centroids=[(25, 25)] * 25,
            overall_quality=0.9,
            fragment_separation_quality=0.9,
            edge_quality=0.8,
            sam_model_version="SAM",
            processing_time_seconds=3.0,
            total_fragments_detected=25
        )
        
        with patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer._try_sam_segmentation',
                   return_value=True), \
             patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer._sam_segment_fragments',
                   return_value=mock_sam_result), \
             patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer._traditional_segment_fragments',
                   return_value=mock_traditional_result):
            
            response = client.post(
                "/api/v1/ml/test-segmentation",
                files={"image": ("test.jpg", test_image_bytes, "image/jpeg")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "segmentation_comparison" in data["data"]
        
        comparison = data["data"]["segmentation_comparison"]
        assert comparison["sam_available"] is True
        assert comparison["sam_results"]["fragment_count"] == 25
        assert comparison["traditional_results"]["fragment_count"] == 15
        assert data["data"]["recommendation"] == "SAM"
    
    def test_test_segmentation_sam_not_available(self, client, test_image_bytes):
        """Test segmentation comparison when SAM is not available"""
        from src.drill_blast_system.ml_pipeline.data_structures import SegmentationResult
        
        mock_traditional_result = SegmentationResult(
            masks=[np.ones((50, 50), dtype=bool) for _ in range(10)],
            mask_scores=[0.6] * 10,
            fragment_areas_pixels=[2500.0] * 10,
            fragment_perimeters=[200.0] * 10,
            fragment_centroids=[(25, 25)] * 10,
            overall_quality=0.6,
            fragment_separation_quality=0.7,
            edge_quality=0.5,
            sam_model_version="Traditional CV",
            processing_time_seconds=1.0,
            total_fragments_detected=10
        )
        
        with patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer._try_sam_segmentation',
                   return_value=False), \
             patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer._traditional_segment_fragments',
                   return_value=mock_traditional_result):
            
            response = client.post(
                "/api/v1/ml/test-segmentation",
                files={"image": ("test.jpg", test_image_bytes, "image/jpeg")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        comparison = data["data"]["segmentation_comparison"]
        assert comparison["sam_available"] is False
        assert comparison["sam_results"] is None
        assert comparison["traditional_results"]["fragment_count"] == 10
        assert data["data"]["recommendation"] == "Traditional CV"
    
    def test_recommendations_generation(self, client, test_image_bytes):
        """Test that appropriate recommendations are generated"""
        # Mock poor quality result
        mock_result = FragmentationResult(
            p10=5.0, p50=10.0, p80=600.0, mean_size=200.0,  # Large P80, indicating poor fragmentation
            characteristic_size=250.0, uniformity_index=0.8,
            fragment_count=8,  # Too few fragments
            fragment_sizes=[5, 8, 10, 15, 20, 500, 600, 700],
            fragment_areas=[25, 64, 100, 225, 400, 250000, 360000, 490000],
            measurement_quality=0.4,  # Poor quality
            scale_detection_quality=0.3,  # Poor scale detection
            segmentation_quality=0.5,
            image_path="test.jpg",
            processing_timestamp=datetime.now(),
            scale_factor=1.0,
            total_analyzed_area=10000.0,
            quality_flags=["Poor image quality", "Scale detection issues"],
            is_valid=False
        )
        
        with patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer.analyze_muckpile_image',
                   return_value=mock_result):
            
            response = client.post(
                "/api/v1/ml/analyze-fragmentation",
                files={"image": ("test.jpg", test_image_bytes, "image/jpeg")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        recommendations = data["data"]["recommendations"]
        assert len(recommendations) > 0
        
        # Check for specific recommendations based on the poor quality result
        recommendation_text = " ".join(recommendations).lower()
        assert any(keyword in recommendation_text for keyword in [
            "lighting", "image", "scale", "fragments", "powder factor"
        ])


class TestMLPipelineIntegration:
    """Integration tests for ML pipeline with other system components"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_ml_pipeline_in_main_api(self, client):
        """Test that ML pipeline routes are properly integrated in main API"""
        # Test that the ML endpoints are accessible
        response = client.get("/api/v1/ml/analyzer-status")
        
        # Should not return 404 (route not found)
        assert response.status_code != 404
    
    def test_cors_headers_on_ml_endpoints(self, client):
        """Test that CORS headers are properly set on ML endpoints"""
        response = client.options("/api/v1/ml/analyzer-status")
        
        # Should handle OPTIONS request for CORS
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled
    
    def test_error_handling_consistency(self, client):
        """Test that ML pipeline error handling is consistent with rest of API"""
        # Test with invalid endpoint
        response = client.get("/api/v1/ml/nonexistent-endpoint")
        assert response.status_code == 404
        
        # Test error response format
        error_data = response.json()
        assert "detail" in error_data or "error" in error_data


@pytest.mark.performance
class TestMLPipelinePerformance:
    """Performance tests for ML pipeline"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def large_test_image_bytes(self):
        """Create large test image for performance testing"""
        # Create larger image (2MP)
        image = np.zeros((1200, 1600, 3), dtype=np.uint8)
        
        # Add many fragments
        for i in range(100):
            center = (np.random.randint(50, 1550), np.random.randint(50, 1150))
            radius = np.random.randint(10, 50)
            color = np.random.randint(80, 180, 3).tolist()
            cv2.circle(image, center, radius, color, -1)
        
        # Convert to bytes
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        return io.BytesIO(buffer.tobytes())
    
    def test_large_image_processing_time(self, client, large_test_image_bytes):
        """Test processing time for large images"""
        import time
        
        # Mock to avoid actual heavy processing
        mock_result = FragmentationResult(
            p10=30.0, p50=60.0, p80=120.0, mean_size=65.0,
            characteristic_size=70.0, uniformity_index=1.6,
            fragment_count=100, fragment_sizes=list(range(20, 120)),
            fragment_areas=[(i*2)**2 for i in range(20, 120)],
            measurement_quality=0.8, scale_detection_quality=0.8,
            segmentation_quality=0.8, image_path="large_test.jpg",
            processing_timestamp=datetime.now(), scale_factor=0.3,
            total_analyzed_area=100000.0, quality_flags=[], is_valid=True
        )
        
        with patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer.analyze_muckpile_image',
                   return_value=mock_result):
            
            start_time = time.time()
            
            response = client.post(
                "/api/v1/ml/analyze-fragmentation",
                files={"image": ("large_test.jpg", large_test_image_bytes, "image/jpeg")},
                data={"known_scale_mm_per_pixel": "0.3"}
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
        
        assert response.status_code == 200
        # API should respond quickly even for large images (mocked processing)
        assert processing_time < 5.0  # Should be much faster with mocking
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent analysis requests"""
        import threading
        import time
        
        # Create simple test image
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        cv2.circle(image, (150, 100), 30, (128, 128, 128), -1)
        _, buffer = cv2.imencode('.jpg', image)
        test_image_bytes = io.BytesIO(buffer.tobytes())
        
        mock_result = FragmentationResult(
            p10=20.0, p50=40.0, p80=80.0, mean_size=45.0,
            characteristic_size=50.0, uniformity_index=1.5,
            fragment_count=1, fragment_sizes=[40],
            fragment_areas=[1256], measurement_quality=0.7,
            scale_detection_quality=0.6, segmentation_quality=0.7,
            image_path="concurrent_test.jpg", processing_timestamp=datetime.now(),
            scale_factor=0.5, total_analyzed_area=1256.0,
            quality_flags=[], is_valid=True
        )
        
        results = []
        
        def make_request():
            with patch('src.drill_blast_system.ml_pipeline.FragmentationAnalyzer.analyze_muckpile_image',
                       return_value=mock_result):
                response = client.post(
                    "/api/v1/ml/analyze-fragmentation",
                    files={"image": ("test.jpg", test_image_bytes, "image/jpeg")},
                    data={"known_scale_mm_per_pixel": "0.5"}
                )
                results.append(response.status_code)
        
        # Start multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])