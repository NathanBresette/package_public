# Stripe Dashboard Metadata Setup Guide

## 🎯 **Why Set Metadata in Stripe Dashboard?**

Setting metadata in Stripe dashboard is:
- ✅ **More secure** - No sensitive data in your code
- ✅ **Easier to manage** - Visual interface
- ✅ **Automatic** - Stripe handles it for you
- ✅ **Consistent** - Same metadata across all customers

## 📋 **Step-by-Step Setup**

### **Step 1: Create Products with Metadata**

1. **Go to Stripe Dashboard** → **Products**
2. **Create/Edit each product:**

   **Product: RgentAI Free**
   - Name: "RgentAI Free Plan"
   - Description: "Free tier with limited requests"
   - **Metadata:**
     ```
     plan_type: free
     requests: 50
     daily_limit: 50
     ```

   **Product: RgentAI Pro Haiku**
   - Name: "RgentAI Pro Haiku"
   - Description: "Pro plan with Haiku model"
   - **Metadata:**
     ```
     plan_type: pro_haiku
     requests: 1000
     daily_limit: 1000
     model: haiku
     ```

   **Product: RgentAI Pro Sonnet**
   - Name: "RgentAI Pro Sonnet"
   - Description: "Pro plan with Sonnet model"
   - **Metadata:**
     ```
     plan_type: pro_sonnet
     requests: 1000
     daily_limit: 1000
     model: sonnet
     ```

### **Step 2: Create Prices with Lookup Keys**

1. **For each product, create a price:**
   
   **Free Plan Price:**
   - Amount: $0
   - Billing: One-time
   - **Lookup Key:** `free_plan`
   - **Metadata:**
     ```
     plan_type: free
     requests: 50
     ```

   **Pro Haiku Price:**
   - Amount: $10/month
   - Billing: Recurring (monthly)
   - **Lookup Key:** `pro_haiku_monthly_base`
   - **Metadata:**
     ```
     plan_type: pro_haiku
     requests: 1000
     model: haiku
     ```

   **Pro Sonnet Price:**
   - Amount: $20/month
   - Billing: Recurring (monthly)
   - **Lookup Key:** `pro_sonnet_monthly_base`
   - **Metadata:**
     ```
     plan_type: pro_sonnet
     requests: 1000
     model: sonnet
     ```

### **Step 3: Set Up Webhooks**

1. **Go to Developers** → **Webhooks**
2. **Add endpoint:** `https://your-backend.com/api/webhook`
3. **Select events:**
   - `customer.created`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`

### **Step 4: Configure Customer Metadata**

**Option A: Set Default Metadata for New Customers**

1. **Go to Settings** → **Billing** → **Customer Portal**
2. **Enable customer portal**
3. **Add default metadata** that gets applied to new customers

**Option B: Use Webhooks to Set Metadata**

Your webhook handler will automatically set metadata when subscriptions are created:

```python
# In your webhook handler
if event['type'] == 'customer.subscription.created':
    subscription = event['data']['object']
    customer_id = subscription.customer
    
    # Get plan type from subscription
    plan_type = subscription.metadata.get('plan_type', 'free')
    
    # Update customer with metadata
    stripe.Customer.modify(
        customer_id,
        metadata={
            'plan_type': plan_type,
            'subscription_id': subscription.id,
            'updated_at': datetime.now().isoformat()
        }
    )
```

### **Step 5: Test the Setup**

1. **Create a test customer** in Stripe dashboard
2. **Assign a subscription** to the customer
3. **Check that metadata is automatically set**
4. **Test your backend** with the customer

## 🔧 **Updated Backend Code**

With metadata set in Stripe, your backend code becomes much simpler:

```python
@app.post("/api/signin")
async def signin(request: SignInRequest):
    """Sign in using Stripe customer management"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Find Stripe customer by email
        customers = stripe.Customer.list(email=request.email, limit=1)
        
        if not customers.data:
            raise HTTPException(status_code=401, detail="Account not found")
        
        customer = customers.data[0]
        
        # Get plan type from customer metadata (set by Stripe)
        plan_type = 'free'  # default
        if customer.metadata and 'plan_type' in customer.metadata:
            plan_type = customer.metadata.get('plan_type')
        
        # Find user by Stripe customer ID
        user = user_manager.get_user_by_stripe_customer_id(customer.id)
        
        if not user:
            raise HTTPException(status_code=401, detail="User account not found")
        
        return {
            "success": True,
            "access_code": user.access_code,
            "plan_type": plan_type,  # From Stripe metadata
            "stripe_customer_id": customer.id,
            "billing_status": user.billing_status
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## 🧪 **Testing Your Setup**

1. **Run the test script:**
   ```bash
   python3 test_stripe_config.py
   ```

2. **Check customer metadata:**
   - Go to Customers in Stripe dashboard
   - Click on any customer
   - Verify metadata is set

3. **Test webhook events:**
   - Create a test subscription
   - Check that customer metadata is updated automatically

## 🚨 **Common Issues**

### **Issue: Metadata not being set automatically**
- **Solution:** Check webhook configuration and ensure events are being sent

### **Issue: Plan type not matching**
- **Solution:** Verify product/price metadata matches what your code expects

### **Issue: Lookup keys not found**
- **Solution:** Create prices with the exact lookup keys your code expects

## ✅ **Benefits of This Approach**

1. **Security:** No sensitive metadata in your code
2. **Maintainability:** Easy to update in Stripe dashboard
3. **Consistency:** All customers get the same metadata structure
4. **Automation:** Stripe handles metadata updates via webhooks
5. **Audit Trail:** All changes tracked in Stripe dashboard

This approach is much cleaner and follows Stripe's best practices! 