"""
Agent Orchestrator
Manages escalations, state coordination, and system-wide decision making
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EscalationReason(Enum):
    GENERATION_FAILURE = "generation_failure"
    COMPLEX_QUERY = "complex_query"
    CUSTOMER_REQUEST = "customer_request"
    MULTIPLE_FAILURES = "multiple_failures"
    TIMEOUT = "timeout"


class SystemState(Enum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    HANDOVER_PENDING = "handover_pending"
    HANDOVER_ACTIVE = "handover_active"
    ENDING = "ending"


@dataclass
class SessionState:
    session_id: str
    system_state: SystemState
    failure_count: int = 0
    escalation_history: list = field(default_factory=list)
    handover_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)


@dataclass
class EscalationEvent:
    session_id: str
    message_id: str
    reason: EscalationReason
    user_query: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentOrchestrator:
    """
    Orchestrates system-wide decisions, manages escalations, 
    and coordinates state transitions
    """
    
    def __init__(self):
        self.session_states: Dict[str, SessionState] = {}
        self.max_failures_before_handover = 3
        self.escalation_timeout = 30.0  # seconds
        
    def register_session(self, session_id: str) -> SessionState:
        """Register a new session"""
        state = SessionState(
            session_id=session_id,
            system_state=SystemState.NORMAL
        )
        self.session_states[session_id] = state
        logger.info(f"Registered session {session_id}")
        return state
    
    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """Get current state of a session"""
        return self.session_states.get(session_id)
    
    async def handle_escalation(self, event: EscalationEvent, 
                               output_queue: asyncio.Queue) -> Dict[str, Any]:
        """
        Handle escalation event and determine appropriate action
        Returns decision dictionary with action to take
        """
        logger.info(f"Handling escalation for session {event.session_id}: {event.reason.value}")
        
        # Get or create session state
        session_state = self.session_states.get(event.session_id)
        if not session_state:
            session_state = self.register_session(event.session_id)
        
        # Update session
        session_state.failure_count += 1
        session_state.escalation_history.append(event)
        session_state.last_activity = datetime.now()
        
        # Determine action based on escalation reason and history
        decision = await self._make_escalation_decision(event, session_state, output_queue)
        
        return decision
    
    async def _make_escalation_decision(self, event: EscalationEvent, 
                                       session_state: SessionState,
                                       output_queue: asyncio.Queue) -> Dict[str, Any]:
        """Make decision on how to handle escalation"""
        
        # Check if handover threshold reached
        if session_state.failure_count >= self.max_failures_before_handover:
            return await self._initiate_handover(
                event, 
                session_state, 
                output_queue,
                reason="Multiple generation failures"
            )
        
        # Handle specific escalation reasons
        if event.reason == EscalationReason.CUSTOMER_REQUEST:
            return await self._initiate_handover(
                event,
                session_state,
                output_queue,
                reason="Customer requested human agent"
            )
        
        if event.reason == EscalationReason.COMPLEX_QUERY:
            # Try enhanced filler strategy first
            return await self._try_enhanced_filler_strategy(event, session_state, output_queue)
        
        if event.reason == EscalationReason.GENERATION_FAILURE:
            # Generate contextual filler and retry
            return await self._retry_with_filler(event, session_state, output_queue)
        
        if event.reason == EscalationReason.TIMEOUT:
            return await self._handle_timeout(event, session_state, output_queue)
        
        # Default: generate filler
        return {
            "action": "generate_filler",
            "message_id": event.message_id,
            "session_id": event.session_id
        }
    
    async def _initiate_handover(self, event: EscalationEvent, 
                                session_state: SessionState,
                                output_queue: asyncio.Queue,
                                reason: str) -> Dict[str, Any]:
        """Initiate handover to human agent"""
        logger.info(f"Initiating handover for session {event.session_id}: {reason}")
        
        session_state.system_state = SystemState.HANDOVER_PENDING
        session_state.handover_reason = reason
        
        # Generate handover message
        handover_message = self._generate_handover_message(reason)
        
        # Send to output queue
        await output_queue.put({
            "type": "handover",
            "session_id": event.session_id,
            "message": handover_message,
            "reason": reason,
            "metadata": {
                "failure_count": session_state.failure_count,
                "original_query": event.user_query
            }
        })
        
        session_state.system_state = SystemState.HANDOVER_ACTIVE
        
        return {
            "action": "handover",
            "session_id": event.session_id,
            "reason": reason
        }
    
    def _generate_handover_message(self, reason: str) -> str:
        """Generate appropriate handover message based on reason"""
        
        messages = {
            "Multiple generation failures": 
                "I want to make sure you get the best assistance. Let me connect you with one of our specialists who can help you better.",
            
            "Customer requested human agent":
                "Of course! I'll connect you with one of our team members right away.",
            
            "Complex technical query":
                "That's a detailed technical question. Let me connect you with our technical specialist who can provide you with comprehensive information.",
            
            "Timeout":
                "I apologize for the delay. Let me transfer you to someone who can assist you immediately."
        }
        
        return messages.get(reason, "Let me connect you with a human agent who can better assist you.")
    
    async def _try_enhanced_filler_strategy(self, event: EscalationEvent,
                                           session_state: SessionState,
                                           output_queue: asyncio.Queue) -> Dict[str, Any]:
        """Try enhanced filler strategy for complex queries"""
        
        from filler_generator import FillerGeneratorAgent
        filler_gen = FillerGeneratorAgent()
        
        # Generate multiple progressive fillers
        fillers = filler_gen.generate_multiple_fillers(event.user_query, count=2)
        
        # Send fillers
        for filler in fillers:
            await output_queue.put({
                "type": "filler",
                "message_id": event.message_id,
                "text": filler
            })
            await asyncio.sleep(2)
        
        session_state.system_state = SystemState.DEGRADED
        
        return {
            "action": "enhanced_filler",
            "message_id": event.message_id,
            "retry_allowed": True
        }
    
    async def _retry_with_filler(self, event: EscalationEvent,
                                session_state: SessionState,
                                output_queue: asyncio.Queue) -> Dict[str, Any]:
        """Generate filler and allow retry"""
        
        from filler_generator import FillerGeneratorAgent
        filler_gen = FillerGeneratorAgent()
        
        filler = filler_gen.generate_filler(event.user_query)
        
        await output_queue.put({
            "type": "filler",
            "message_id": event.message_id,
            "text": filler
        })
        
        return {
            "action": "retry_with_filler",
            "message_id": event.message_id,
            "session_id": event.session_id
        }
    
    async def _handle_timeout(self, event: EscalationEvent,
                             session_state: SessionState,
                             output_queue: asyncio.Queue) -> Dict[str, Any]:
        """Handle timeout scenario"""
        
        # If this is not the first timeout, escalate to handover
        if session_state.failure_count > 1:
            return await self._initiate_handover(
                event,
                session_state,
                output_queue,
                reason="Timeout"
            )
        
        # Otherwise, generate apology filler
        from filler_generator import FillerGeneratorAgent
        filler_gen = FillerGeneratorAgent()
        
        timeout_filler = filler_gen.generate_filler_for_error('timeout')
        
        await output_queue.put({
            "type": "filler",
            "message_id": event.message_id,
            "text": timeout_filler
        })
        
        return {
            "action": "timeout_recovery",
            "message_id": event.message_id
        }
    
    async def monitor_session_health(self, session_id: str):
        """Monitor session health and take proactive actions"""
        
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            session_state = self.session_states.get(session_id)
            if not session_state:
                break
            
            # Check for prolonged degraded state
            if session_state.system_state == SystemState.DEGRADED:
                time_in_degraded = (datetime.now() - session_state.last_activity).total_seconds()
                
                if time_in_degraded > 15:  # 15 seconds in degraded state
                    logger.warning(f"Session {session_id} in degraded state for {time_in_degraded}s")
                    # Could trigger automatic handover here
    
    def get_session_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a session"""
        
        session_state = self.session_states.get(session_id)
        if not session_state:
            return None
        
        duration = (datetime.now() - session_state.created_at).total_seconds()
        
        return {
            "session_id": session_id,
            "duration_seconds": duration,
            "failure_count": session_state.failure_count,
            "escalation_count": len(session_state.escalation_history),
            "current_state": session_state.system_state.value,
            "handover_reason": session_state.handover_reason
        }
    
    def cleanup_session(self, session_id: str):
        """Clean up session state"""
        if session_id in self.session_states:
            logger.info(f"Cleaning up session {session_id}")
            del self.session_states[session_id]


# Test Agent Orchestrator
async def test_orchestrator():
    orchestrator = AgentOrchestrator()
    output_queue = asyncio.Queue()
    
    # Register session
    session_id = "test_session_001"
    orchestrator.register_session(session_id)
    
    print("\n=== Testing Generation Failure Escalation ===")
    event1 = EscalationEvent(
        session_id=session_id,
        message_id="msg_001",
        reason=EscalationReason.GENERATION_FAILURE,
        user_query="What's the best SUV?"
    )
    
    decision1 = await orchestrator.handle_escalation(event1, output_queue)
    print(f"Decision: {decision1}")
    print(f"Session metrics: {orchestrator.get_session_metrics(session_id)}")
    
    print("\n=== Testing Multiple Failures (Should Trigger Handover) ===")
    for i in range(3):
        event = EscalationEvent(
            session_id=session_id,
            message_id=f"msg_{i+2}",
            reason=EscalationReason.GENERATION_FAILURE,
            user_query="Complex technical question"
        )
        decision = await orchestrator.handle_escalation(event, output_queue)
        print(f"Attempt {i+1} Decision: {decision['action']}")
    
    print(f"\nFinal session metrics: {orchestrator.get_session_metrics(session_id)}")
    
    print("\n=== Testing Customer Request Handover ===")
    session_id2 = "test_session_002"
    orchestrator.register_session(session_id2)
    
    event2 = EscalationEvent(
        session_id=session_id2,
        message_id="msg_100",
        reason=EscalationReason.CUSTOMER_REQUEST,
        user_query="I want to speak to a human"
    )
    
    decision2 = await orchestrator.handle_escalation(event2, output_queue)
    print(f"Decision: {decision2}")
    
    # Check output queue
    print(f"\n=== Output Queue Contents ===")
    while not output_queue.empty():
        item = await output_queue.get()
        print(f"Type: {item['type']}, Message: {item.get('message', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(test_orchestrator())