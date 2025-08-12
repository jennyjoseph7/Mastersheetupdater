import json
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from ai_service import ai_service
from urllib.parse import urlparse
import requests
import os
import io
import re
from typing import Union, Dict, Any
from datetime import datetime, timedelta
try:
    from .base_agent import BaseAgent
except:
    from base_agent import BaseAgent
from utils import GRYD_SERVICE, GRYD_CONFIG, get_logger
logger = get_logger(__name__)
SCORING_CATEGORIES = [
    'intent_score',
    'engagement_score', 
    'demographic_score',
    'campaign_response_score',
    'urgency_score'
]

PRIORITY_LEVELS = {
    'HOT': {'min_score': 80, 'color': '#FF4444', 'response_time': '30 minutes'},
    'WARM': {'min_score': 60, 'color': '#FF8800', 'response_time': '2 hours'},
    'COOL': {'min_score': 40, 'color': '#4488FF', 'response_time': '24 hours'},
    'COLD': {'min_score': 0, 'color': '#888888', 'response_time': '72 hours'}
}


class LeadPrioritizationAgent(BaseAgent):
    def __init__(self,source,model_identifier='azure-gpt-4o'):
        self.model_identifier = model_identifier
        self.data = self._load_json(source=source)
        self.scores = None
        self.total_score=None
        self.priority_level=None
        self.recommended_actions = []

    def _calculate_intent_score(self,data):
        """calculate intent score based on the user actions(0-40 points)""" 
        score = 0
        #High Intent indicators
        if data.get('book_test_drive',False):
            score +=15
        if data.get('variants_and_pricing',False):
            score +=10
        if data.get('finance_and_offer', False):
                score += 8
        if data.get('brochure_download', False):
            score += 5
        if data.get('configure', False) or data.get('build_your_own', False):
            score += 7
            
        # Walk-in specific indicators
            if data.get('source') == 'walk-in':
                if 'test drive' in data.get('details', '').lower():
                    score += 15
                if 'immediate delivery' in data.get('details', '').lower():
                    score += 12
            
        # Medium intent indicators
        if data.get('technology', False):
            score += 3
        if data.get('safety', False):
            score += 3
        if data.get('locate_dealer', False):
            score += 3
        if data.get('final_colour'):
            score += 2
            
        return min(score, 40)

    def _calculate_engagement_score(self, data):
        """Calculate engagement score (0-25 points)"""
        score = 0
        
        if data.get('source') == 'walk-in':
            score += 15
            if len(data.get('model', '').split(',')) > 1:
                score += 8
        else:
            # Website engagement
            sections_viewed = sum([
                data.get('exterior', False),
                data.get('interior', False),
                data.get('performance', False),
                data.get('technology', False),
                data.get('safety', False)
            ])
            
            if sections_viewed >= 3:
                score += 10
            elif sections_viewed >= 2:
                score += 6
            
            if data.get('exterior_views', 0) > 2:
                score += 3
            
            if len(data.get('technology_views', [])) > 2:
                score += 4
            
            if len(data.get('compared_cars', [])) > 1:
                score += 7
                
            if data.get('hd_view') == 'on':
                score += 3
                
        return min(score, 25)

    def _calculate_demographic_score(self, data):
        """Calculate demographic score (0-20 points)"""
        score = 0
        
        # Location-based scoring
        city = data.get('city', '').lower()
        metro_cities = ['bengaluru', 'bangalore', 'mumbai', 'delhi', 'chennai', 'hyderabad', 'pune']
        if city in metro_cities:
            score += 8
        elif city:
            score += 6
        
        # Device/Channel scoring
        if data.get('source') == 'walk-in':
            score += 12
        elif data.get('device') in ['laptop', 'desktop']:
            score += 6
        elif data.get('device') == 'mobile':
            score += 4
            
        return min(score, 20)

    def _calculate_campaign_response_score(self, data):
        """Calculate campaign response score (0-15 points)"""
        score = 0
        
        source = data.get('source', '')
        utm_source = data.get('utm_source', '')
        utm_medium = data.get('utm_medium', '')
        
        if source == 'walk-in':
            score += 15
        elif source == 'website':
            if utm_medium == 'ppc':
                score += 8
            elif utm_source == 'google':
                score += 7
            elif utm_source in ['facebook', 'instagram']:
                score += 6
            else:
                score += 10  # Direct website
                
        return min(score, 15)

    def _calculate_urgency_score(self, data):
            """Calculate urgency score based on time sensitivity (0-10 points)"""
            score = 0
            
            # Recent activity gets higher score
            if data.get('date'):
                try:
                    lead_date = datetime.strptime(data['date'], '%Y-%m-%d')
                    today = datetime.now()
                    days_old = (today - lead_date).days
                    
                    if days_old == 0:
                        score += 10
                    elif days_old <= 2:
                        score += 8
                    elif days_old <= 7:
                        score += 5
                    elif days_old <= 14:
                        score += 2
                except:
                    score += 5  # Default for invalid dates
            
            return score
    def _get_model_boost(self, data):
            """Additional points for premium models"""
            models = data.get('model', '').lower()
            premium_models = ['grand vitara', 'invicto']
            
            for premium in premium_models:
                if premium in models:
                    return 10
            return 0
        
    def _determine_priority_level(self, total_score):
        """Determine priority level based on total score"""
        for level, config in PRIORITY_LEVELS.items():
            if total_score >= config['min_score']:
                return level
        return 'COLD'
    
    def _generate_recommendations(self, data, priority_level, scores):
        """Generate recommended actions based on lead data and priority"""
        actions = []
        
        if priority_level == 'HOT':
            actions.extend([
                'immediate_phone_call',
                'dealer_assignment',
                'special_offers',
                'priority_scheduling',
                "personalized_email"
            ])
            
            if data.get('book_test_drive'):
                actions.append('confirm_test_drive')
            if data.get('finance_and_offer'):
                actions.append('finance_consultation')
                
        elif priority_level == 'WARM':
            actions.extend([
                'phone_call_within_2hrs',
                'personalized_email',
                'schedule_test_drive'
            ])
            
            if scores['intent_score'] > 20:
                actions.append('send_pricing_details')
                
        elif priority_level == 'COOL':
            actions.extend([
                'personalized_email',
                'feature_highlights',
                'nurture_campaign_enrollment'
            ])
            
        else:  # COLD
            actions.extend([
                'personalized_email',
                'retargeting_ads',
                'awareness_campaign'
            ])
            
        return actions

    def _extract_json_from_text(self,raw_llm_response):
        """
        Extracts the first complete JSON object from raw LLM response,
        even if it includes nested objects.
        """
        raw_text = raw_llm_response.strip()
        print(raw_text)
        start = None
        brace_stack = []

        for i, char in enumerate(raw_text):
            if char == '{':
                if not brace_stack:
                    start = i
                brace_stack.append('{')
            elif char == '}':
                if brace_stack:
                    brace_stack.pop()
                    if not brace_stack and start is not None:
                        json_candidate = raw_text[start:i + 1]
                        try:
                            return json.loads(json_candidate)
                        except json.JSONDecodeError as e:
                            print(f"Invalid JSON segment: {e}")
                            continue

        raise ValueError("No valid JSON object found in LLM response.")

    def _build_messages(self):
        messages = []
        prompt = f"""
        You are a lead scoring assistant for an automobile company.

        A potential customer has interacted with our system. Here's the raw data:
        {json.dumps(self.data, indent=2)}

        Analyze this lead data and provide insights on:
        1. Customer intent level
        2. Engagement quality  
        3. Urgency indicators
        4. Budget signals
        5. Preferred communication approach

        Respond only  with a JSON object containing your analysis:
        {{
            "customer_insights": {{
                "intent_level": "high/medium/low",
                "budget_category": "premium/mid-range/budget",
                "urgency": "immediate/moderate/low",
                "preferred_models": ["model1", "model2"],
                "key_interests": ["feature1", "feature2"],
                "communication_preference": "phone/email/whatsapp"
            }},
            "risk_factors": ["factor1", "factor2"],
            "conversion_likelihood": 0.0-1.0,
            "talking_points":[""point1","point2"]
        }}
        """
        user_message = {"role": "user", "content": prompt}
        messages.append(user_message)
        return messages

    def get_ai_insights(self):
        """Get AI-powered insights about the lead"""
        messages = self._build_messages()
        response = ai_service.get_llm_response(messages=messages, model_identifier=self.model_identifier,)
        return self._extract_json_from_text(raw_llm_response=response)

    def calculate_lead_score(self):
        """Calculate comprehensive lead score"""
        scores = {}
        
        # Calculate individual category scores
        scores['intent_score'] = self._calculate_intent_score(self.data)
        scores['engagement_score'] = self._calculate_engagement_score(self.data)
        scores['demographic_score'] = self._calculate_demographic_score(self.data)
        scores['campaign_response_score'] = self._calculate_campaign_response_score(self.data)
        scores['urgency_score'] = self._calculate_urgency_score(self.data)
        
        # Calculate total score with model boost
        base_total = sum(scores.values())
        model_boost = self._get_model_boost(self.data)
        total_score = base_total + model_boost
        
        # Determine priority level and recommendations
        priority_level = self._determine_priority_level(total_score)
        recommendations = self._generate_recommendations(self.data, priority_level, scores)
        
        self.scores = scores
        self.total_score = total_score
        self.priority_level = priority_level
        self.recommended_actions = recommendations
        
        return {
            'category_scores': scores,
            'model_boost': model_boost,
            'total_score': total_score,
            'priority_level': priority_level,
            'recommended_actions': recommendations,
            'response_time': PRIORITY_LEVELS[priority_level]['response_time']
        }

    def generate_communication_brief(self):
        """Generate a communication brief for the sales team"""
        if not self.scores:
            self.calculate_lead_score()
            
        brief = {
            'lead_id': self.data.get('uuid', 'N/A'),
            'priority_level': self.priority_level,
            'total_score': self.total_score,
            #'response_time': PRIORITY_LEVELS[self.priority_level]['response_time'],
            'contact_info': {
                'phone': self.data.get('phone'),
                'email': self.data.get('email')
            },
            'customer_profile': {
                'location': f"{self.data.get('city', 'N/A')}, {self.data.get('pincode', 'N/A')}",
                'interested_models': self.data.get('model', 'N/A'),
                'source': self.data.get('source', 'N/A'),
                'preferred_colors': self.data.get('final_colour', [])
            },
            'key_interests': [],
            'recommended_actions': self.recommended_actions,
            'talking_points': []
        }
        
        # Add key interests based on data
        if self.data.get('technology'):
            brief['key_interests'].append('Technology features')
        if self.data.get('safety'):
            brief['key_interests'].append('Safety features')
        if self.data.get('variants_and_pricing'):
            brief['key_interests'].append('Pricing and variants')
        if self.data.get('finance_and_offer'):
            brief['key_interests'].append('Finance options')
            
        # Add talking points based on priority
        if self.priority_level == 'HOT':
            brief['talking_points'] = [
                'Lead shows high purchase intent',
                'Immediate follow-up required',
                'Consider exclusive offers',
                'Prioritize test drive scheduling'
            ]
        elif self.priority_level == 'WARM':
            brief['talking_points'] = [
                'Good engagement level',
                'Focus on product benefits',
                'Share detailed specifications',
                'Schedule showroom visit'
            ]
            
        return brief
    def complete_analysis(self):
        "having created the final response"
        lead_analysis = self.calculate_lead_score()
        ai_insights = self.get_ai_insights()
        comm_brief = self.generate_communication_brief()
        
        insights = {}
        insights['priority_level'] = lead_analysis['priority_level']
        insights['prioritization_score'] = lead_analysis['total_score']
        insights['customer_summary'] = {
                                        "contact_info": comm_brief.get("contact_info", {}),
                                        "customer_profile": comm_brief.get("customer_profile", {}),
                                        "key_interests": list(set(  # Merge and deduplicate key interests
                                            ai_insights.get("customer_insights", {}).get("key_interests", []) +
                                            comm_brief.get("key_interests", [])
                                        )),
                                        "preferred_models": ai_insights.get("customer_insights", {}).get("preferred_models", []),
                                        "preferred_colors": comm_brief.get("customer_profile", {}).get("preferred_colors", []),
                                        "budget_category":ai_insights.get("customer_insights", {}).get("budget_category", []),
                                    }
        insights["risk_factors"] = ai_insights.get("risk_factors",[])
        insights['talking_points'] = ai_insights.get("talking_points",[])
        insights["recommended_actions"] = comm_brief.get("recommended_actions",[])
        
        return insights
        
    def run(self):
        """Main execution method"""
        # Calculate lead scores
        #lead_analysis = self.calculate_lead_score()
        insights = self.complete_analysis()
        
        # Get AI insights
        # try:
        #ai_insights = self.get_ai_insights()
        # except:
        #     ai_insights = {"error": "AI insights unavailable"}
        
        # Generate communication brief
        # comm_brief = self.generate_communication_brief()
        
        return {
            # 'priority_level': lead_analysis['priority_level'],
            # 'prioritization_score':lead_analysis['total_score']
            "insights": insights
            #'ai_insights': ai_insights,
            #'communication_brief': comm_brief,
            #}
        }
if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        "uuid": "test-uuid-123",
        "source": "website",
        "utm_source": "facebook",
        "utm_medium": "ppc",
        "utm_campaign": "monsoon_promotional_campaign",
        "model": "Grand Vitara",
        "book_test_drive": True,
        "variants_and_pricing": True,
        "technology": True,
        "safety": True,
        "final_colour": ["Arctic White"],
        "phone": "9980838165",
        "email": "test@example.com",
        "city": "Bengaluru",
        "device": "laptop",
        "date": "2025-08-06"
    }
    
    # Save sample data to temp file for testing
    with open('temp_lead_data.json', 'w') as f:
        json.dump(sample_data, f)
    
    # Initialize and run agent
    lead_agent = LeadPrioritizationAgent('temp_lead_data.json', model_identifier='azure-gpt-4o')
    result = lead_agent.run()
    
    print("Lead Analysis Results:")
    print(json.dumps(result['lead_analysis'], indent=2))
    print(f"\nPriority Level: {result['lead_analysis']['priority_level']}")
    print(f"Total Score: {result['lead_analysis']['total_score']}")
    print(f"Recommended Actions: {result['lead_analysis']['recommended_actions']}")
    
    # Clean up temp file
    os.remove('temp_lead_data.json')

