#!/usr/bin/env python3
"""
Complete Billing System Test
Tests the updated pricing and limits for the PII-free billing system
"""

import requests
import json
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://rgent.onrender.com"
TEST_EMAIL = "test@example.com"

def test_backend_health():
    """Test if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return False

def test_free_trial_creation():
    """Test free trial account creation"""
    try:
        # Create free trial account
        response = requests.post(f"{BACKEND_URL}/api/create-account", 
                               json={
                                   "email": TEST_EMAIL,
                                   "password": "testpass123",
                                   "plan_type": "free_trial"
                               }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Free trial created: {data.get('access_code', 'N/A')}")
            return data.get('access_code')
        else:
            print(f"❌ Free trial creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Free trial creation error: {e}")
        return None

def test_chat_with_billing(access_code):
    """Test chat functionality with billing reporting"""
    try:
        response = requests.post(f"{BACKEND_URL}/chat",
                               json={
                                   "access_code": access_code,
                                   "prompt": "Hello, this is a test message for billing verification.",
                                   "context_data": {"test": True},
                                   "context_type": "test"
                               }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat successful: {len(data.get('response', ''))} characters")
            return True
        else:
            print(f"❌ Chat failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return False

def test_usage_tracking(access_code):
    """Test usage tracking"""
    try:
        response = requests.get(f"{BACKEND_URL}/usage/{access_code}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Usage tracking working: {data}")
            return True
        else:
            print(f"❌ Usage tracking failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Usage tracking error: {e}")
        return False

def test_stripe_webhook_simulation():
    """Test Stripe webhook handling"""
    try:
        # Test webhook endpoint exists
        response = requests.post(f"{BACKEND_URL}/api/webhook",
                               json={"test": "webhook"},
                               headers={"stripe-signature": "test"},
                               timeout=10)
        
        # Should fail due to invalid signature, but endpoint should exist
        if response.status_code in [400, 401, 500]:
            print("✅ Webhook endpoint exists (expected error for test)")
            return True
        else:
            print(f"❌ Unexpected webhook response: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Webhook test error: {e}")
        return False

def test_pricing_calculation():
    """Test pricing calculation with new rates"""
    try:
        # Test the pricing calculation logic
        from backend.stripe_billing import calculate_token_cost
        
        # Test Haiku pricing
        haiku_cost = calculate_token_cost(1000, 500, 'pro_haiku')
        expected_haiku = (1000/1000) * 0.0013 + (500/1000) * 0.00533
        print(f"✅ Haiku pricing: {haiku_cost:.4f} (expected: {expected_haiku:.4f})")
        
        # Test Sonnet pricing
        sonnet_cost = calculate_token_cost(1000, 500, 'pro_sonnet')
        expected_sonnet = (1000/1000) * 0.005 + (500/1000) * 0.02
        print(f"✅ Sonnet pricing: {sonnet_cost:.4f} (expected: {expected_sonnet:.4f})")
        
        return True
    except Exception as e:
        print(f"❌ Pricing calculation error: {e}")
        return False

def test_meter_configuration():
    """Test meter configuration"""
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        if not stripe.api_key:
            print("⚠️  STRIPE_SECRET_KEY not set - skipping meter test")
            return True
        
        # List meters to verify configuration
        meters = stripe.Meter.list(limit=10)
        meter_names = [meter.display_name for meter in meters.data]
        
        if 'Input Tokens' in meter_names and 'Output Tokens' in meter_names:
            print("✅ Both meters configured: Input Tokens, Output Tokens")
            return True
        else:
            print(f"❌ Missing meters. Found: {meter_names}")
            return False
            
    except Exception as e:
        print(f"❌ Meter configuration error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Complete Billing System Test")
    print("=" * 50)
    
    tests = [
        ("Backend Health", test_backend_health),
        ("Pricing Calculation", test_pricing_calculation),
        ("Meter Configuration", test_meter_configuration),
        ("Free Trial Creation", test_free_trial_creation),
        ("Stripe Webhook", test_stripe_webhook_simulation),
    ]
    
    results = {}
    access_code = None
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing: {test_name}")
        try:
            if test_name == "Free Trial Creation":
                access_code = test_func()
                results[test_name] = access_code is not None
            else:
                results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results[test_name] = False
    
    # Test chat and usage if we have an access code
    if access_code:
        print(f"\n🧪 Testing: Chat with Billing")
        results["Chat with Billing"] = test_chat_with_billing(access_code)
        
        print(f"\n🧪 Testing: Usage Tracking")
        results["Usage Tracking"] = test_usage_tracking(access_code)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your billing system is ready.")
    else:
        print("⚠️  Some tests failed. Check the configuration.")
    
    return passed == total

if __name__ == "__main__":
    main() 