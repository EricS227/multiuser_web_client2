#!/usr/bin/env python3
"""
Test script for n8n integration
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from backend.n8n_service import n8n_service

async def test_n8n_integration():
    """Test n8n integration functionality"""
    print("=== n8n Integration Test ===")
    
    # Test if n8n is enabled
    print(f"n8n Enabled: {await n8n_service.is_enabled()}")
    print(f"n8n URL: {n8n_service.n8n_url}")
    
    if not await n8n_service.is_enabled():
        print("X n8n is disabled. Set N8N_ENABLED=true in .env to test.")
        return
    
    # Test health check
    print("\n--- Health Check ---")
    health = await n8n_service.health_check()
    print(f"Health Status: {health}")
    
    # Test sending to workflow
    print("\n--- Test Workflow Trigger ---")
    test_data = {
        "message": "Test message from Python",
        "phone_number": "+5541999999999",
        "customer_name": "Test Customer",
        "test": True
    }
    
    result = await n8n_service.trigger_chat_workflow(
        message=test_data["message"],
        phone_number=test_data["phone_number"],
        customer_name=test_data["customer_name"]
    )
    
    print(f"Workflow Result: {result}")
    
    # Test webhook processing
    print("\n--- Test Webhook Processing ---")
    webhook_data = {
        "message": "Response from n8n",
        "response": "This is a test response",
        "workflow_id": "test_workflow",
        "execution_id": "test_123",
        "phone_number": "+5541999999999",
        "action": "message"
    }
    
    processed = await n8n_service.process_webhook_response(webhook_data)
    print(f"Processed Response: {processed}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_n8n_integration())