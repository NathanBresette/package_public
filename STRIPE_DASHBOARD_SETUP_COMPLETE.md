# Complete Stripe Dashboard Setup Guide

## 🎯 **Overview**
This guide walks you through setting up your Stripe dashboard to work with your PII-free system, including webhooks, customer metadata, and testing.

## 📋 **Step-by-Step Setup**

### **Step 1: API Keys Configuration**

1. **Go to Stripe Dashboard** → **Developers** → **API Keys**
2. **Copy your keys:**
   - **Publishable key** (starts with `pk_test_`)
   - **Secret key** (starts with `sk_test_`)
3. **Set environment variables:**
   ```bash
   export STRIPE_SECRET_KEY=sk_test_your_secret_key_here
   export STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
   ```

### **Step 2: Create Products and Prices**

1. **Run the setup script:**
   ```bash
   python3 setup_stripe_products.py
   ```
2. **Verify in Stripe Dashboard** → **Products**:
   - ✅ RgentAI Free Trial
   - ✅ RgentAI Pro (Haiku)
   - ✅ RgentAI Pro (Sonnet)

### **Step 3: Webhook Configuration**

1. **Go to Stripe Dashboard** → **Developers** → **Webhooks**
2. **Click "Add endpoint"**
3. **Enter endpoint URL:** `https://rgent.onrender.com/api/webhook`
4. **Select these events:**
   - ✅ `customer.created`
   - ✅ `customer.subscription.created`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `checkout.session.completed`
   - ✅ `invoice.paid`
   - ✅ `invoice.payment_failed`
5. **Click "Add endpoint"**
6. **Copy the webhook secret** (starts with `whsec_`)
7. **Set environment variable:**
   ```bash
   export STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
   ```

### **Step 4: Customer Portal Setup (Optional)**

1. **Go to Stripe Dashboard** → **Settings** → **Billing** → **Customer Portal**
2. **Enable customer portal**
3. **Configure settings:**
   - ✅ Allow customers to update payment methods
   - ✅ Allow customers to cancel subscriptions
   - ✅ Allow customers to update billing information

### **Step 5: Test the Complete Setup**

1. **Run the test script:**
   ```bash
   python3 test_stripe_config.py
   ```

2. **Create a test customer:**
   ```bash
   python3 setup_stripe_products.py
   # Choose option 2 or 3
   ```

3. **Test webhook events:**
   - Create a customer in Stripe dashboard
   - Check that metadata is automatically set
   - Verify webhook events are received

## 🔧 **What Each Webhook Event Does**

### **`customer.created`**
- Sets default metadata for new customers
- Plan type: `free_trial`
- Trial requests remaining: `50`

### **`customer.subscription.created`**
- Updates customer metadata when subscription starts
- Sets plan type based on subscription
- Links subscription ID to customer

### **`checkout.session.completed`**
- Updates customer metadata after successful checkout
- Sets plan type from session metadata
- Links checkout session ID

### **`invoice.paid`**
- Creates user account in your system
- Generates access code
- Links Stripe customer to your user

## 🧪 **Testing Your Setup**

### **Test 1: Product Creation**
```bash
python3 setup_stripe_products.py
```
**Expected output:**
```
✅ Created product: RgentAI Free Trial (ID: prod_...)
✅ Created price: $0 (Lookup Key: free_trial)
✅ Created product: RgentAI Pro (Haiku) (ID: prod_...)
✅ Created price: $10/month (Lookup Key: pro_haiku_monthly_base)
✅ Created product: RgentAI Pro (Sonnet) (ID: prod_...)
✅ Created price: $10/month (Lookup Key: pro_sonnet_monthly_base)
```

### **Test 2: Configuration Verification**
```bash
python3 test_stripe_config.py
```
**Expected output:**
```
✅ API key valid - Account: acct_...
✅ Found X customers
✅ Found 3 products
✅ Found 3 prices
✅ Found 1 webhooks
✅ STRIPE_WEBHOOK_SECRET is set
```

### **Test 3: Customer Metadata**
1. **Create a test customer in Stripe dashboard**
2. **Check customer metadata:**
   ```json
   {
     "plan_type": "free_trial",
     "created_at": "2024-01-01T00:00:00.000Z",
     "trial_requests_remaining": "50"
   }
   ```

## 🚨 **Common Issues & Solutions**

### **Issue: Webhook signature verification fails**
- **Cause:** `STRIPE_WEBHOOK_SECRET` not set correctly
- **Solution:** Copy webhook secret from Stripe dashboard

### **Issue: Customer metadata not being set**
- **Cause:** Webhook events not configured
- **Solution:** Add missing webhook events in Stripe dashboard

### **Issue: Products not found**
- **Cause:** Setup script not run
- **Solution:** Run `python3 setup_stripe_products.py`

### **Issue: API key authentication fails**
- **Cause:** Wrong API key or test/live mode mismatch
- **Solution:** Check API key and ensure you're in test mode

## 📊 **Metadata Structure**

### **Customer Metadata (Auto-set by webhooks):**
```json
{
  "plan_type": "free_trial|pro_haiku|pro_sonnet",
  "created_at": "2024-01-01T00:00:00.000Z",
  "subscription_id": "sub_...",
  "trial_requests_remaining": "50"
}
```

### **Product Metadata (Set by setup script):**
```json
{
  "plan_type": "pro_haiku",
  "pricing_model": "subscription_plus_tokens",
  "model": "haiku",
  "monthly_subscription": "10.0",
  "input_token_rate": "0.0013",
  "output_token_rate": "0.0065",
  "estimated_prompts_per_10_dollars": "1500"
}
```

## ✅ **Verification Checklist**

- [ ] API keys configured in environment
- [ ] Products created with proper metadata
- [ ] Prices created with lookup keys
- [ ] Webhook endpoint configured
- [ ] Webhook secret set in environment
- [ ] All required webhook events selected
- [ ] Test customer created successfully
- [ ] Customer metadata auto-set by webhooks
- [ ] Test script passes all checks

## 🎉 **You're Ready!**

Once you've completed all steps above, your Stripe integration will:
- ✅ Automatically set customer metadata
- ✅ Handle subscription creation/updates
- ✅ Process payments and create user accounts
- ✅ Support all three pricing plans
- ✅ Work with your PII-free system

Your backend will be able to pull all the metadata values from Stripe to determine user plans, pricing, and limits! 