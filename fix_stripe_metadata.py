#!/usr/bin/env python3
"""
Fix Stripe Customer Metadata Script
Adds missing metadata to existing customers and updates code to set metadata properly
"""

import os
import stripe
from datetime import datetime

def fix_existing_customers():
    """Add metadata to existing customers that don't have it"""
    
    if not os.getenv("STRIPE_SECRET_KEY"):
        print("❌ STRIPE_SECRET_KEY not set")
        return False
    
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    print("🔧 Fixing existing customer metadata...")
    print("=" * 50)
    
    try:
        # Get all customers
        customers = stripe.Customer.list(limit=100)
        print(f"Found {len(customers.data)} customers")
        
        fixed_count = 0
        skipped_count = 0
        
        for customer in customers.data:
            print(f"\n📧 Customer: {customer.email} (ID: {customer.id})")
            
            # Check if customer has metadata
            if customer.metadata and 'plan_type' in customer.metadata:
                print("   ✅ Already has metadata - skipping")
                skipped_count += 1
                continue
            
            # Determine plan type based on subscriptions
            plan_type = 'free'  # default
            
            if customer.subscriptions and customer.subscriptions.data:
                subscription = customer.subscriptions.data[0]
                if subscription.status == 'active':
                    # Try to determine plan from subscription
                    if hasattr(subscription, 'metadata') and subscription.metadata:
                        plan_type = subscription.metadata.get('plan_type', 'pro')
                    else:
                        # Check price lookup key
                        if subscription.items.data:
                            price = subscription.items.data[0].price
                            if hasattr(price, 'lookup_key') and price.lookup_key:
                                if 'haiku' in price.lookup_key:
                                    plan_type = 'pro_haiku'
                                elif 'sonnet' in price.lookup_key:
                                    plan_type = 'pro_sonnet'
                                else:
                                    plan_type = 'pro'
            
            # Add metadata to customer
            metadata = {
                'plan_type': plan_type,
                'created_at': datetime.fromtimestamp(customer.created).isoformat(),
                'fixed_at': datetime.now().isoformat()
            }
            
            print(f"   🔧 Adding metadata: {metadata}")
            
            # Update customer with metadata
            updated_customer = stripe.Customer.modify(
                customer.id,
                metadata=metadata
            )
            
            print(f"   ✅ Updated successfully")
            fixed_count += 1
        
        print("\n" + "=" * 50)
        print(f"✅ Fixed {fixed_count} customers")
        print(f"⏭️  Skipped {skipped_count} customers (already had metadata)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_test_customer():
    """Create a test customer with proper metadata"""
    
    if not os.getenv("STRIPE_SECRET_KEY"):
        print("❌ STRIPE_SECRET_KEY not set")
        return False
    
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    print("🧪 Creating test customer with proper metadata...")
    
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

def update_code_metadata():
    """Show the code changes needed to set metadata properly"""
    
    print("\n📝 Code Changes Needed:")
    print("=" * 50)
    
    print("""
1. Update create_account function in backend/main.py:

```python
# When creating a customer
customer = stripe.Customer.create(
    email=request.email,
    metadata={
        'plan_type': request.plan_type,
        'created_at': datetime.now().isoformat(),
        'access_code': access_code  # Add this for easier lookup
    }
)
```

2. Update checkout session creation:

```python
checkout_session = stripe.checkout.Session.create(
    # ... other parameters ...
    metadata={
        'plan_type': request.plan_type,
        'requests': str(request.requests),
        'customer_email': request.customer_email or '',
        'lookup_key': request.lookup_key if hasattr(request, 'lookup_key') else ''
    }
)
```

3. Update webhook handling to set subscription metadata:

```python
# In webhook handler for subscription creation
subscription = stripe.Subscription.modify(
    subscription.id,
    metadata={
        'plan_type': plan_type,
        'lookup_key': lookup_key
    }
)
```
""")

def main():
    print("🔧 Stripe Metadata Fix Tool")
    print("=" * 50)
    
    # Check if Stripe is configured
    if not os.getenv("STRIPE_SECRET_KEY"):
        print("❌ STRIPE_SECRET_KEY not set")
        print("💡 Set it with: export STRIPE_SECRET_KEY=sk_test_...")
        return
    
    print("Options:")
    print("1. Fix existing customers (add metadata)")
    print("2. Create test customer with metadata")
    print("3. Show code changes needed")
    print("4. Run all fixes")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        fix_existing_customers()
    elif choice == "2":
        create_test_customer()
    elif choice == "3":
        update_code_metadata()
    elif choice == "4":
        print("\n🔧 Running all fixes...")
        fix_existing_customers()
        create_test_customer()
        update_code_metadata()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main() 