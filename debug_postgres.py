#!/usr/bin/env python3
"""
Debug script to test PostgreSQL database connection
"""

import requests
import json

# Render backend URL
BACKEND_URL = "https://rgent.onrender.com"

def test_database():
    """Test database connection and basic queries"""
    print("🔍 Testing PostgreSQL database...")
    print("=" * 50)
    
    # Test 1: Check if users exist
    print("Test 1: Checking users list...")
    try:
        response = requests.get(f"{BACKEND_URL}/users/list?admin_access_code=admin123")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    
    # Test 2: Try a simple validation without rate limiting
    print("Test 2: Testing simple validation...")
    try:
        response = requests.post(
            f"{BACKEND_URL}/validate",
            json={"access_code": "DEMO123"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    
    # Test 3: Check health endpoint
    print("Test 3: Checking health...")
    try:
        response = requests.get(f"{BACKEND_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_database() 