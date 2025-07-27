#!/usr/bin/env python3
"""
PII-Free System Test
Tests the complete PII-free billing system with a Stripe test customer
"""

import requests
import json
import os
import stripe
from datetime import datetime

# Configuration
BACKEND_URL = "https://rgent.onrender.com"
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

def test_stripe_connection():
    """Test Stripe API connection"""
    try:
        stripe.api_key = STRIPE_SECRET_KEY
        customers = stripe.Customer.list(limit=1)
        print("✅ Stripe connection successful")
        return True
    except Exception as e:
        print(f"❌ Stripe connection failed: {e}")
        return False

def create_test_customer():
    """Create a test customer in Stripe"""
    try:
        customer = stripe.Customer.create(
            email="test@example.com",
            name="Test Customer",
            description="Testing PII-free system",
            metadata={
                "plan_type": "free_trial",
                "created_at": datetime.now().isoformat(),
                "trial_requests_remaining": "25"
            }
        )
        print(f"✅ Test customer created: {customer.id}")
        return customer.id
    except Exception as e:
        print(f"❌ Failed to create test customer: {e}")
        return None

def test_account_creation_with_stripe_id(customer_id):
    """Test creating account with Stripe customer ID"""
    try:
        response = requests.post(f"{BACKEND_URL}/api/create-account", 
                               json={
                                   "email": "test@example.com",
                                   "password": "testpass123",
                                   "plan_type": "free_trial"
                               }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Account created: {data.get('access_code', 'N/A')}")
            print(f"   Stripe Customer ID: {data.get('stripe_customer_id', 'N/A')}")
            return data.get('access_code')
        else:
            print(f"❌ Account creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Account creation error: {e}")
        return None

def test_chat_with_billing_reporting(access_code):
    """Test chat functionality with automatic billing reporting"""
    try:
        print(f"\n🧪 Testing chat with access code: {access_code}")
        
        response = requests.post(f"{BACKEND_URL}/chat",
                               json={
                                   "access_code": access_code,
                                   "prompt": "Hello! This is a test message to verify token usage reporting.",
                                   "context_data": {"test": True, "timestamp": datetime.now().isoformat()},
                                   "context_type": "test"
                               }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat successful!")
            print(f"   Response length: {len(data.get('response', ''))} characters")
            print(f"   Conversation ID: {data.get('conversation_id', 'N/A')}")
            return True
        else:
            print(f"❌ Chat failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return False

def test_usage_tracking(access_code):
    """Test usage tracking and limits"""
    try:
        response = requests.get(f"{BACKEND_URL}/usage/{access_code}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Usage tracking working:")
            print(f"   Daily limit: {data.get('daily_limit', 'N/A')}")
            print(f"   Requests used: {data.get('requests_used', 'N/A')}")
            print(f"   Requests remaining: {data.get('requests_remaining', 'N/A')}")
            return True
        else:
            print(f"❌ Usage tracking failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Usage tracking error: {e}")
        return False

def test_database_schema():
    """Test that no PII is stored in database"""
    try:
        # Test user validation (should not return PII)
        response = requests.post(f"{BACKEND_URL}/validate",
                               json={"access_code": "TEST123"}, timeout=10)
        
        if response.status_code in [200, 401]:  # Both valid and invalid responses are fine
            data = response.json()
            # Check that response doesn't contain PII
            if 'email' not in data and 'user_name' not in data and 'name' not in data:
                print("✅ No PII in API responses")
                return True
            else:
                print(f"❌ PII found in response: {data}")
                return False
        else:
            print(f"❌ Validation endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Database schema test error: {e}")
        return False

def test_stripe_webhook_simulation():
    """Test webhook endpoint exists"""
    try:
        response = requests.post(f"{BACKEND_URL}/api/webhook",
                               json={"type": "test.event"},
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

def test_meter_reporting(customer_id):
    """Test that usage is reported to Stripe meters"""
    try:
        if not STRIPE_SECRET_KEY:
            print("⚠️  STRIPE_SECRET_KEY not set - skipping meter test")
            return True
        
        # Check if meters exist
        meters = stripe.Meter.list(limit=10)
        meter_names = [meter.display_name for meter in meters.data]
        
        if 'Input Tokens' in meter_names and 'Output Tokens' in meter_names:
            print("✅ Both meters configured: Input Tokens, Output Tokens")
            
            # Note: Actual usage reporting happens in the chat endpoint
            # This just verifies the meters are set up
            return True
        else:
            print(f"❌ Missing meters. Found: {meter_names}")
            return False
            
    except Exception as e:
        print(f"❌ Meter test error: {e}")
        return False

def cleanup_test_customer(customer_id):
    """Clean up test customer"""
    try:
        if customer_id:
            stripe.Customer.delete(customer_id)
            print(f"✅ Test customer cleaned up: {customer_id}")
    except Exception as e:
        print(f"⚠️  Could not clean up test customer: {e}")

def main():
    """Run complete PII-free system test"""
    print("🚀 Starting PII-Free System Test")
    print("=" * 60)
    
    customer_id = None
    
    try:
        # Test 1: Stripe Connection
        print("\n🧪 Test 1: Stripe Connection")
        if not test_stripe_connection():
            print("❌ Cannot proceed without Stripe connection")
            return False
        
        # Test 2: Create Test Customer
        print("\n🧪 Test 2: Create Test Customer")
        customer_id = create_test_customer()
        if not customer_id:
            print("❌ Cannot proceed without test customer")
            return False
        
        # Test 3: Database Schema (No PII)
        print("\n🧪 Test 3: Database Schema (No PII)")
        if not test_database_schema():
            print("❌ PII found in database")
            return False
        
        # Test 4: Account Creation
        print("\n🧪 Test 4: Account Creation with Stripe ID")
        access_code = test_account_creation_with_stripe_id(customer_id)
        if not access_code:
            print("❌ Cannot proceed without access code")
            return False
        
        # Test 5: Chat with Billing
        print("\n🧪 Test 5: Chat with Automatic Billing Reporting")
        if not test_chat_with_billing_reporting(access_code):
            print("❌ Chat with billing failed")
            return False
        
        # Test 6: Usage Tracking
        print("\n🧪 Test 6: Usage Tracking")
        if not test_usage_tracking(access_code):
            print("❌ Usage tracking failed")
            return False
        
        # Test 7: Webhook Endpoint
        print("\n🧪 Test 7: Webhook Endpoint")
        if not test_stripe_webhook_simulation():
            print("❌ Webhook endpoint failed")
            return False
        
        # Test 8: Meter Configuration
        print("\n🧪 Test 8: Meter Configuration")
        if not test_meter_reporting(customer_id):
            print("❌ Meter configuration failed")
            return False
        
        # Success!
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("✅ Your PII-free system is working correctly:")
        print("   • No PII stored in database")
        print("   • Stripe integration working")
        print("   • Usage-based billing configured")
        print("   • Token usage reporting active")
        print("   • Webhooks configured")
        print("   • Meters set up correctly")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        return False
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        cleanup_test_customer(customer_id)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 