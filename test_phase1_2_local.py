#!/usr/bin/env python3
"""
Simplified local test for Phase 1 & 2 - PII-free system
Tests what we can verify locally without PostgreSQL connection
"""

import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append('backend')

def print_test_header(test_name):
    print(f"\n{'='*60}")
    print(f"🧪 TESTING: {test_name}")
    print(f"{'='*60}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️ {message}")

def test_code_structure():
    """Test 1: Code structure and imports"""
    print_test_header("Code Structure and Imports")
    
    try:
        # Test if we can import the PostgreSQL user manager
        from user_management_postgres import UserManagerPostgreSQL
        print_success("PostgreSQL user manager imports correctly")
        
        # Test if we can import the memory context
        from memory_only_context import memory_context
        print_success("Memory-only context imports correctly")
        
        # Test if we can import the config
        from config import get_user_manager
        print_success("Config imports correctly")
        
        return True
        
    except ImportError as e:
        print_error(f"Import error: {e}")
        return False
    except Exception as e:
        print_error(f"Code structure test error: {e}")
        return False

def test_memory_context():
    """Test 2: Memory-only context processing"""
    print_test_header("Memory-only Context Processing")
    
    try:
        from memory_only_context import memory_context
        
        # Test context processing
        access_code = "test_access_123"
        context_data = {
            "file_content": "test R code",
            "file_name": "test.R"
        }
        
        # Process context (should not persist)
        context_hash = memory_context.process_context(access_code, context_data, "r_code")
        
        if context_hash:
            print_success("Context processing working")
            print_info(f"Context hash: {context_hash}")
            
            # Test session stats
            stats = memory_context.get_session_stats(access_code)
            if stats:
                print_success("Session stats working")
                print_info(f"Session active: {stats.get('session_active', False)}")
            else:
                print_error("Session stats failed")
                return False
            
            # Test clearing session
            memory_context.clear_session(access_code)
            print_success("Session clearing working")
        else:
            print_error("Context processing failed")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Memory context test error: {e}")
        return False

def test_access_code_generation():
    """Test 3: Access code generation (16-character alphanumeric)"""
    print_test_header("Access Code Generation")
    
    try:
        from user_management_postgres import UserManagerPostgreSQL
        
        # Create a temporary instance just for testing
        user_manager = UserManagerPostgreSQL("postgresql://test")
        
        # Generate access codes
        codes = []
        for i in range(5):
            code = user_manager.generate_access_code()
            codes.append(code)
            print_info(f"Generated code {i+1}: {code}")
        
        # Verify all codes are 16 characters
        for code in codes:
            if len(code) != 16:
                print_error(f"Access code length incorrect: {len(code)} chars")
                return False
        
        # Verify all codes are unique
        if len(set(codes)) != len(codes):
            print_error("Generated codes are not unique")
            return False
        
        # Verify codes contain only alphanumeric characters
        import string
        allowed_chars = string.ascii_letters + string.digits
        for code in codes:
            if not all(c in allowed_chars for c in code):
                print_error(f"Access code contains invalid characters: {code}")
                return False
        
        print_success("Access code generation working correctly")
        print_info("All codes are 16-character alphanumeric and unique")
        
        return True
        
    except Exception as e:
        print_error(f"Access code generation test error: {e}")
        return False

def test_pii_free_schema():
    """Test 4: PII-free schema verification"""
    print_test_header("PII-free Schema Verification")
    
    try:
        from user_management_postgres import UserProfile
        
        # Test UserProfile dataclass
        user = UserProfile(
            access_code="test12345678901234",
            stripe_customer_id="cus_test123",
            is_active=True,
            daily_limit=1000,
            monthly_budget=10.0
        )
        
        # Verify no PII fields
        user_dict = user.__dict__
        pii_fields = ['email', 'password_hash', 'user_name']
        
        for field in pii_fields:
            if field in user_dict:
                print_error(f"PII field found in schema: {field}")
                return False
        
        # Verify required fields exist
        required_fields = ['access_code', 'stripe_customer_id', 'is_active']
        for field in required_fields:
            if field not in user_dict:
                print_error(f"Required field missing: {field}")
                return False
        
        print_success("Schema is PII-free")
        print_info(f"User profile fields: {list(user_dict.keys())}")
        
        return True
        
    except Exception as e:
        print_error(f"Schema verification test error: {e}")
        return False

def test_config_structure():
    """Test 5: Configuration structure"""
    print_test_header("Configuration Structure")
    
    try:
        from config import get_user_manager, USE_POSTGRESQL, DATABASE_URL
        
        # Verify configuration
        if USE_POSTGRESQL:
            print_success("PostgreSQL is configured as primary database")
        else:
            print_error("PostgreSQL not configured as primary database")
            return False
        
        # Test that get_user_manager function exists
        if callable(get_user_manager):
            print_success("get_user_manager function is callable")
        else:
            print_error("get_user_manager is not callable")
            return False
        
        print_info("Configuration structure is correct")
        return True
        
    except Exception as e:
        print_error(f"Configuration test error: {e}")
        return False

def main():
    """Run all local tests"""
    print("🚀 STARTING LOCAL PII-FREE SYSTEM TESTS (Phase 1 & 2)")
    print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📝 Testing code structure and memory-only context processing")
    
    # Track test results
    test_results = []
    
    # Run tests
    test_results.append(("Code Structure", test_code_structure()))
    test_results.append(("Memory Context", test_memory_context()))
    test_results.append(("Access Code Generation", test_access_code_generation()))
    test_results.append(("PII-free Schema", test_pii_free_schema()))
    test_results.append(("Configuration", test_config_structure()))
    
    # Summary
    print_test_header("TEST SUMMARY")
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    if passed == total:
        print_success("🎉 ALL LOCAL TESTS PASSED!")
        print_info("Phase 1 & 2 code structure is working correctly.")
        print_info("PostgreSQL integration will be tested when deployed.")
    else:
        print_error(f"⚠️ {total - passed} local tests failed. Check the code changes.")
    
    print(f"\n📅 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 