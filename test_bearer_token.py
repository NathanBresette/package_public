#!/usr/bin/env python3
"""
Test Bearer Token Authentication System
"""

import requests
import time

BACKEND_URL = "https://rgent.onrender.com"
TEST_EMAIL = f"test-bearer-{int(time.time())}@example.com"

def test_bearer_token_system():
    """Test the complete Bearer token authentication system"""
    print("🔐 Testing Bearer Token Authentication System")
    print("=" * 60)
    
    # Test 1: Create Account
    print(f"\n1️⃣ Creating account with email: {TEST_EMAIL}")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/create-account",
            json={
                "email": TEST_EMAIL,
                "password": "testpassword123",
                "plan_type": "free_trial"
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Account created successfully!")
            print(f"   Access Code: {data.get('access_code', 'N/A')}")
            
            # Check for token
            token = data.get('token')
            if token:
                print(f"✅ JWT token received: {token[:30]}...")
            else:
                print("❌ No JWT token received")
                return False
        else:
            print(f"❌ Account creation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Test Session with Bearer Token
    print(f"\n2️⃣ Testing session with Bearer token...")
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(f"{BACKEND_URL}/api/session", headers=headers)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Session validation successful!")
            print(f"   User: {data.get('user', {}).get('access_code', 'N/A')}")
            print(f"   Email: {data.get('user', {}).get('email', 'N/A')}")
        else:
            print(f"❌ Session validation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 3: Test Sign In
    print(f"\n3️⃣ Testing sign in...")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/signin",
            json={
                "email": TEST_EMAIL,
                "password": "testpassword123"
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Sign in successful!")
            print(f"   Access Code: {data.get('access_code', 'N/A')}")
            
            # Check for new token
            new_token = data.get('token')
            if new_token:
                print(f"✅ New JWT token received: {new_token[:30]}...")
            else:
                print("❌ No JWT token received")
                return False
        else:
            print(f"❌ Sign in failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 4: Test Session with New Token
    print(f"\n4️⃣ Testing session with new Bearer token...")
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {new_token}"
        }
        
        response = requests.get(f"{BACKEND_URL}/api/session", headers=headers)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ New session validation successful!")
            print(f"   User: {data.get('user', {}).get('access_code', 'N/A')}")
        else:
            print(f"❌ New session validation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 5: Test Invalid Token
    print(f"\n5️⃣ Testing invalid token...")
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid_token_123"
        }
        
        response = requests.get(f"{BACKEND_URL}/api/session", headers=headers)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Invalid token properly rejected!")
        else:
            print(f"❌ Invalid token not rejected: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print("\n🎉 All Bearer Token Tests Passed!")
    return True

if __name__ == "__main__":
    success = test_bearer_token_system()
    if success:
        print("\n✅ Bearer Token System Summary:")
        print("   • JWT tokens are generated and returned")
        print("   • Bearer token authentication works")
        print("   • Session validation with tokens works")
        print("   • Invalid tokens are properly rejected")
        print("   • Cross-domain authentication is now possible")
        print("\n🚀 The authentication system should now work properly!")
    else:
        print("\n❌ Tests failed. Please check the implementation.") 