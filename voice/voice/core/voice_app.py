"""
Voice App Core - Main Orchestrator
Manages job intake, prompt generation, and coordinates all managers
"""

import asyncio
import uuid
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobType(Enum):
    PRE_SALES = "pre_sales"
    POST_SALES = "post_sales"
    DEALER_CAMPAIGN = "dealer_campaign"
    INBOUND = "inbound"


class CallStatus(Enum):
    INITIATED = "initiated"
    CONNECTED = "connected"
    IN_PROGRESS = "in_progress"
    HANDOVER = "handover"
    ENDED = "ended"


@dataclass
class Job:
    job_id: str
    job_type: JobType
    customer_data: Dict[str, Any]
    campaign_data: Optional[Dict[str, Any]] = None


@dataclass
class CallSession:
    session_id: str
    job: Job
    call_status: CallStatus
    voice_provider_call_id: str
    created_at: float


class VoiceAppCore:
    """Main orchestrator for the Voice App system"""
    
    def __init__(self, voice_provider_config: Dict, messaging_server_config: Dict):
        self.voice_provider_config = voice_provider_config
        self.messaging_server_config = messaging_server_config
        self.active_sessions: Dict[str, CallSession] = {}
        
    def generate_session_id(self) -> str:
        """Generate unique session ID for call tracking"""
        return f"session_{uuid.uuid4().hex}"
    
    def generate_prompt(self, job: Job) -> str:
        """Generate dynamic prompt based on job type and data"""
        
        base_prompt = """You are a professional voice assistant for an automotive company.
Be conversational, helpful, and natural in your responses."""
        
        prompts = {
            JobType.PRE_SALES: f"""
{base_prompt}

Context: Pre-sales inquiry
Customer: {job.customer_data.get('name', 'Customer')}
Interest: {job.customer_data.get('vehicle_interest', 'General inquiry')}

Your goal:
- Understand customer requirements
- Provide vehicle information
- Schedule test drive if interested
- Offer to connect with sales representative if needed

Guidelines:
- Be enthusiastic but not pushy
- Ask clarifying questions
- Provide accurate information
- Handle objections professionally
""",
            
            JobType.POST_SALES: f"""
{base_prompt}

Context: Post-sales support
Customer: {job.customer_data.get('name', 'Customer')}
Vehicle: {job.customer_data.get('vehicle', 'N/A')}
Purchase Date: {job.customer_data.get('purchase_date', 'N/A')}

Your goal:
- Check customer satisfaction
- Address concerns or issues
- Schedule service if needed
- Collect feedback

Guidelines:
- Be empathetic and solution-oriented
- Take detailed notes of issues
- Escalate to human agent if complex technical issues
""",
            
            JobType.DEALER_CAMPAIGN: f"""
{base_prompt}

Context: Dealer campaign outreach
Campaign: {job.campaign_data.get('campaign_name', 'General')}
Customer: {job.customer_data.get('name', 'Customer')}
Offer: {job.campaign_data.get('offer_details', 'Special promotion')}

Your goal:
- Introduce the campaign
- Gauge customer interest
- Schedule dealership visit
- Capture intent data

Guidelines:
- Be brief and value-focused
- Respect customer's time
- Offer clear next steps
""",
            
            JobType.INBOUND: f"""
{base_prompt}

Context: Inbound customer call
Customer: {job.customer_data.get('name', 'Caller')}

Your goal:
- Understand reason for calling
- Route to appropriate department if needed
- Resolve simple queries
- Provide excellent service

Guidelines:
- Be welcoming and attentive
- Ask clarifying questions
- Provide accurate information
- Transfer to human agent when necessary
"""
        }
        
        return prompts.get(job.job_type, base_prompt)
    
    async def create_call_with_provider(self, session_id: str, phone_number: str) -> str:
        """
        Create call with voice provider
        Returns voice_provider_call_id
        """
        logger.info(f"Creating call for session {session_id} to {phone_number}")
        
        # Simulate API call to voice provider
        # In production: integrate with actual voice provider API (Twilio, Vonage, etc.)
        call_id = f"call_{uuid.uuid4().hex}"
        
        # Mock API call
        await asyncio.sleep(0.5)
        
        logger.info(f"Call created: {call_id}")
        return call_id
    
    async def connect_to_messaging_server(self, session_id: str, call_id: str):
        """
        Connect voice provider to messaging server using session_id
        This establishes the audio bridge
        """
        logger.info(f"Connecting session {session_id} to messaging server")
        
        # In production: WebSocket or WebRTC connection to messaging server
        # Send session_id and call_id to establish bidirectional audio stream
        
        await asyncio.sleep(0.5)
        logger.info(f"Connected to messaging server")
    
    async def process_job(self, job: Job, phone_number: str):
        """
        Main job processing pipeline
        """
        try:
            # 1. Generate session ID
            session_id = self.generate_session_id()
            logger.info(f"Processing job {job.job_id} with session {session_id}")
            
            # 2. Generate prompt for Voice Agent
            prompt = self.generate_prompt(job)
            logger.info(f"Generated prompt for {job.job_type.value}")
            
            # 3. Create call with voice provider
            call_id = await self.create_call_with_provider(session_id, phone_number)
            
            # 4. Create call session
            session = CallSession(
                session_id=session_id,
                job=job,
                call_status=CallStatus.INITIATED,
                voice_provider_call_id=call_id,
                created_at=asyncio.get_event_loop().time()
            )
            self.active_sessions[session_id] = session
            
            # 5. Connect to messaging server
            await self.connect_to_messaging_server(session_id, call_id)
            
            session.call_status = CallStatus.CONNECTED
            
            # 6. Initialize shared queues
            input_queue = asyncio.Queue()
            output_queue = asyncio.Queue()
            
            # 7. Start Input Manager, Output Manager, and Voice Agent in parallel
            from input_manager import InputManager
            from output_manager import OutputManager
            from voice_agent import VoiceAgent
            
            input_mgr = InputManager(session_id, input_queue, output_queue)
            output_mgr = OutputManager(session_id, output_queue)
            voice_agent = VoiceAgent(session_id, input_queue, output_queue, prompt)
            
            session.call_status = CallStatus.IN_PROGRESS
            
            # Run all managers concurrently
            await asyncio.gather(
                input_mgr.run(),
                output_mgr.run(),
                voice_agent.run(),
                return_exceptions=True
            )
            
            logger.info(f"Session {session_id} completed")
            session.call_status = CallStatus.ENDED
            
        except Exception as e:
            logger.error(f"Error processing job {job.job_id}: {e}")
            raise
        finally:
            # Cleanup
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]


# Example usage
async def main():
    # Configuration
    voice_config = {
        "provider": "twilio",
        "api_key": "your_api_key"
    }
    
    messaging_config = {
        "server_url": "ws://messaging-server:8080"
    }
    
    # Initialize Voice App
    app = VoiceAppCore(voice_config, messaging_config)
    
    # Create sample job
    job = Job(
        job_id="job_001",
        job_type=JobType.PRE_SALES,
        customer_data={
            "name": "John Doe",
            "phone": "+1234567890",
            "vehicle_interest": "SUV"
        }
    )
    
    # Process job
    await app.process_job(job, "+1234567890")


if __name__ == "__main__":
    asyncio.run(main())