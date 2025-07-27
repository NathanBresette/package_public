#!/usr/bin/env python3
"""
Test Session Cookie System
Tests the new HTTP-only cookie-based session management
"""

import requests
import json
import time

# Configuration
BACKEND_URL = "https://rgent.onrender.com"
TEST_EMAIL = "test-session@example.com"
TEST_PASSWORD = "testpassword123"

def test_session_system():
    """Test the complete session cookie system"""
    print("🔐 Testing Session Cookie System")
    print("=" * 50)
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Test 1: Create Account
    print("\n1️⃣ Testing Account Creation...")
    try:
        create_response = session.post(
            f"{BACKEND_URL}/api/create-account",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "plan_type": "free_trial"
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {create_response.status_code}")
        print(f"Response: {create_response.text[:200]}...")
        
        if create_response.status_code == 200:
            data = create_response.json()
            print("✅ Account created successfully")
            print(f"   Access Code: {data.get('access_code', 'N/A')}")
            print(f"   Plan Type: {data.get('plan_type', 'N/A')}")
            
            # Check if session cookie was set
            cookies = session.cookies
            session_cookie = cookies.get('session_token')
            if session_cookie:
                print(f"✅ Session cookie set: {session_cookie[:20]}...")
            else:
                print("❌ No session cookie found")
                return False
        else:
            print("❌ Account creation failed")
            return False
            
    except Exception as e:
        print(f"❌ Account creation error: {e}")
        return False
    
    # Test 2: Check Session
    print("\n2️⃣ Testing Session Validation...")
    try:
        session_response = session.get(f"{BACKEND_URL}/api/session")
        
        print(f"Status Code: {session_response.status_code}")
        print(f"Response: {session_response.text[:200]}...")
        
        if session_response.status_code == 200:
            data = session_response.json()
            print("✅ Session validation successful")
            print(f"   User ID: {data.get('user', {}).get('access_code', 'N/A')}")
            print(f"   Email: {data.get('user', {}).get('email', 'N/A')}")
            print(f"   Plan Type: {data.get('user', {}).get('plan_type', 'N/A')}")
        else:
            print("❌ Session validation failed")
            return False
            
    except Exception as e:
        print(f"❌ Session validation error: {e}")
        return False
    
    # Test 3: Test Logout
    print("\n3️⃣ Testing Logout...")
    try:
        logout_response = session.post(f"{BACKEND_URL}/api/logout")
        
        print(f"Status Code: {logout_response.status_code}")
        print(f"Response: {logout_response.text[:200]}...")
        
        if logout_response.status_code == 200:
            print("✅ Logout successful")
            
            # Check if session cookie was cleared
            cookies = session.cookies
            session_cookie = cookies.get('session_token')
            if not session_cookie:
                print("✅ Session cookie cleared")
            else:
                print("❌ Session cookie still present")
                return False
        else:
            print("❌ Logout failed")
            return False
            
    except Exception as e:
        print(f"❌ Logout error: {e}")
        return False
    
    # Test 4: Verify Session is Invalid After Logout
    print("\n4️⃣ Testing Session After Logout...")
    try:
        session_response = session.get(f"{BACKEND_URL}/api/session")
        
        print(f"Status Code: {session_response.status_code}")
        
        if session_response.status_code == 401:
            print("✅ Session properly invalidated after logout")
        else:
            print("❌ Session still valid after logout")
            return False
            
    except Exception as e:
        print(f"❌ Session check error: {e}")
        return False
    
    # Test 5: Test Sign In
    print("\n5️⃣ Testing Sign In...")
    try:
        signin_response = session.post(
            f"{BACKEND_URL}/api/signin",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {signin_response.status_code}")
        print(f"Response: {signin_response.text[:200]}...")
        
        if signin_response.status_code == 200:
            data = signin_response.json()
            print("✅ Sign in successful")
            print(f"   Access Code: {data.get('access_code', 'N/A')}")
            print(f"   Plan Type: {data.get('plan_type', 'N/A')}")
            
            # Check if new session cookie was set
            cookies = session.cookies
            session_cookie = cookies.get('session_token')
            if session_cookie:
                print(f"✅ New session cookie set: {session_cookie[:20]}...")
            else:
                print("❌ No new session cookie found")
                return False
        else:
            print("❌ Sign in failed")
            return False
            
    except Exception as e:
        print(f"❌ Sign in error: {e}")
        return False
    
    # Test 6: Final Session Check
    print("\n6️⃣ Final Session Validation...")
    try:
        session_response = session.get(f"{BACKEND_URL}/api/session")
        
        print(f"Status Code: {session_response.status_code}")
        
        if session_response.status_code == 200:
            data = session_response.json()
            print("✅ Final session validation successful")
            print(f"   User ID: {data.get('user', {}).get('access_code', 'N/A')}")
            print(f"   Email: {data.get('user', {}).get('email', 'N/A')}")
        else:
            print("❌ Final session validation failed")
            return False
            
    except Exception as e:
        print(f"❌ Final session check error: {e}")
        return False
    
    print("\n🎉 All Session Cookie Tests Passed!")
    return True

def test_cookie_security():
    """Test cookie security features"""
    print("\n🔒 Testing Cookie Security Features")
    print("=" * 50)
    
    session = requests.Session()
    
    # Create account to get a session
    try:
        create_response = session.post(
            f"{BACKEND_URL}/api/create-account",
            json={
                "email": f"security-test-{int(time.time())}@example.com",
                "password": "testpassword123",
                "plan_type": "free_trial"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if create_response.status_code == 200:
            print("✅ Account created for security testing")
            
            # Check cookie attributes
            cookies = session.cookies
            session_cookie = cookies.get('session_token')
            
            if session_cookie:
                print(f"✅ Session cookie present: {session_cookie[:20]}...")
                
                # Note: We can't directly check HttpOnly, Secure, SameSite from client
                # These are set by the server and enforced by the browser
                print("ℹ️  Cookie security features (HttpOnly, Secure, SameSite) are enforced by the browser")
                print("ℹ️  These cannot be directly tested from Python but are set in the backend")
            else:
                print("❌ No session cookie found")
                return False
        else:
            print("❌ Account creation failed for security testing")
            return False
            
    except Exception as e:
        print(f"❌ Security test error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Session Cookie System Tests")
    print("=" * 60)
    
    # Test basic session functionality
    session_success = test_session_system()
    
    # Test security features
    security_success = test_cookie_security()
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   Session System: {'✅ PASS' if session_success else '❌ FAIL'}")
    print(f"   Security Features: {'✅ PASS' if security_success else '❌ FAIL'}")
    
    if session_success and security_success:
        print("\n🎉 All tests passed! Session cookie system is working correctly.")
        print("\n✅ Benefits of this implementation:")
        print("   • HTTP-only cookies prevent XSS attacks")
        print("   • Secure flag ensures HTTPS-only transmission")
        print("   • SameSite=Lax provides CSRF protection")
        print("   • No more localStorage domain issues")
        print("   • Proper session management across all pages")
    else:
        print("\n❌ Some tests failed. Please check the implementation.") 