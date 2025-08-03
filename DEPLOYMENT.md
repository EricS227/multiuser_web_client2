# Deployment Guide

This guide explains how to deploy your FastAPI Chat Application to various hosting platforms.

## 🏗️ Prerequisites

- Docker and Docker Compose installed
- Domain name (for production deployment)
- SSL certificate (for HTTPS)
- Twilio account (for WhatsApp integration)

## 🚀 Quick Start (Local Development)

1. **Clone and setup**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Deploy with Docker**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Access your application**:
   - Direct: http://localhost:8000
   - Via nginx: http://localhost

## ☁️ Cloud Hosting Options

### 1. **Railway** (Recommended for beginners)
- Easy deployment with GitHub integration
- Automatic HTTPS
- Built-in database options

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### 2. **DigitalOcean App Platform**
- Simple deployment
- Managed database options
- Automatic scaling

### 3. **AWS EC2**
- More control and customization
- Cost-effective for larger applications

### 4. **Google Cloud Run**
- Serverless container platform
- Pay-per-use pricing

### 5. **Heroku**
- Easy deployment with git
- Add-ons for databases and services

## 🔧 Production Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```env
SECRET_KEY=your-very-secure-secret-key
DATABASE_URL=sqlite:///./data/chatwoot_clone.db
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_WHATSAPP_FROM=whatsapp:+your-number
```

### SSL Configuration
For HTTPS, uncomment the SSL server block in `nginx.conf` and:
1. Obtain SSL certificates (Let's Encrypt recommended)
2. Place certificates in `ssl/` directory
3. Update `nginx.conf` with your domain name

### Database
For production, consider PostgreSQL instead of SQLite:

```yaml
# Add to docker-compose.yml
postgres:
  image: postgres:13
  environment:
    POSTGRES_DB: chatapp
    POSTGRES_USER: user
    POSTGRES_PASSWORD: password
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

Update `DATABASE_URL` in `.env`:
```env
DATABASE_URL=postgresql://user:password@postgres:5432/chatapp
```

## 📊 Monitoring

### Health Check Endpoint
The application includes a health check endpoint at `/health`.

### Logs
View application logs:
```bash
docker-compose logs -f web
```

### Database Backup
Backup SQLite database:
```bash
docker-compose exec web cp /app/data/chatwoot_clone.db /app/backup.db
```

## 🔒 Security Considerations

1. **Change default secret key**
2. **Use environment variables for sensitive data**
3. **Enable HTTPS in production**
4. **Regularly update dependencies**
5. **Set up proper firewall rules**
6. **Use strong database passwords**

## 🚨 Troubleshooting

### Common Issues

1. **Port already in use**:
   ```bash
   docker-compose down
   # Or change ports in docker-compose.yml
   ```

2. **Database permission errors**:
   ```bash
   sudo chown -R $USER:$USER data/
   ```

3. **Twilio webhook not receiving messages**:
   - Ensure your server is publicly accessible
   - Configure webhook URL in Twilio console
   - Use ngrok for local testing

### Logs and Debugging
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs web
docker-compose logs nginx
docker-compose logs redis

# Access container shell
docker-compose exec web bash
```

## 📞 Support

For issues or questions:
1. Check the logs first
2. Verify environment variables
3. Ensure all services are running
4. Check Twilio configuration

## 🔄 Updates

To update the application:
```bash
git pull origin main
docker-compose build
docker-compose up -d
```