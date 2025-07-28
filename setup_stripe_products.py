#!/usr/bin/env python3
"""
Setup Stripe Products Script
Creates products and prices with proper metadata for the PII-free system
"""

import os
import stripe
from datetime import datetime

def setup_stripe_products():
    """Create products and prices with proper metadata"""
    
    if not os.getenv("STRIPE_SECRET_KEY"):
        print("❌ STRIPE_SECRET_KEY not set")
        print("💡 Set it with: export STRIPE_SECRET_KEY=sk_test_...")
        return False
    
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    print("🏗️  Setting up Stripe products and prices...")
    print("=" * 50)
    
    try:
        # Product 1: Free Trial
        print("\n1️⃣ Creating Free Trial Product...")
        free_product = stripe.Product.create(
            name="RgentAI Free Trial",
            description="Free trial - 50 requests (one-time trial). Claude 3.5 Haiku – Fastest & most cost-effective. No card or payment required.",
            metadata={
                'plan_type': 'free_trial',
                'pricing_model': 'one_time_trial',
                'model': 'haiku',
                'trial_requests': '50',
                'trial_type': 'one_time',
                'no_payment_required': 'true'
            }
        )
        print(f"✅ Created product: {free_product.name} (ID: {free_product.id})")
        
        # Free Trial Price
        free_price = stripe.Price.create(
            product=free_product.id,
            unit_amount=0,  # $0
            currency='usd',
            recurring=None,  # One-time
            lookup_key='free_trial',
            metadata={
                'plan_type': 'free_trial',
                'pricing_model': 'one_time_trial',
                'model': 'haiku',
                'trial_requests': '50',
                'trial_type': 'one_time',
                'no_payment_required': 'true'
            }
        )
        print(f"✅ Created price: $0 (Lookup Key: {free_price.lookup_key})")
        
        # Product 2: Pro Haiku
        print("\n2️⃣ Creating Pro Haiku Product...")
        haiku_product = stripe.Product.create(
            name="RgentAI Pro (Haiku)",
            description="Pro plan with Claude 3.5 Haiku – Fastest & most cost-effective. Perfect for simple tasks & high volume.",
            metadata={
                'plan_type': 'pro_haiku',
                'pricing_model': 'subscription_plus_tokens',
                'model': 'haiku',
                'monthly_subscription': '10.0',
                'input_token_rate': '0.0013',
                'output_token_rate': '0.0065',
                'tokens_per_1000_input': '0.0013',
                'tokens_per_1000_output': '0.0065',
                'estimated_prompts_per_10_dollars': '1500'
            }
        )
        print(f"✅ Created product: {haiku_product.name} (ID: {haiku_product.id})")
        
        # Pro Haiku Price
        haiku_price = stripe.Price.create(
            product=haiku_product.id,
            unit_amount=1000,  # $10.00
            currency='usd',
            recurring={'interval': 'month'},
            lookup_key='pro_haiku_monthly_base',
            metadata={
                'plan_type': 'pro_haiku',
                'pricing_model': 'subscription_plus_tokens',
                'model': 'haiku',
                'monthly_subscription': '10.0',
                'input_token_rate': '0.0013',
                'output_token_rate': '0.0065',
                'tokens_per_1000_input': '0.0013',
                'tokens_per_1000_output': '0.0065',
                'estimated_prompts_per_10_dollars': '1500'
            }
        )
        print(f"✅ Created price: $10/month (Lookup Key: {haiku_price.lookup_key})")
        
        # Product 3: Pro Sonnet
        print("\n3️⃣ Creating Pro Sonnet Product...")
        sonnet_product = stripe.Product.create(
            name="RgentAI Pro (Sonnet)",
            description="Pro plan with Claude 3.5 Sonnet – Advanced reasoning & coding. Perfect for complex analysis.",
            metadata={
                'plan_type': 'pro_sonnet',
                'pricing_model': 'subscription_plus_tokens',
                'model': 'sonnet',
                'monthly_subscription': '10.0',
                'input_token_rate': '0.005',
                'output_token_rate': '0.02',
                'tokens_per_1000_input': '0.005',
                'tokens_per_1000_output': '0.02',
                'estimated_prompts_per_10_dollars': '400'
            }
        )
        print(f"✅ Created product: {sonnet_product.name} (ID: {sonnet_product.id})")
        
        # Pro Sonnet Price
        sonnet_price = stripe.Price.create(
            product=sonnet_product.id,
            unit_amount=1000,  # $10.00 (same as Haiku)
            currency='usd',
            recurring={'interval': 'month'},
            lookup_key='pro_sonnet_monthly_base',
            metadata={
                'plan_type': 'pro_sonnet',
                'pricing_model': 'subscription_plus_tokens',
                'model': 'sonnet',
                'monthly_subscription': '10.0',
                'input_token_rate': '0.005',
                'output_token_rate': '0.02',
                'tokens_per_1000_input': '0.005',
                'tokens_per_1000_output': '0.02',
                'estimated_prompts_per_10_dollars': '400'
            }
        )
        print(f"✅ Created price: $10/month (Lookup Key: {sonnet_price.lookup_key})")
        
        print("\n" + "=" * 50)
        print("✅ All products and prices created successfully!")
        
        # Summary
        print("\n📋 Summary:")
        print(f"   • Free Trial: {free_product.name} - $0 (50 requests, one-time)")
        print(f"   • Pro Haiku: {haiku_product.name} - $10/month + pay per token")
        print(f"   • Pro Sonnet: {sonnet_product.name} - $10/month + pay per token")
        print(f"   • Lookup Keys: {free_price.lookup_key}, {haiku_price.lookup_key}, {sonnet_price.lookup_key}")
        print(f"   • Haiku Token Rates: $0.0013/1K input, $0.0065/1K output (~1,500 prompts/$10)")
        print(f"   • Sonnet Token Rates: $0.005/1K input, $0.02/1K output (~400 prompts/$10)")
        
        return True
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_test_customer():
    """Create a test customer with proper metadata"""
    
    if not os.getenv("STRIPE_SECRET_KEY"):
        print("❌ STRIPE_SECRET_KEY not set")
        return False
    
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    print("\n🧪 Creating test customer...")
    
    try:
        # Create test customer
        customer = stripe.Customer.create(
            email=f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}@example.com",
            metadata={
                'plan_type': 'free',
                'created_at': datetime.now().isoformat(),
                'test_customer': 'true'
            }
        )
        
        print(f"✅ Created test customer: {customer.email}")
        print(f"   ID: {customer.id}")
        print(f"   Metadata: {customer.metadata}")
        
        return customer.id
        
    except Exception as e:
        print(f"❌ Error creating test customer: {e}")
        return False

def main():
    print("🏗️  Stripe Products Setup Tool")
    print("=" * 50)
    
    # Check if Stripe is configured
    if not os.getenv("STRIPE_SECRET_KEY"):
        print("❌ STRIPE_SECRET_KEY not set")
        print("💡 Set it with: export STRIPE_SECRET_KEY=sk_test_...")
        return
    
    print("Options:")
    print("1. Create products and prices with metadata")
    print("2. Create test customer")
    print("3. Run both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        setup_stripe_products()
    elif choice == "2":
        create_test_customer()
    elif choice == "3":
        print("\n🏗️  Running complete setup...")
        setup_stripe_products()
        create_test_customer()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main() 