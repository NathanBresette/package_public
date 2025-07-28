# Environment Variables Configuration Guide

## Required Environment Variables for PII-Free System

### 🔑 **Core API Keys**

#### **Claude API (Required for AI functionality)**
```bash
CLAUDE_API_KEY=sk-ant-api03-...
```
- **Purpose**: Enables AI chat functionality
- **Source**: https://console.anthropic.com/
- **Note**: Without this, the system will return mock responses

#### **Stripe Configuration (Required for Phase 2 - Payments)**
```bash
STRIPE_SECRET_KEY=sk_test_... or sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_test_... or pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```
- **Purpose**: Enables payment processing and customer management
- **Source**: https://dashboard.stripe.com/apikeys
- **Note**: Without these, payment features will be disabled (502 errors)

### 🗄️ **Database Configuration**

#### **PostgreSQL (Required for user management)**
```bash
DATABASE_URL=postgresql://username:password@host:port/database
```
- **Purpose**: Stores user data, usage tracking, and billing information
- **Note**: Must be configured for the system to work

### 🔐 **Security & Admin**

#### **Admin Access (Required for admin functions)**
```bash
ADMIN_ACCESS_CODE=your-secure-admin-code
```
- **Purpose**: Enables admin dashboard and user management
- **Default**: "admin123" (change in production)

### 📧 **Email Configuration (Optional - for password reset)**
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```
- **Purpose**: Password reset functionality
- **Note**: Optional - system works without email

## 🚀 **Deployment Configuration**

### **For Render.com Deployment**
Add these environment variables in your Render dashboard:

1. Go to your service dashboard
2. Navigate to "Environment" tab
3. Add each variable above

### **For Local Development**
Create a `.env` file in the backend directory:
```bash
# Core API Keys
CLAUDE_API_KEY=sk-ant-api03-...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Database
DATABASE_URL=postgresql://username:password@host:port/database

# Admin
ADMIN_ACCESS_CODE=your-secure-admin-code

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 🔍 **Testing Without Stripe**

If you want to test the system without Stripe integration:

1. **Don't set** the Stripe environment variables
2. The system will show: `⚠️  STRIPE_SECRET_KEY not set. Payment features will be disabled.`
3. All other functionality will work normally
4. Payment-related endpoints will return 502 errors (expected)

## ✅ **Verification**

After setting environment variables, restart your backend and check the startup logs:

```
✅ Stripe configured successfully
🚀 RStudio AI Backend v1.3.0 starting up...
DEBUG: CLAUDE_API_KEY is set (length: 108)
DEBUG: CLAUDE_API_KEY preview: sk-ant-api...
```

## 🛡️ **Security Notes**

1. **Never commit** `.env` files to git
2. Use **test keys** for development
3. Use **live keys** only in production
4. Rotate keys regularly
5. Use strong admin access codes

## 📋 **Phase-Specific Requirements**

### **Phase 1: Database & Data Storage** ✅
- `DATABASE_URL` (Required)

### **Phase 2: Stripe Integration** ⚠️
- `STRIPE_SECRET_KEY` (Required)
- `STRIPE_PUBLISHABLE_KEY` (Required)
- `STRIPE_WEBHOOK_SECRET` (Required)

### **Phase 4: Context Processing** ✅
- `CLAUDE_API_KEY` (Required for AI responses)
- No additional variables needed

### **Admin Functions** ⚠️
- `ADMIN_ACCESS_CODE` (Required for admin dashboard) 