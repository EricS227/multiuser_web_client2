# Production Deployment Guide

## Quick Deploy to Render.com (FREE)

### Prerequisites
- GitHub account
- Render.com account (free signup)
- Twilio account credentials

### Step 1: Push to GitHub

```bash
# Initialize and commit your code
git add .
git commit -m "Initial commit - WhatsApp ChatBot"

# Create new repo on GitHub: https://github.com/new
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Render

1. **Go to**: https://render.com/ and sign up
2. **Click**: "New +" → "Web Service"
3. **Connect**: Your GitHub repository
4. **Render will detect** the `render.yaml` file automatically
5. **Click**: "Apply" to use the configuration

### Step 3: Configure Environment Variables

In Render dashboard, add these environment variables:

```
TWILIO_ACCOUNT_SID=your_actual_sid_here
TWILIO_AUTH_TOKEN=your_actual_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
ANTHROPIC_API_KEY=your_claude_key_here (optional)
```

### Step 4: Get Your Production URL

After deployment completes:
- Your app URL will be: `https://your-app-name.onrender.com`
- Note this URL for Twilio webhook configuration

### Step 5: Configure Twilio Webhook

1. **Go to**: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
2. **Under "Sandbox Configuration"**:
   - When a message comes in: `https://your-app-name.onrender.com/webhook/whatsapp`
   - Method: `POST`
3. **Click**: Save

### Step 6: Test

1. Rejoin WhatsApp sandbox (send join code to sandbox number)
2. Send a message to test the integration
3. Check Render logs for any errors

---

## Alternative: Deploy to Fly.io (FREE)

### Quick Deploy

```bash
# Install Fly CLI
# Windows: iwr https://fly.io/install.ps1 -useb | iex

# Login and deploy
fly auth login
fly launch
fly deploy

# Set environment variables
fly secrets set TWILIO_ACCOUNT_SID=your_sid
fly secrets set TWILIO_AUTH_TOKEN=your_token
fly secrets set TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

Your app will be at: `https://your-app-name.fly.dev`

---

## Alternative: Deploy to Heroku

```bash
# Install Heroku CLI, then:
heroku login
heroku create your-app-name

# Set environment variables
heroku config:set SECRET_KEY=$(openssl rand -hex 32)
heroku config:set TWILIO_ACCOUNT_SID=your_sid
heroku config:set TWILIO_AUTH_TOKEN=your_token
heroku config:set TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Deploy
git push heroku main
```

---

## Database Migration for Production

For production, switch from SQLite to PostgreSQL:

**Render** provides PostgreSQL automatically (configured in render.yaml)

**Manual PostgreSQL setup**:
```bash
# Update .env
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

---

## Monitoring & Logs

**Render**: Dashboard → Logs tab
**Fly.io**: `fly logs`
**Heroku**: `heroku logs --tail`

---

## Security Checklist

- [ ] Use strong `SECRET_KEY` (auto-generated on Render)
- [ ] Never commit `.env` file (added to .gitignore)
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS (automatic on all platforms)
- [ ] Use PostgreSQL for production (not SQLite)
- [ ] Set up monitoring/alerts

---

## Troubleshooting

### Deployment fails
- Check build logs for missing dependencies
- Verify `backend/requirements.txt` is complete

### Webhook not working
- Verify URL in Twilio console
- Check logs for incoming requests
- Ensure endpoint is `/webhook/whatsapp` (with leading slash)

### Database errors
- For SQLite: Ensure volume/persistent storage is configured
- For PostgreSQL: Verify DATABASE_URL connection string

---

## Cost Estimate

**Free Options:**
- Render: Free tier (750 hrs/month, auto-sleep after inactivity)
- Fly.io: 3 free VMs, 3GB storage
- Heroku: Eco dynos ($5/month minimum)

**Recommended for Production:**
- Render: $7/month (always-on, no sleep)
- Fly.io: ~$5-10/month depending on usage
- DigitalOcean: $5/month App Platform

Choose based on your traffic and uptime requirements.
