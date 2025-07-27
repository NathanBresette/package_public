// Test script to simulate frontend request
const BACKEND_URL = 'https://rgent.onrender.com';

async function testAccountCreation() {
    try {
        console.log('Testing account creation...');
        
        const response = await fetch(`${BACKEND_URL}/api/create-account`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                email: 'test12@example.com', 
                password: 'test123', 
                plan_type: 'pro_haiku' 
            })
        });
        
        console.log('Response status:', response.status);
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.success) {
            console.log('✅ Account creation successful!');
            console.log('User object:', data.user);
            
            // Test the Stripe checkout creation that happens next
            console.log('\nTesting Stripe checkout creation...');
            
            const checkoutResponse = await fetch(`${BACKEND_URL}/api/create-stripe-checkout`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lookup_key: 'pro_haiku_monthly_base_v3',
                    customer_email: 'test12@example.com'
                })
            });
            
            console.log('Checkout response status:', checkoutResponse.status);
            const checkoutData = await checkoutResponse.json();
            console.log('Checkout response data:', checkoutData);
            
            if (checkoutData.id) {
                console.log('✅ Stripe checkout creation successful!');
            } else {
                console.log('❌ Stripe checkout creation failed');
            }
            
        } else {
            console.log('❌ Account creation failed:', data.detail);
        }
        
    } catch (error) {
        console.error('❌ Request failed:', error);
    }
}

// Run the test
testAccountCreation(); 