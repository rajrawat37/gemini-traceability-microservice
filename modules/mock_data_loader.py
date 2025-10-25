"""
Mock Data Loader Module
Provides utilities for loading mock data from the mockData directory
"""

import json
import os
from typing import Dict, Any, List, Optional


def get_mock_data_path(subdirectory: str, filename: str) -> str:
    """
    Get the full path to a mock data file
    
    Args:
        subdirectory: Subdirectory within mockData (e.g., 'responses', 'inputs', 'configs')
        filename: Name of the file
        
    Returns:
        Full path to the mock data file
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, "mockData", subdirectory, filename)


def load_json_mock_data(subdirectory: str, filename: str, fallback_data: Optional[Dict] = None) -> Dict:
    """
    Load JSON mock data from the mockData directory
    
    Args:
        subdirectory: Subdirectory within mockData (e.g., 'responses', 'inputs', 'configs')
        filename: Name of the JSON file
        fallback_data: Fallback data to return if file is not found
        
    Returns:
        Loaded JSON data or fallback data
    """
    file_path = get_mock_data_path(subdirectory, filename)
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Mock data file not found at {file_path}")
        if fallback_data:
            return fallback_data
        return {}
    except json.JSONDecodeError as e:
        print(f"⚠️  Error parsing mock data file {file_path}: {e}")
        if fallback_data:
            return fallback_data
        return {}


def load_json_list_mock_data(subdirectory: str, filename: str, fallback_data: Optional[List] = None) -> List:
    """
    Load JSON list mock data from the mockData directory
    
    Args:
        subdirectory: Subdirectory within mockData (e.g., 'responses', 'inputs', 'configs')
        filename: Name of the JSON file
        fallback_data: Fallback data to return if file is not found
        
    Returns:
        Loaded JSON list data or fallback data
    """
    file_path = get_mock_data_path(subdirectory, filename)
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Mock data file not found at {file_path}")
        if fallback_data:
            return fallback_data
        return []
    except json.JSONDecodeError as e:
        print(f"⚠️  Error parsing mock data file {file_path}: {e}")
        if fallback_data:
            return fallback_data
        return []


def load_document_ai_mock() -> Dict:
    """Load Document AI mock response"""
    return load_json_mock_data("responses", "document_ai_mock_response.json")


def load_fallback_tests_mock() -> List[Dict]:
    """Load fallback tests mock data"""
    return load_json_list_mock_data("responses", "fallback_tests.json")


def load_sample_requirements() -> List[Dict]:
    """Load sample requirements mock data"""
    return load_json_list_mock_data("inputs", "sample_requirements.json")


def load_sample_compliance_standards() -> List[Dict]:
    """Load sample compliance standards mock data"""
    return load_json_list_mock_data("inputs", "sample_compliance_standards.json")


def load_mock_environment_config() -> Dict:
    """Load mock environment configuration"""
    return load_json_mock_data("configs", "mock_environment.json")


def load_test_categories_config() -> Dict:
    """Load test categories configuration"""
    return load_json_mock_data("configs", "test_categories.json")
