import json
import os
from datetime import datetime
from typing import Dict, Any
from loguru import logger

class ResponseStorage:
    def __init__(self):
        self.base_dir = "reports/responses"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure necessary directories exist"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "validations"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "comparisons"), exist_ok=True)
    
    def store_validation(self, test_id: str, language: str, query: str, response: str, validation_results: Dict[str, Any]):
        """Store validation results for a single response"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_id}_{language}_{timestamp}.json"
        filepath = os.path.join(self.base_dir, "validations", filename)
        
        data = {
            "test_id": test_id,
            "language": language,
            "timestamp": timestamp,
            "query": query,
            "response": response,
            "validation_results": validation_results
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Stored validation results in {filepath}")
    
    def store_comparison(self, test_id: str, en_data: Dict[str, str], ar_data: Dict[str, str], comparison_results: Dict[str, Any]):
        """Store comparison results between English and Arabic responses"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_id}_comparison_{timestamp}.json"
        filepath = os.path.join(self.base_dir, "comparisons", filename)
        
        data = {
            "test_id": test_id,
            "timestamp": timestamp,
            "english": en_data,
            "arabic": ar_data,
            "comparison_results": comparison_results
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Stored comparison results in {filepath}")
    
    def get_latest_validation(self, test_id: str, language: str) -> Dict[str, Any]:
        """Get the latest validation results for a test case and language"""
        validation_dir = os.path.join(self.base_dir, "validations")
        matching_files = [f for f in os.listdir(validation_dir) 
                        if f.startswith(f"{test_id}_{language}_") and f.endswith(".json")]
        
        if not matching_files:
            return None
        
        latest_file = max(matching_files)
        filepath = os.path.join(validation_dir, latest_file)
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_latest_comparison(self, test_id: str) -> Dict[str, Any]:
        """Get the latest comparison results for a test case"""
        comparison_dir = os.path.join(self.base_dir, "comparisons")
        matching_files = [f for f in os.listdir(comparison_dir) 
                        if f.startswith(f"{test_id}_comparison_") and f.endswith(".json")]
        
        if not matching_files:
            return None
        
        latest_file = max(matching_files)
        filepath = os.path.join(comparison_dir, latest_file)
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f) 