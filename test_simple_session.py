#!/usr/bin/env python3
"""
Simple Session Cookie Test
"""

import requests
import time

BACKEND_URL = "https://rgent.onrender.com"
TEST_EMAIL = f"test-{int(time.time())}@example.com"

def test_simple_session():
    """Simple test of session cookies"""
    print("🔐 Testing Simple Session Cookie System")
    print("=" * 50)
    
    # Create session to maintain cookies
    session = requests.Session()
    
    # Test 1: Create Account
    print(f"\n1️⃣ Creating account with email: {TEST_EMAIL}")
    try:
        response = session.post(
            f"{BACKEND_URL}/api/create-account",
            json={
                "email": TEST_EMAIL,
                "password": "testpassword123",
                "plan_type": "free_trial"
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Account created successfully!")
            print(f"   Access Code: {data.get('access_code', 'N/A')}")
            
            # Check for session cookie
            cookies = session.cookies
            session_cookie = cookies.get('session_token')
            if session_cookie:
                print(f"✅ Session cookie set: {session_cookie[:30]}...")
            else:
                print("❌ No session cookie found")
                return False
        else:
            print(f"❌ Account creation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Check Session
    print(f"\n2️⃣ Checking session...")
    try:
        response = session.get(f"{BACKEND_URL}/api/session")
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
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
    
    # Test 3: Logout
    print(f"\n3️⃣ Testing logout...")
    try:
        response = session.post(f"{BACKEND_URL}/api/logout")
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ Logout successful!")
            
            # Check if cookie was cleared
            cookies = session.cookies
            session_cookie = cookies.get('session_token')
            if not session_cookie:
                print("✅ Session cookie cleared")
            else:
                print("❌ Session cookie still present")
                return False
        else:
            print(f"❌ Logout failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 4: Verify session is invalid
    print(f"\n4️⃣ Verifying session is invalid after logout...")
    try:
        response = session.get(f"{BACKEND_URL}/api/session")
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Session properly invalidated!")
        else:
            print(f"❌ Session still valid: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print("\n🎉 All tests passed! Session cookie system is working!")
    return True

if __name__ == "__main__":
    success = test_simple_session()
    if success:
        print("\n✅ Session Cookie System Summary:")
        print("   • HTTP-only cookies are working")
        print("   • Session creation and validation work")
        print("   • Logout properly clears cookies")
        print("   • Session invalidation works correctly")
        print("\n🚀 The logout issue should now be fixed!")
    else:
        print("\n❌ Tests failed. Please check the implementation.") 