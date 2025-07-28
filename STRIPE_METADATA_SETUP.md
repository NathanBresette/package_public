# Stripe Metadata Setup Guide

## 🔍 **Current Metadata Fields Your Code Expects**

Based on your code analysis, here are the metadata fields your system is trying to access:

### **1. Customer Metadata (Set during account creation)**
```javascript
{
  'plan_type': 'free' | 'pro' | 'pro_haiku' | 'pro_sonnet',
  'created_at': '2024-01-01T00:00:00.000Z'
}
```

### **2. Checkout Session Metadata (Set during payment)**
```javascript
{
  'plan_type': 'free' | 'pro' | 'pro_haiku' | 'pro_sonnet',
  'requests': '500',  // string
  'customer_email': 'user@example.com',
  'lookup_key': 'pro_haiku_monthly_base' | 'pro_sonnet_monthly_base'
}
```

### **3. Subscription Metadata (Set during subscription creation)**
```javascript
{
  'lookup_key': 'pro_haiku_monthly_base' | 'pro_sonnet_monthly_base',
  'plan_type': 'pro_haiku' | 'pro_sonnet'
}
```

### **4. Payment Intent Metadata (Set during payment processing)**
```javascript
{
  'subscription_id': 'sub_1234567890'
}
```

## 🛠️ **How to Check Your Stripe Configuration**

### **Step 1: Access Your Stripe Dashboard**
1. Go to https://dashboard.stripe.com/
2. Make sure you're in the correct mode (Test/Live)

### **Step 2: Check Customer Metadata**
1. Navigate to **Customers** in the left sidebar
2. Click on any customer
3. Scroll down to **Metadata** section
4. **Expected fields**: `plan_type`, `created_at`

### **Step 3: Check Product/Price Configuration**
1. Navigate to **Products** in the left sidebar
2. Check if you have products with these lookup keys:
   - `pro_haiku_monthly_base`
   - `pro_sonnet_monthly_base`

### **Step 4: Check Webhook Configuration**
1. Navigate to **Developers > Webhooks**
2. Verify you have a webhook endpoint configured
3. **Required events**:
   - `invoice.paid`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`

### **Step 5: Check API Keys**
1. Navigate to **Developers > API keys**
2. Verify you have:
   - **Publishable key** (starts with `pk_`)
   - **Secret key** (starts with `sk_`)

## 🔧 **How to Fix Missing Metadata**

### **Option 1: Update Your Code to Set Metadata Properly**

Your current code is setting some metadata, but let's make sure it's comprehensive:

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

# When creating checkout session
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

### **Option 2: Add Missing Products/Prices in Stripe**

If you don't have the lookup keys set up:

1. **Create Products**:
   - Product: "RgentAI Pro Haiku"
   - Product: "RgentAI Pro Sonnet"

2. **Create Prices with Lookup Keys**:
   - Price: $10/month for Haiku
   - Lookup Key: `pro_haiku_monthly_base`
   - Price: $20/month for Sonnet  
   - Lookup Key: `pro_sonnet_monthly_base`

### **Option 3: Test with Existing Data**

You can also test with your existing Stripe data by checking what metadata is actually there:

```python
# Add this to your code temporarily to debug
@app.get("/api/debug/stripe-customer/{customer_id}")
async def debug_stripe_customer(customer_id: str):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        customer = stripe.Customer.retrieve(customer_id)
        return {
            "customer_id": customer.id,
            "email": customer.email,
            "metadata": customer.metadata,
            "subscriptions": [sub.id for sub in customer.subscriptions.data]
        }
    except Exception as e:
        return {"error": str(e)}
```

## 🧪 **Quick Test Script**

Create this test script to check your Stripe configuration:

```python
import stripe
import os

# Set your Stripe key
stripe.api_key = "sk_test_..."  # Your test secret key

def test_stripe_config():
    try:
        # Test 1: List customers
        customers = stripe.Customer.list(limit=5)
        print(f"✅ Found {len(customers.data)} customers")
        
        # Test 2: Check customer metadata
        if customers.data:
            customer = customers.data[0]
            print(f"📧 Customer email: {customer.email}")
            print(f"🏷️  Customer metadata: {customer.metadata}")
        
        # Test 3: List products
        products = stripe.Product.list(limit=5)
        print(f"✅ Found {len(products.data)} products")
        
        # Test 4: List prices with lookup keys
        prices = stripe.Price.list(limit=10)
        lookup_keys = [price.lookup_key for price in prices.data if price.lookup_key]
        print(f"🔑 Lookup keys found: {lookup_keys}")
        
        # Test 5: List webhooks
        webhooks = stripe.WebhookEndpoint.list(limit=5)
        print(f"✅ Found {len(webhooks.data)} webhooks")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_stripe_config()
```

## 🚨 **Common Issues & Solutions**

### **Issue 1: "Customer not found" errors**
- **Cause**: Customer metadata doesn't match what code expects
- **Solution**: Check customer metadata in Stripe dashboard

### **Issue 2: "Price not found for lookup key" errors**
- **Cause**: Lookup keys not configured in Stripe
- **Solution**: Create prices with proper lookup keys

### **Issue 3: Webhook signature verification fails**
- **Cause**: `STRIPE_WEBHOOK_SECRET` not set correctly
- **Solution**: Copy webhook secret from Stripe dashboard

### **Issue 4: Metadata fields are empty**
- **Cause**: Code not setting metadata during creation
- **Solution**: Update code to set all required metadata fields

## 📋 **Checklist for Complete Setup**

- [ ] Stripe API keys configured in environment
- [ ] Products created in Stripe dashboard
- [ ] Prices created with lookup keys
- [ ] Webhook endpoint configured
- [ ] Webhook secret set in environment
- [ ] Customer metadata being set during creation
- [ ] Checkout session metadata being set
- [ ] Subscription metadata being set
- [ ] Test with real Stripe test data

Run the test script above to verify your configuration! 