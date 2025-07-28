#!/usr/bin/env python3
"""
Test Stripe Products and Prices
Check what's available in your Stripe account
"""

import os
import stripe

# Set up Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def check_stripe_products():
    """Check what products and prices exist in Stripe"""
    print("🔍 Checking Stripe Products and Prices...")
    print("=" * 50)
    
    try:
        # Get all products
        print("\n📦 PRODUCTS:")
        products = stripe.Product.list(limit=10)
        for product in products.data:
            print(f"  • {product.name} (ID: {product.id})")
            print(f"    Active: {product.active}")
            print(f"    Metadata: {product.metadata}")
            print()
        
        # Get all prices
        print("\n💰 PRICES:")
        prices = stripe.Price.list(limit=20)
        for price in prices.data:
            print(f"  • {price.nickname or 'No name'} (ID: {price.id})")
            print(f"    Product: {price.product}")
            print(f"    Active: {price.active}")
            print(f"    Unit Amount: {price.unit_amount} {price.currency}")
            print(f"    Recurring: {price.recurring}")
            print(f"    Lookup Key: {price.lookup_key}")
            print(f"    Metadata: {price.metadata}")
            print()
        
        # Check for specific lookup keys we need
        print("\n🔑 LOOKUP KEYS WE NEED:")
        required_keys = [
            'free_trial_monthly',
            'pro_haiku_monthly_base', 
            'pro_haiku_input_tokens',
            'pro_haiku_output_tokens',
            'pro_sonnet_monthly_base',
            'pro_sonnet_input_tokens', 
            'pro_sonnet_output_tokens'
        ]
        
        for key in required_keys:
            try:
                price = stripe.Price.retrieve(key)
                print(f"  ✅ {key}: {price.id} (Active: {price.active})")
            except stripe.error.InvalidRequestError:
                print(f"  ❌ {key}: Not found")
            except Exception as e:
                print(f"  ⚠️  {key}: Error - {str(e)}")
        
        print("\n" + "=" * 50)
        print("✅ Stripe connection successful!")
        
    except Exception as e:
        print(f"❌ Error checking Stripe: {str(e)}")

if __name__ == "__main__":
    check_stripe_products() 