"""
Stripe Usage-Based Billing Module
Handles reporting token usage to Stripe for automatic billing
"""

import os
import stripe
from datetime import datetime
from typing import Dict, Optional

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def get_customer_subscription(customer_id: str) -> Optional[stripe.Subscription]:
    """Get the active subscription for a customer"""
    try:
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status='active',
            limit=1
        )
        return subscriptions.data[0] if subscriptions.data else None
    except Exception as e:
        print(f"Error getting subscription: {e}")
        return None

def get_usage_price_ids(plan_type: str) -> Dict[str, str]:
    """Get the usage-based price IDs for a plan type"""
    # These will be the price IDs you create in Stripe dashboard
    # You'll need to replace these with your actual price IDs
    price_ids = {
        'pro_haiku': {
            'input_tokens': 'price_input_haiku',  # Replace with actual price ID for lookup_key: pro_haiku_input_tokens
            'output_tokens': 'price_output_haiku'  # Replace with actual price ID for lookup_key: pro_haiku_output_tokens
        },
            'pro_sonnet': {
        'input_tokens': 'price_input_sonnet',  # Replace with actual price ID for lookup_key: pro_sonnet_input_tokens_v2
        'output_tokens': 'price_output_sonnet'  # Replace with actual price ID for lookup_key: pro_sonnet_output_tokens_v2
    }
    }
    return price_ids.get(plan_type, {})

def report_token_usage(customer_id: str, input_tokens: int, output_tokens: int) -> bool:
    """
    Report token usage to Stripe for automatic billing
    
    Args:
        customer_id: Stripe customer ID
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
    
    Returns:
        bool: True if usage was reported successfully
    """
    try:
        # Get customer's plan type
        customer = stripe.Customer.retrieve(customer_id)
        plan_type = customer.metadata.get('plan_type')
        
        if not plan_type or plan_type == 'free_trial':
            print(f"Customer {customer_id} is on free trial - no billing needed")
            return True
        
        # Get subscription
        subscription = get_customer_subscription(customer_id)
        if not subscription:
            print(f"No active subscription for customer {customer_id}")
            return False
        
        # Report input token usage to Input Tokens meter
        if input_tokens > 0:
            stripe.MeterEvent.create(
                meter='Input Tokens',
                value=input_tokens,
                timestamp=int(datetime.now().timestamp()),
                customer=customer_id
            )
            print(f"Reported {input_tokens} input tokens to meter for customer {customer_id}")
        
        # Report output token usage to Output Tokens meter
        if output_tokens > 0:
            stripe.MeterEvent.create(
                meter='Output Tokens',
                value=output_tokens,
                timestamp=int(datetime.now().timestamp()),
                customer=customer_id
            )
            print(f"Reported {output_tokens} output tokens to meter for customer {customer_id}")
        
        return True
        
    except Exception as e:
        print(f"Error reporting token usage: {e}")
        return False

def calculate_token_cost(input_tokens: int, output_tokens: int, plan_type: str) -> float:
    """Calculate the cost of token usage for display purposes"""
    rates = {
        'pro_haiku': {
            'input_rate': 0.0013,  # per 1000 tokens
            'output_rate': 0.00533  # Updated rate
        },
        'pro_sonnet': {
            'input_rate': 0.005,
            'output_rate': 0.02
        }
    }
    
    if plan_type not in rates:
        return 0.0
    
    rate = rates[plan_type]
    input_cost = (input_tokens / 1000) * rate['input_rate']
    output_cost = (output_tokens / 1000) * rate['output_rate']
    
    return input_cost + output_cost

def get_customer_billing_info(customer_id: str) -> Dict:
    """Get customer's billing information and usage"""
    try:
        customer = stripe.Customer.retrieve(customer_id)
        subscription = get_customer_subscription(customer_id)
        
        info = {
            'customer_id': customer_id,
            'plan_type': customer.metadata.get('plan_type', 'unknown'),
            'email': customer.email,
            'has_subscription': subscription is not None
        }
        
        if subscription:
            info['subscription_id'] = subscription.id
            info['subscription_status'] = subscription.status
            info['current_period_start'] = subscription.current_period_start
            info['current_period_end'] = subscription.current_period_end
            
            # Get usage for current period
            for item in subscription.items.data:
                if item.price.recurring and item.price.recurring.usage_type == 'metered':
                    usage_records = stripe.SubscriptionItem.list_usage_record_summaries(
                        item.id,
                        limit=1
                    )
                    if usage_records.data:
                        usage = usage_records.data[0]
                        info['usage'] = {
                            'total_usage': usage.total_usage,
                            'period_start': usage.period.start,
                            'period_end': usage.period.end
                        }
        
        return info
        
    except Exception as e:
        print(f"Error getting billing info: {e}")
        return {'error': str(e)} 