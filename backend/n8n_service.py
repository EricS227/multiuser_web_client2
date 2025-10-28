"""
n8n Integration Service
Handles communication with n8n workflows
"""

import httpx
import os
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class N8nService:
    def __init__(self):
        self.n8n_url = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678")
        self.api_key = os.getenv("N8N_API_KEY")
        self.enabled = os.getenv("N8N_ENABLED", "false").lower() == "true"
        
    async def is_enabled(self) -> bool:
        """Check if n8n integration is enabled"""
        return self.enabled
    
    async def send_to_workflow(
        self, 
        workflow_id: str, 
        data: Dict[Any, Any],
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send data to n8n workflow webhook
        
        Args:
            workflow_id: The n8n workflow ID
            data: Data to send to the workflow
            execution_id: Optional execution ID for tracking
            
        Returns:
            Response from n8n workflow
        """
        if not self.enabled:
            return {"error": "n8n integration disabled"}
            
        try:
            webhook_url = f"{self.n8n_url}/webhook/{workflow_id}"
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            payload = {
                "timestamp": datetime.now().isoformat(),
                "execution_id": execution_id,
                **data
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Successfully sent to n8n workflow {workflow_id}")
                    return {
                        "success": True,
                        "workflow_id": workflow_id,
                        "execution_id": execution_id,
                        "response": result
                    }
                else:
                    logger.error(f"n8n workflow failed: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "workflow_id": workflow_id
                    }
                    
        except Exception as e:
            logger.error(f"Error sending to n8n workflow {workflow_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workflow_id": workflow_id
            }
    
    async def trigger_chat_workflow(
        self, 
        message: str, 
        phone_number: str, 
        customer_name: Optional[str] = None,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Trigger the main chat processing workflow
        
        Args:
            message: Customer message
            phone_number: Customer phone number
            customer_name: Customer name (optional)
            conversation_id: Conversation ID (optional)
            
        Returns:
            n8n workflow response
        """
        data = {
            "message": message,
            "phone_number": phone_number,
            "customer_name": customer_name,
            "conversation_id": conversation_id,
            "source": "chatapp"
        }
        
        # Use default chat workflow ID - can be configured via environment
        workflow_id = os.getenv("N8N_CHAT_WORKFLOW_ID", "chat")
        
        return await self.send_to_workflow(workflow_id, data)
    
    async def process_webhook_response(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming webhook data from n8n
        
        Args:
            webhook_data: Data received from n8n webhook
            
        Returns:
            Processed response data
        """
        try:
            # Extract common fields
            result = {
                "success": True,
                "message": webhook_data.get("message"),
                "response": webhook_data.get("response"),
                "workflow_id": webhook_data.get("workflow_id"),
                "execution_id": webhook_data.get("execution_id"),
                "phone_number": webhook_data.get("phone_number"),
                "conversation_id": webhook_data.get("conversation_id"),
                "action": webhook_data.get("action", "message"),
                "data": webhook_data
            }
            
            logger.info(f"Processed n8n webhook response: {result.get('workflow_id')}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing n8n webhook: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": webhook_data
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check n8n service health
        
        Returns:
            Health status
        """
        if not self.enabled:
            return {"status": "disabled", "enabled": False}
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.n8n_url}/healthz",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"status": "healthy", "enabled": True}
                else:
                    return {"status": "unhealthy", "enabled": True, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            return {"status": "unhealthy", "enabled": True, "error": str(e)}

# Global instance
n8n_service = N8nService()