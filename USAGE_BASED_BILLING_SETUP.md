# Stripe Usage-Based Billing Setup Guide

## 🎯 **Overview**
This guide shows you how to set up automatic usage-based billing where customers pay $10/month subscription + token usage billed monthly.

## 📋 **Step-by-Step Setup**

### **Step 1: Create Usage-Based Prices in Stripe Dashboard**

**Go to Stripe Dashboard → Products → Edit each Pro product:**

#### **For Pro Haiku Product:**
1. **Click "Add price"**
2. **Set pricing model:** "Usage-based"
3. **Billing:** "Per unit"
4. **Unit price:** $0.0013 per 1000 input tokens
5. **Click "Add price"**
6. **Repeat for output tokens:** $0.0065 per 1000 output tokens

#### **For Pro Sonnet Product:**
1. **Click "Add price"**
2. **Set pricing model:** "Usage-based"
3. **Billing:** "Per unit"
4. **Unit price:** $0.005 per 1000 input tokens
5. **Click "Add price"**
6. **Repeat for output tokens:** $0.02 per 1000 output tokens

### **Step 2: Update Price IDs in Code**

After creating the usage-based prices, copy their IDs and update the `stripe_billing.py` file:

```python
def get_usage_price_ids(plan_type: str) -> Dict[str, str]:
    """Get the usage-based price IDs for a plan type"""
    price_ids = {
        'pro_haiku': {
            'input_tokens': 'price_1234567890',  # Replace with actual price ID
            'output_tokens': 'price_0987654321'  # Replace with actual price ID
        },
        'pro_sonnet': {
            'input_tokens': 'price_abcdef1234',  # Replace with actual price ID
            'output_tokens': 'price_1234defabc'  # Replace with actual price ID
        }
    }
    return price_ids.get(plan_type, {})
```

### **Step 3: Create Subscription with Usage-Based Items**

When a customer subscribes, you need to create a subscription with both:
- **Base subscription price** ($10/month)
- **Usage-based prices** (for token billing)

```python
# Create subscription with usage-based items
subscription = stripe.Subscription.create(
    customer=customer_id,
    items=[
        {
            'price': 'price_base_subscription',  # $10/month base
        },
        {
            'price': 'price_input_haiku',  # Usage-based input tokens
        },
        {
            'price': 'price_output_haiku',  # Usage-based output tokens
        }
    ],
    payment_behavior='default_incomplete',
    expand=['latest_invoice.payment_intent']
)
```

### **Step 4: Report Usage Automatically**

Your backend now automatically reports token usage after each API call:

```python
# This happens automatically in your chat endpoint
report_token_usage(
    customer_id,
    input_tokens,
    output_tokens
)
```

## 🧪 **Testing the Setup**

### **Test 1: Create Test Subscription**
```bash
python3 setup_stripe_products.py
# Choose option to create test customer and subscription
```

### **Test 2: Make API Calls**
```bash
# Make chat requests to test token reporting
curl -X POST https://rgent.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"access_code": "test123", "prompt": "Hello world"}'
```

### **Test 3: Check Usage in Stripe**
1. **Go to Stripe Dashboard** → **Subscriptions**
2. **Click on test subscription**
3. **Check "Usage" tab** - should show reported token usage

## 📊 **How Billing Works**

### **Monthly Billing Cycle:**
1. **Customer subscribes** → $10/month base charge
2. **Customer uses API** → Token usage reported to Stripe
3. **Monthly invoice** → $10 + token usage charges
4. **Automatic payment** → Stripe charges customer

### **Example Customer Bill:**
```
Base Subscription: $10.00
Input Tokens (5,000): $0.0065
Output Tokens (2,000): $0.013
Total: $10.0195
```

## 🔧 **Configuration Files**

### **Environment Variables:**
```bash
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_...
```

### **Price IDs to Update:**
- `price_input_haiku` - Input token price for Haiku
- `price_output_haiku` - Output token price for Haiku
- `price_input_sonnet` - Input token price for Sonnet
- `price_output_sonnet` - Output token price for Sonnet

## 🚨 **Important Notes**

### **Free Trial:**
- No subscription required
- No token billing
- Just track 50 requests limit

### **Pro Plans:**
- Require subscription
- Automatic token billing
- Monthly invoices

### **Error Handling:**
- If token reporting fails, API calls still work
- Billing errors don't break the service
- Usage is logged locally as backup

## ✅ **Verification Checklist**

- [ ] Usage-based prices created in Stripe
- [ ] Price IDs updated in `stripe_billing.py`
- [ ] Webhook configured for subscription events
- [ ] Test subscription created successfully
- [ ] Token usage reporting working
- [ ] Monthly billing cycle configured
- [ ] Error handling implemented

## 🎉 **Benefits**

- ✅ **Automatic billing** - No manual work
- ✅ **Accurate pricing** - Pay for actual usage
- ✅ **Professional invoices** - Stripe handles everything
- ✅ **Real-time tracking** - Usage reported immediately
- ✅ **Scalable** - Works for any number of customers

Your system will now automatically bill customers monthly for their token usage while maintaining the $10/month subscription fee! 