"""
Complete System Integration Example
Demonstrates how all modules work together in a real call scenario
"""

import asyncio
import logging
from datetime import datetime

# Import all modules
from core import VoiceAppCore, Job, JobType
from input_manager import InputManager
from output_manager import OutputManager
from agent import VoiceAgent
from orchestrator import AgentOrchestrator, EscalationEvent, EscalationReason

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegratedVoiceSystem:
    """
    Complete integrated voice system with all components
    """
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()        
        # Voice provider configuration
        self.voice_config = {
            "provider": "twilio",
            "api_key": "your_api_key",
            "webhook_url": "https://your-server.com/webhook"
        }
        
        # Messaging server configuration
        self.messaging_config = {
            "server_url": "ws://messaging-server:8080",
            "auth_token": "your_auth_token"
        }
    
    async def enhanced_voice_agent_with_orchestrator(self, session_id: str, 
                                                     input_queue: asyncio.Queue,
                                                     output_queue: asyncio.Queue,
                                                     system_prompt: str):
        """
        Enhanced Voice Agent that integrates with Agent Orchestrator
        """
        voice_agent = VoiceAgent(session_id, input_queue, output_queue, system_prompt)
        
        async def process_with_orchestrator():
            """Process messages with orchestrator support"""
            while voice_agent.running:
                try:
                    user_message = await asyncio.wait_for(
                        input_queue.get(),
                        timeout=1.0
                    )
                    
                    # Try to generate response
                    result = await voice_agent.call_llm_api(
                        user_message.transcript,
                        user_message.is_interruption
                    )
                    
                    if result.success:
                        # Stream response normally
                        await voice_agent.stream_response(
                            user_message.message_id,
                            result.response_text
                        )
                    else:
                        # Escalate to orchestrator
                        logger.warning(f"Generation failed, escalating to orchestrator")
                        
                        escalation_event = EscalationEvent(
                            session_id=session_id,
                            message_id=user_message.message_id,
                            reason=EscalationReason.GENERATION_FAILURE,
                            user_query=user_message.transcript
                        )
                        
                        decision = await self.orchestrator.handle_escalation(
                            escalation_event,
                            output_queue
                        )
                        
                        # Handle orchestrator decision
                        if decision['action'] == 'handover':
                            logger.info("Orchestrator initiated handover")
                            voice_agent.running = False
                            break
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error in voice agent: {e}")
        
        await process_with_orchestrator()
    
    async def run_complete_call(self, job: Job, phone_number: str):
        """
        Run a complete call with all integrated components
        """
        try:
            # Initialize Voice App Core
            app = VoiceAppCore(self.voice_config, self.messaging_config)
            
            # Generate session ID
            session_id = app.generate_session_id()
            logger.info(f"\n{'='*60}")
            logger.info(f"STARTING CALL SESSION: {session_id}")
            logger.info(f"Job Type: {job.job_type.value}")
            logger.info(f"Customer: {job.customer_data.get('name')}")
            logger.info(f"{'='*60}\n")
            
            # Register session with orchestrator
            self.orchestrator.register_session(session_id)
            
            # Generate prompt
            prompt = app.generate_prompt(job)
            
            # Create call with provider
            call_id = await app.create_call_with_provider(session_id, phone_number)
            
            # Connect to messaging server
            await app.connect_to_messaging_server(session_id, call_id)
            
            # Initialize shared queues
            input_queue = asyncio.Queue()
            output_queue = asyncio.Queue()
            
            # Create managers
            input_mgr = InputManager(session_id, input_queue, output_queue)
            output_mgr = OutputManager(session_id, output_queue)
            
            # Start all components
            logger.info("Starting all system components...\n")
            
            await asyncio.gather(
                input_mgr.run(),
                output_mgr.run(),
                self.enhanced_voice_agent_with_orchestrator(
                    session_id,
                    input_queue,
                    output_queue,
                    prompt
                ),
                return_exceptions=True
            )
            
            # Get final metrics
            metrics = self.orchestrator.get_session_metrics(session_id)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"CALL SESSION COMPLETED: {session_id}")
            logger.info(f"Duration: {metrics['duration_seconds']:.1f}s")
            logger.info(f"Failure Count: {metrics['failure_count']}")
            logger.info(f"Final State: {metrics['current_state']}")
            if metrics['handover_reason']:
                logger.info(f"Handover Reason: {metrics['handover_reason']}")
            logger.info(f"{'='*60}\n")
            
            # Cleanup
            self.orchestrator.cleanup_session(session_id)
            
        except Exception as e:
            logger.error(f"Error in call execution: {e}")
            raise


async def demo_pre_sales_call():
    """Demo: Pre-sales inquiry call"""
    
    system = IntegratedVoiceSystem()
    
    job = Job(
        job_id="job_pre_001",
        job_type=JobType.PRE_SALES,
        customer_data={
            "name": "Sarah Johnson",
            "phone": "+1234567890",
            "vehicle_interest": "Family SUV",
            "budget": "$35,000-$45,000"
        }
    )
    
    await system.run_complete_call(job, "+1234567890")


async def demo_post_sales_call():
    """Demo: Post-sales support call"""
    
    system = IntegratedVoiceSystem()
    
    job = Job(
        job_id="job_post_001",
        job_type=JobType.POST_SALES,
        customer_data={
            "name": "Michael Chen",
            "phone": "+1987654321",
            "vehicle": "2024 Explorer XLT",
            "purchase_date": "2024-09-15",
            "concern": "Service reminder"
        }
    )
    
    await system.run_complete_call(job, "+1987654321")


async def demo_dealer_campaign_call():
    """Demo: Dealer campaign outreach call"""
    
    system = IntegratedVoiceSystem()
    
    job = Job(
        job_id="job_campaign_001",
        job_type=JobType.DEALER_CAMPAIGN,
        customer_data={
            "name": "Emily Rodriguez",
            "phone": "+1555123456",
            "last_contact": "2024-06-01"
        },
        campaign_data={
            "campaign_name": "Summer Sales Event 2024",
            "offer_details": "0% APR for 60 months + $2000 trade-in bonus",
            "valid_until": "2024-08-31"
        }
    )
    
    await system.run_complete_call(job, "+1555123456")


async def demo_inbound_call():
    """Demo: Inbound customer call"""
    
    system = IntegratedVoiceSystem()
    
    job = Job(
        job_id="job_inbound_001",
        job_type=JobType.INBOUND,
        customer_data={
            "name": "Unknown Caller",
            "phone": "+1444555666"
        }
    )
    
    await system.run_complete_call(job, "+1444555666")


async def main():
    """
    Run demonstrations of different call types
    """
    
    print("\n" + "="*80)
    print("VOICE APP SYSTEM - COMPLETE INTEGRATION DEMONSTRATION")
    print("="*80 + "\n")
    
    demos = [
        ("Pre-Sales Call", demo_pre_sales_call),
        ("Post-Sales Call", demo_post_sales_call),
        ("Dealer Campaign Call", demo_dealer_campaign_call),
        ("Inbound Call", demo_inbound_call),
    ]
    
    for demo_name, demo_func in demos:
        print(f"\n{'*'*80}")
        print(f"DEMO: {demo_name}")
        print(f"{'*'*80}\n")
        
        try:
            await demo_func()
        except Exception as e:
            logger.error(f"Demo failed: {e}")
        
        print("\nWaiting before next demo...\n")
        await asyncio.sleep(2)
    
    print("\n" + "="*80)
    print("ALL DEMONSTRATIONS COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())