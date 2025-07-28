#!/usr/bin/env python3
"""
Stripe Configuration Test Script
Checks your Stripe setup and metadata configuration
"""

import os
import stripe
from datetime import datetime

def test_stripe_config():
    """Test Stripe configuration and metadata setup"""
    
    # Check if Stripe key is set
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        print("❌ STRIPE_SECRET_KEY not found in environment")
        print("💡 Set it with: export STRIPE_SECRET_KEY=sk_test_...")
        return False
    
    # Configure Stripe
    stripe.api_key = stripe_key
    
    print("🔍 Testing Stripe Configuration...")
    print("=" * 50)
    
    try:
        # Test 1: API Key validity
        print("1️⃣ Testing API key...")
        account = stripe.Account.retrieve()
        print(f"✅ API key valid - Account: {account.id}")
        
        # Test 2: List customers
        print("\n2️⃣ Checking customers...")
        customers = stripe.Customer.list(limit=5)
        print(f"✅ Found {len(customers.data)} customers")
        
        # Test 3: Check customer metadata
        if customers.data:
            customer = customers.data[0]
            print(f"📧 Sample customer: {customer.email}")
            print(f"🏷️  Customer metadata: {customer.metadata}")
            
            if not customer.metadata:
                print("⚠️  Warning: Customer has no metadata")
            else:
                expected_fields = ['plan_type', 'created_at']
                missing_fields = [field for field in expected_fields if field not in customer.metadata]
                if missing_fields:
                    print(f"⚠️  Missing metadata fields: {missing_fields}")
                else:
                    print("✅ Customer metadata looks good")
        
        # Test 4: List products
        print("\n3️⃣ Checking products...")
        products = stripe.Product.list(limit=10)
        print(f"✅ Found {len(products.data)} products")
        
        for product in products.data:
            print(f"   📦 {product.name} (ID: {product.id})")
        
        # Test 5: List prices with lookup keys
        print("\n4️⃣ Checking prices and lookup keys...")
        prices = stripe.Price.list(limit=20)
        lookup_keys = [price.lookup_key for price in prices.data if price.lookup_key]
        
        print(f"✅ Found {len(prices.data)} prices")
        print(f"🔑 Lookup keys found: {lookup_keys}")
        
        # Check for expected lookup keys
        expected_lookup_keys = ['pro_haiku_monthly_base', 'pro_sonnet_monthly_base']
        missing_keys = [key for key in expected_lookup_keys if key not in lookup_keys]
        
        if missing_keys:
            print(f"⚠️  Missing expected lookup keys: {missing_keys}")
        else:
            print("✅ All expected lookup keys found")
        
        # Test 6: List webhooks
        print("\n5️⃣ Checking webhooks...")
        webhooks = stripe.WebhookEndpoint.list(limit=5)
        print(f"✅ Found {len(webhooks.data)} webhooks")
        
        for webhook in webhooks.data:
            print(f"   🔗 {webhook.url}")
            print(f"      Events: {webhook.enabled_events}")
        
        # Test 7: Check webhook secret
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if webhook_secret:
            print("✅ STRIPE_WEBHOOK_SECRET is set")
        else:
            print("⚠️  STRIPE_WEBHOOK_SECRET not set")
        
        # Test 8: Test customer creation (dry run)
        print("\n6️⃣ Testing customer creation metadata...")
        test_customer_data = {
            'email': 'test@example.com',
            'metadata': {
                'plan_type': 'free',
                'created_at': datetime.now().isoformat(),
                'test': 'true'
            }
        }
        print(f"📝 Would create customer with metadata: {test_customer_data['metadata']}")
        
        print("\n" + "=" * 50)
        print("✅ Stripe configuration test completed!")
        
        # Summary
        print("\n📋 Summary:")
        print(f"   • API Key: ✅ Valid")
        print(f"   • Customers: {len(customers.data)} found")
        print(f"   • Products: {len(products.data)} found")
        print(f"   • Prices: {len(prices.data)} found")
        print(f"   • Lookup Keys: {len(lookup_keys)} found")
        print(f"   • Webhooks: {len(webhooks.data)} found")
        
        return True
        
    except stripe.error.AuthenticationError:
        print("❌ Authentication failed - check your API key")
        return False
    except stripe.error.PermissionError:
        print("❌ Permission denied - check your API key permissions")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def debug_customer(customer_id):
    """Debug a specific customer's metadata"""
    if not os.getenv("STRIPE_SECRET_KEY"):
        print("❌ STRIPE_SECRET_KEY not set")
        return
    
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    try:
        customer = stripe.Customer.retrieve(customer_id)
        print(f"\n🔍 Customer Debug: {customer_id}")
        print("=" * 40)
        print(f"Email: {customer.email}")
        print(f"Created: {datetime.fromtimestamp(customer.created)}")
        print(f"Metadata: {customer.metadata}")
        
        # Check subscriptions
        subscriptions = stripe.Subscription.list(customer=customer.id)
        print(f"Subscriptions: {len(subscriptions.data)}")
        
        for sub in subscriptions.data:
            print(f"  📦 {sub.id} - Status: {sub.status}")
            print(f"     Metadata: {sub.metadata}")
            
    except Exception as e:
        print(f"❌ Error retrieving customer: {e}")

if __name__ == "__main__":
    print("🧪 Stripe Configuration Test")
    print("=" * 50)
    
    # Run main test
    success = test_stripe_config()
    
    if success:
        print("\n💡 Next steps:")
        print("1. Check the metadata fields in your Stripe dashboard")
        print("2. Create missing products/prices if needed")
        print("3. Set up webhooks if not configured")
        print("4. Update your code to set proper metadata")
        
        # Option to debug specific customer
        customer_id = input("\n🔍 Enter a customer ID to debug (or press Enter to skip): ").strip()
        if customer_id:
            debug_customer(customer_id)
    else:
        print("\n❌ Fix the issues above before proceeding") 