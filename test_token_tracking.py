#!/usr/bin/env python3
"""
Test script to verify token tracking functionality
"""

from user_management_sqlite import UserManagerSQLite
import os

def test_token_tracking():
    """Test the token tracking functionality"""
    print("🧪 Testing token tracking functionality...")
    
    # Initialize user manager
    um = UserManagerSQLite("test_users.db")
    
    # Create a test user
    test_access_code = "TEST123"
    um.create_user(test_access_code, "Test User", "test@example.com")
    
    # Test recording usage with input/output tokens
    usage_info = {
        "request_type": "chat",
        "input_tokens": 150,
        "output_tokens": 300,
        "cost": 0.002,
        "prompt_length": 50,
        "response_length": 100,
        "success": True
    }
    
    # Record usage
    success = um.record_usage(test_access_code, usage_info)
    print(f"✅ Usage recording: {'SUCCESS' if success else 'FAILED'}")
    
    # Get user stats
    stats = um.get_user_stats(test_access_code)
    print(f"✅ Stats retrieval: {'SUCCESS' if stats else 'FAILED'}")
    
    if stats:
        print(f"📊 User Stats:")
        print(f"   Total Input Tokens: {stats.get('total_input_tokens', 0)}")
        print(f"   Total Output Tokens: {stats.get('total_output_tokens', 0)}")
        print(f"   Today Input Tokens: {stats.get('today_input_tokens', 0)}")
        print(f"   Today Output Tokens: {stats.get('today_output_tokens', 0)}")
        print(f"   Total Cost: ${stats.get('total_cost', 0):.4f}")
        print(f"   Today Cost: ${stats.get('today_cost', 0):.4f}")
    
    # Clean up test database
    try:
        os.remove("test_users.db")
        print("✅ Test database cleaned up")
    except:
        pass
    
    print("🎉 Token tracking test completed!")

if __name__ == "__main__":
    test_token_tracking() 