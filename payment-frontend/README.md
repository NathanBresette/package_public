# RgentAI Payment Frontend

A modern, responsive payment website for RgentAI - the RStudio AI Assistant. Built with vanilla JavaScript and designed for seamless Stripe integration.

## 🚀 Features

- **Modern Design**: Beautiful, responsive UI with gradient backgrounds and smooth animations
- **Stripe Integration**: Seamless payment processing with Stripe Checkout
- **User Dashboard**: Post-purchase dashboard with access codes and usage tracking
- **Mobile Responsive**: Optimized for all device sizes
- **Security**: Built-in security headers and best practices

## 📁 Project Structure

```
payment-frontend/
├── index.html          # Main pricing page
├── dashboard.html      # User dashboard after purchase
├── app.js             # Main JavaScript for pricing page
├── dashboard.js       # Dashboard functionality
├── package.json       # Dependencies and scripts
├── vercel.json        # Vercel deployment configuration
└── README.md          # This file
```

## 🛠️ Setup Instructions

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Stripe account
- Vercel account (for deployment)

### Local Development

1. **Clone and navigate to the project:**
   ```bash
   cd payment-frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure Stripe:**
   - Replace `pk_test_your_publishable_key_here` in `app.js` with your actual Stripe publishable key
   - Set up your Stripe webhook endpoints

4. **Start development server:**
   ```bash
   npm run dev
   ```

5. **Open in browser:**
   - Navigate to `http://localhost:3000`

### Environment Variables

Create a `.env` file in the root directory:

```env
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
STRIPE_SECRET_KEY=sk_test_your_key_here
```

## 🚀 Deployment

### Deploy to Vercel

1. **Install Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Deploy:**
   ```bash
   vercel --prod
   ```

3. **Set environment variables in Vercel dashboard:**
   - Go to your project settings
   - Add `STRIPE_PUBLISHABLE_KEY` environment variable

### Deploy to Other Platforms

The frontend is static and can be deployed to any hosting platform:

- **Netlify**: Drag and drop the folder
- **GitHub Pages**: Push to a repository and enable Pages
- **AWS S3**: Upload files to an S3 bucket
- **Cloudflare Pages**: Connect your repository

## 🔧 Configuration

### Stripe Setup

1. **Create Stripe Account:**
   - Sign up at [stripe.com](https://stripe.com)
   - Get your API keys from the dashboard

2. **Configure Webhooks:**
   - Add webhook endpoint: `https://your-domain.com/api/webhook`
   - Events to listen for:
     - `checkout.session.completed`
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`

3. **Update API Keys:**
   - Replace the placeholder in `app.js`
   - Set environment variables in production

### Customization

#### Pricing Plans

Edit the `plans` object in `app.js`:

```javascript
const plans = {
    starter: {
        name: 'Starter',
        price: 900, // $9.00 in cents
        requests: 100,
        features: ['Feature 1', 'Feature 2']
    },
    // Add more plans...
};
```

#### Styling

The design uses CSS custom properties for easy theming. Main colors:

```css
--primary-color: #667eea;
--secondary-color: #764ba2;
--success-color: #27ae60;
--error-color: #e74c3c;
```

#### Domain Configuration

1. **Point your domain to Vercel:**
   - Add domain in Vercel dashboard
   - Update DNS records as instructed

2. **SSL Certificate:**
   - Automatically handled by Vercel

## 🔌 API Integration

### Backend Requirements

Your backend needs these endpoints:

1. **Create Checkout Session:**
   ```
   POST /api/create-checkout-session
   Body: { planType, planName, price, requests }
   Response: { id: "cs_..." }
   ```

2. **Webhook Handler:**
   ```
   POST /api/webhook
   Body: Stripe webhook payload
   ```

3. **User Data:**
   ```
   GET /api/user/{sessionId}
   Response: { accessCode, plan, usage, user }
   ```

### Example Backend Integration

```python
# FastAPI example
@app.post("/api/create-checkout-session")
async def create_checkout_session(request: CheckoutRequest):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': request.planName,
                },
                'unit_amount': request.price,
            },
            'quantity': 1,
        }],
        mode='subscription',
        success_url='https://your-domain.com/dashboard?session_id={CHECKOUT_SESSION_ID}',
        cancel_url='https://your-domain.com?cancelled=true',
    )
    return {"id": session.id}
```

## 📊 Analytics

The frontend includes basic analytics tracking. To add your own:

1. **Google Analytics:**
   ```javascript
   // Add to both HTML files
   <script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
   ```

2. **Custom Events:**
   ```javascript
   function trackEvent(eventName, properties = {}) {
       // Your analytics code here
       gtag('event', eventName, properties);
   }
   ```

## 🔒 Security

### Built-in Security Features

- **CSP Headers**: Content Security Policy
- **XSS Protection**: X-XSS-Protection header
- **Frame Options**: X-Frame-Options: DENY
- **Content Type**: X-Content-Type-Options: nosniff

### Additional Recommendations

1. **HTTPS Only**: All production deployments should use HTTPS
2. **Input Validation**: Validate all user inputs
3. **Rate Limiting**: Implement rate limiting on your backend
4. **CORS**: Configure CORS properly for your domain

## 🐛 Troubleshooting

### Common Issues

1. **Stripe not loading:**
   - Check your publishable key
   - Ensure HTTPS in production

2. **Payment not processing:**
   - Verify webhook configuration
   - Check Stripe dashboard for errors

3. **Dashboard not loading:**
   - Check session storage
   - Verify API endpoints

### Debug Mode

Enable debug logging:

```javascript
// Add to app.js
const DEBUG = true;

function log(...args) {
    if (DEBUG) console.log(...args);
}
```

## 📈 Performance

### Optimization Tips

1. **Minify Assets**: Use build tools to minify CSS/JS
2. **Image Optimization**: Compress images
3. **CDN**: Use a CDN for static assets
4. **Caching**: Set appropriate cache headers

### Performance Monitoring

- **Lighthouse**: Run Lighthouse audits
- **Web Vitals**: Monitor Core Web Vitals
- **Real User Monitoring**: Track actual user performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

- **Documentation**: [docs.rgentai.com](https://docs.rgentai.com)
- **Email**: support@rgentai.com
- **GitHub Issues**: [github.com/your-username/rstudioai/issues](https://github.com/your-username/rstudioai/issues)

---

**Built with ❤️ for the R community** 