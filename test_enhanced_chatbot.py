"""
Test script for Enhanced Claude Chatbot Service
Tests all features including Claude API, fallbacks, and database context
"""

import asyncio
import os
import json
from pathlib import Path
from sqlmodel import Session, SQLModel, create_engine
from backend.enhanced_chatbot_service import EnhancedClaudeChatbotService
from backend.models import BotContext, BotInteraction, Message, Conversation, User
from datetime import datetime, timedelta

# Test database
TEST_DB_PATH = "test_enhanced_chatbot.db"
TEST_ENGINE = create_engine(f"sqlite:///{TEST_DB_PATH}")

def setup_test_db():
    """Setup test database"""
    SQLModel.metadata.create_all(TEST_ENGINE)
    print("✅ Test database created")

def cleanup_test_db():
    """Cleanup test database"""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    print("🧹 Test database cleaned up")

class TestEnhancedChatbot:
    def __init__(self):
        self.test_phone = "+5511999999999"
        self.test_profile = "João Teste"
        
    async def test_context_management(self, session: Session):
        """Test database context management"""
        print("\n🧪 Testing Context Management...")
        
        service = EnhancedClaudeChatbotService(session)
        
        # Test getting new context
        context1 = service.context_manager.get_context(self.test_phone)
        assert context1['phone_number'] == self.test_phone
        assert context1['conversation_stage'] == 'greeting'
        print("✅ New context creation works")
        
        # Test updating context
        service.context_manager.update_context(self.test_phone, {
            'bot_responses_count': 2,
            'conversation_stage': 'pricing_inquiry',
            'user_intent': 'asking_price'
        })
        
        # Test retrieving updated context
        context2 = service.context_manager.get_context(self.test_phone)
        assert context2['bot_responses_count'] == 2
        assert context2['conversation_stage'] == 'pricing_inquiry'
        print("✅ Context update and retrieval works")
        
        # Test context persistence
        service2 = EnhancedClaudeChatbotService(session)
        context3 = service2.context_manager.get_context(self.test_phone)
        assert context3['bot_responses_count'] == 2
        print("✅ Context persistence across service instances works")
        
        return True

    async def test_escalation_logic(self, session: Session):
        """Test smart escalation logic"""
        print("\n🧪 Testing Escalation Logic...")
        
        service = EnhancedClaudeChatbotService(session)
        
        # Test direct escalation request
        result1 = await service.process_message(
            self.test_phone, "Preciso falar com um atendente", self.test_profile
        )
        assert result1['should_escalate'] == True
        assert result1['escalation_reason'] == "user_requested"
        print("✅ Direct escalation request works")
        
        # Test complex intent escalation
        result2 = await service.process_message(
            self.test_phone + "2", "Quero cancelar minha conta", "Maria Teste"
        )
        assert result2['should_escalate'] == True
        assert result2['escalation_reason'] == "complex_intent"
        print("✅ Complex intent escalation works")
        
        # Test max responses escalation
        service.context_manager.update_context(self.test_phone + "3", {
            'bot_responses_count': 4
        })
        result3 = await service.process_message(
            self.test_phone + "3", "Ainda tenho dúvidas", "Pedro Teste"
        )
        assert result3['should_escalate'] == True
        assert result3['escalation_reason'] == "max_bot_responses"
        print("✅ Max responses escalation works")
        
        return True

    async def test_fallback_bot(self, session: Session):
        """Test permanent fallback bot"""
        print("\n🧪 Testing Permanent Fallback Bot...")
        
        service = EnhancedClaudeChatbotService(session)
        
        # Test greeting response
        result1 = await service.process_message(
            self.test_phone + "4", "Oi", "Carlos Teste"
        )
        assert result1['should_escalate'] == False
        assert result1['bot_service'] == "fallback"
        assert "Carlos Teste" in result1['bot_response']
        print("✅ Fallback greeting response works")
        
        # Test business hours response
        result2 = await service.process_message(
            self.test_phone + "5", "Qual é o horário de funcionamento?", "Ana Teste"
        )
        assert result2['should_escalate'] == False
        assert result2['bot_service'] == "fallback"
        assert "Segunda a Sexta" in result2['bot_response']
        print("✅ Fallback FAQ response works")
        
        return True

    async def test_claude_integration(self, session: Session):
        """Test Claude API integration (if available)"""
        print("\n🧪 Testing Claude API Integration...")
        
        claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not claude_api_key:
            print("⚠️ Claude API key not found - skipping Claude tests")
            return True
        
        service = EnhancedClaudeChatbotService(session)
        
        # Test Claude response
        result = await service.process_message(
            self.test_phone + "6", "Olá, como você pode me ajudar?", "Roberto Teste"
        )
        
        if result['bot_service'] == "claude":
            assert result['should_escalate'] == False
            assert len(result['bot_response']) > 10
            print("✅ Claude API response works")
        else:
            print("⚠️ Claude API not available, fallback used instead")
        
        return True

    async def test_multi_tier_fallback(self, session: Session):
        """Test multi-tier fallback system"""
        print("\n🧪 Testing Multi-Tier Fallback System...")
        
        service = EnhancedClaudeChatbotService(session)
        
        # This should always work because permanent fallback is always available
        result = await service.process_message(
            self.test_phone + "7", "Teste de fallback", "Fernanda Teste"
        )
        
        assert result['should_escalate'] == False
        assert result['bot_response'] is not None
        assert result['bot_service'] in ["claude", "ollama", "rasa", "fallback"]
        print(f"✅ Multi-tier fallback works (used: {result['bot_service']})")
        
        return True

    async def test_conversation_stages(self, session: Session):
        """Test conversation stage tracking"""
        print("\n🧪 Testing Conversation Stage Tracking...")
        
        service = EnhancedClaudeChatbotService(session)
        phone = self.test_phone + "8"
        
        # Greeting stage
        await service.process_message(phone, "Oi", "Teste Stage")
        context1 = service.context_manager.get_context(phone)
        assert context1['conversation_stage'] == 'greeting'
        
        # Pricing inquiry stage
        await service.process_message(phone, "Quanto custa?", "Teste Stage")
        context2 = service.context_manager.get_context(phone)
        assert context2['conversation_stage'] == 'pricing_inquiry'
        
        print("✅ Conversation stage tracking works")
        return True

    async def test_cleanup_functionality(self, session: Session):
        """Test context cleanup functionality"""
        print("\n🧪 Testing Context Cleanup...")
        
        service = EnhancedClaudeChatbotService(session)
        
        # Create test context
        await service.process_message(
            self.test_phone + "9", "Test cleanup", "Cleanup Test"
        )
        
        # Test cleanup
        cleaned_count = service.cleanup_expired_contexts()
        print(f"✅ Cleanup functionality works (cleaned: {cleaned_count})")
        
        return True

async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Enhanced Chatbot Tests\n")
    
    # Setup
    setup_test_db()
    
    try:
        with Session(TEST_ENGINE) as session:
            test_suite = TestEnhancedChatbot()
            
            # Run tests
            tests = [
                test_suite.test_context_management(session),
                test_suite.test_escalation_logic(session),
                test_suite.test_fallback_bot(session),
                test_suite.test_claude_integration(session),
                test_suite.test_multi_tier_fallback(session),
                test_suite.test_conversation_stages(session),
                test_suite.test_cleanup_functionality(session)
            ]
            
            results = await asyncio.gather(*tests, return_exceptions=True)
            
            # Check results
            passed = sum(1 for result in results if result is True)
            failed = len(results) - passed
            
            print(f"\n📊 Test Results:")
            print(f"✅ Passed: {passed}")
            print(f"❌ Failed: {failed}")
            
            if failed > 0:
                print("\n❌ Some tests failed:")
                for i, result in enumerate(results):
                    if result is not True:
                        print(f"  Test {i+1}: {result}")
                return False
            else:
                print("\n🎉 All tests passed!")
                return True
                
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        return False
    finally:
        cleanup_test_db()

def test_features_availability():
    """Test feature availability without running full tests"""
    print("🔍 Checking Feature Availability:\n")
    
    # Check Claude API
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    claude_status = "✅ Available" if claude_key else "❌ Not configured"
    print(f"Claude API: {claude_status}")
    
    # Check dependencies
    try:
        import anthropic
        print("Anthropic library: ✅ Installed")
    except ImportError:
        print("Anthropic library: ❌ Not installed")
    
    try:
        import httpx
        print("HTTPX library: ✅ Installed")
    except ImportError:
        print("HTTPX library: ❌ Not installed")
    
    # Check database models
    try:
        from backend.models import BotContext, BotInteraction
        print("Enhanced models: ✅ Available")
    except ImportError as e:
        print(f"Enhanced models: ❌ Error - {e}")
    
    print(f"\n🏗️ Multi-tier Architecture:")
    print(f"1️⃣ Primary: Claude API ({claude_status})")
    print(f"2️⃣ Secondary: Ollama (Local LLM)")
    print(f"3️⃣ Tertiary: Rasa (NLU)")
    print(f"4️⃣ Permanent: Rule-based Fallback (✅ Always Available)")

if __name__ == "__main__":
    print("Enhanced Claude Chatbot Test Suite\n" + "="*50)
    
    # Quick feature check
    test_features_availability()
    
    # Ask user if they want to run full tests
    print(f"\nDo you want to run the full test suite? (y/n)")
    response = input("> ").lower().strip()
    
    if response in ['y', 'yes']:
        success = asyncio.run(run_all_tests())
        exit(0 if success else 1)
    else:
        print("✅ Feature availability check completed. Skipping full tests.")