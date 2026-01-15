# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based chat application with WhatsApp integration. It includes user authentication, conversation management, real-time messaging via WebSockets, and Evolution API WhatsApp integration.

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run the development server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Alternative: using python module
python -m uvicorn backend.main:app --reload
```

### Docker Development
```bash
# Quick deployment (creates .env from example if missing)
chmod +x deploy.sh
./deploy.sh

# Manual Docker commands
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop services
docker-compose down
```

### Database Operations
```bash
# The app uses SQLModel with SQLite by default
# Database file: chatapp.db
# No explicit migration commands - SQLModel handles table creation

# For PostgreSQL in production, update DATABASE_URL in .env:
# DATABASE_URL=postgresql://user:password@postgres:5432/chatapp
```

## Architecture

### Core Components
- **FastAPI Application** (`backend/main.py`): Main application with WebSocket support, authentication, and API endpoints
- **Enhanced Chatbot Service** (`backend/enhanced_chatbot_service.py`): Multi-tier chatbot with Claude AI, database context, and permanent fallbacks
- **Models** (`backend/models.py`): SQLModel definitions for User, Conversation, Message, AuditLog, BotInteraction, and BotContext
- **Static Frontend** (`static/`): HTML/CSS/JS client interface for chat management
- **Evolution API Integration**: WhatsApp messaging through Evolution API (free, QR Code based)
- **Docker Stack**: Web app, Redis, and optional Nginx reverse proxy

### Key Files
- `backend/main.py`: Main FastAPI application with all endpoints and WebSocket handling
- `backend/models.py`: Database models using SQLModel
- `backend/requirements.txt`: Python dependencies including FastAPI, SQLModel, httpx, etc.
- `docker-compose.yml`: Multi-service setup with web app, Redis, and Nginx
- `Dockerfile`: Python 3.9 container with system dependencies for compilation
- `static/`: Frontend HTML templates and assets
- `DEPLOYMENT.md`: Comprehensive deployment guide with cloud hosting options

### Database Schema
- **User**: Authentication and role management
- **Conversation**: Customer conversations with assignment and status tracking
- **Message**: Individual messages within conversations (now with message_type and bot_service fields)
- **BotContext**: Persistent conversation context and memory for chatbot interactions
- **BotInteraction**: Analytics and tracking for bot performance
- **AuditLog**: Activity tracking and logging

### Environment Configuration
Required environment variables (see `.env` example):
- `SECRET_KEY`: JWT token signing key
- `DATABASE_URL`: Database connection string (SQLite by default)
- `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE_NAME`: Evolution API WhatsApp integration
- `ANTHROPIC_API_KEY`: Claude API key for enhanced chatbot (optional, fallback available)
- `N8N_ENABLED`, `N8N_WEBHOOK_URL`, `N8N_API_KEY`: n8n workflow automation integration

### Ports and Services
- **8000**: FastAPI application
- **5678**: n8n workflow automation interface
- **6379**: Redis (for session/cache storage)
- **80/443**: Nginx reverse proxy (optional)

## Testing

### n8n Integration Testing
```bash
# Test n8n integration
python test_n8n_integration.py

# Test via API endpoint (requires authentication)
curl -X POST http://localhost:8000/test-n8n
```

No explicit test framework is configured. The codebase includes basic utility scripts in the backend directory but no formal test suite.

## Deployment

The application is containerized and ready for production deployment. See `DEPLOYMENT.md` for detailed instructions covering:
- Local Docker deployment
- Cloud hosting options (Railway, DigitalOcean, AWS, etc.)
- SSL configuration
- Database migration to PostgreSQL
- Monitoring and troubleshooting