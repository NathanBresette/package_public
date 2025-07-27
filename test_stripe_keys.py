#!/usr/bin/env python3
"""
Quick Stripe Key Test
Tests if Stripe keys are properly configured
"""

import os
import stripe

def test_stripe_config():
    """Test Stripe configuration"""
    print("🔍 Testing Stripe Configuration...")
    
    # Check environment variables
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    print(f"STRIPE_SECRET_KEY: {'✅ Set' if secret_key else '❌ Not set'}")
    print(f"STRIPE_WEBHOOK_SECRET: {'✅ Set' if webhook_secret else '❌ Not set'}")
    
    if secret_key:
        print(f"Secret key starts with: {secret_key[:10]}...")
        if secret_key.startswith('sk_test_'):
            print("✅ Using test key (correct for development)")
        elif secret_key.startswith('sk_live_'):
            print("⚠️  Using live key (be careful!)")
        else:
            print("❌ Invalid key format")
    
    # Test Stripe connection
    if secret_key:
        try:
            stripe.api_key = secret_key
            customers = stripe.Customer.list(limit=1)
            print("✅ Stripe connection successful")
            return True
        except Exception as e:
            print(f"❌ Stripe connection failed: {e}")
            return False
    else:
        print("❌ Cannot test connection - no secret key")
        return False

if __name__ == "__main__":
    test_stripe_config() 