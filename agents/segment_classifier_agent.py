from typing import Union, Dict, Any
from ai_service import ai_service_app
from agents.base_agent import BaseAgent
import requests
from bs4 import BeautifulSoup

class SegmentClassifierAgent(BaseAgent):
    def __init__(self, source, model_identifier='azure-gpt-4o'):
        super().__init__(source=source, model_identifier=model_identifier)
        self.model_identifier = model_identifier
        self.llm = lambda messages : ai_service_app.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        self.data = self._load_json(source=source)
        
        self.segment = None
        self.promotional_message = None
        self.media_links = None

    def _normalize_links(self, base: str, links: list):
        normalized = []
        from urllib.parse import urljoin
        for link in links:
            normalized.append(urljoin(base, link))
        return normalized

    def extract_media_links(self, brand_url: str, promotional_message: str, customer_segment: str) -> Dict[str, Any]:
        try:
            response = requests.get(brand_url, timeout=10)
            html = response.text
        except Exception as e:
            return {"error": f"Failed to fetch URL: {str(e)}"}

        soup = BeautifulSoup(html, "html.parser")
        image_links = [img["src"] for img in soup.find_all("img") if img.get("src")]
        video_links = [video["src"] for video in soup.find_all("video") if video.get("src")]
        image_links = self._normalize_links(brand_url, image_links)
        video_links = self._normalize_links(brand_url, video_links)

        prompt = f"""
        You are a Media Relevance Extraction AI.
        Based on the provided list of image and video links extracted from a brand's website, user's interaction history and a promotional message,
        select ONLY the links most relevant to showcasing the CAR or VEHICLE mentioned.
        Max 1 image and 1 video. This is a strict requirement.

        ### User Interaction Data:
        {self.data}

        ### Promotional Message:
        {promotional_message}

        ### Detected Customer Segment:
        {customer_segment}

        ### Image Links:
        {image_links}

        ### Video Links:
        {video_links}

        ### Rules:
        - Pick only the top MOST relevant media links.
        - Ignore UI icons, banners, logos, lazy-loading assets, etc.
        - You MUST return a JSON object in this exact format:

        {{
            "selected_images": ["<image1>", "<image2>", ...],
            "selected_videos": ["<video1>", "<video2>", ...]
        }}
        """
        messages = [{"role": "system", "content": prompt}]
        result = self.llm(messages)
        final_json = self.extract_json_from_llm_response(result)
        return final_json

    @property
    def default_segments(self):
        return ['Configurator Users', 'Price Explorers', 'Feature Seekers', 'Variant Comparers', 'Form Drop-offs', 'Window Shoppers']    

    def classify(self):
        prompt = f"""
        You are a Segment Classification AI. 
        You MUST classify the user's behavior into exactly ONE of the following predefined segments:

        {self.default_segments}

        ### Rules:
        - Choose ONLY from the above list.
        - Do NOT create new segments.
        - Base your classification strictly on the provided data.
        - Your final response MUST be valid JSON in the format:
        {{"detected_segment": "<one_of_the_segments>"}}

        ### User Data:
        {self.data}
        """

        messages = [{"role": "system", "content": prompt}]
        result : str = self.llm(messages)
        final_json = self.extract_json_from_llm_response(result)
        return final_json
    
    def generate_promotional_message(self, segment: str):
        prompt = f"""
        You are a Promotional Message Generation AI.
        Your job is to generate a short, personalized promotional message 
        tailored to the user's detected segment AND their interaction history.

        ### Detected Customer Segment:
        {segment}

        ### User Interaction Data:
        {self.data}

        ### Guidelines:
        - Message must be short (max 2530 words).
        - Tone must match the user's intent and segment behavior.
        - Message should subtly encourage conversion without sounding pushy.
        - Use emojis where relevant.
        - Since we don't know customer's name, use generic terms like 'Hey' or 'Hello' or whatever can be used to introduce the customer.
        - Keep it personalized and contextual based on segment actions.
        - Have it in a way that it's a subtle question.
        - Respond ONLY in valid JSON with the following format:

        {{
        "promotional_message": "<your short promotional message>"
        }}
        """

        messages = [{"role": "system", "content": prompt}]
        result: str = self.llm(messages)
        final_json = self.extract_json_from_llm_response(result)
        return final_json


    def run(self, brand_url: str = None):
        segment_json = self.classify()
        promo_json = self.generate_promotional_message(segment_json)

        segment = segment_json.get("detected_segment")
        promotional_message = promo_json.get("promotional_message")

        final_output = {**segment_json, **promo_json}  

        if brand_url is not None:
            media_json = self.extract_media_links(brand_url, promotional_message, segment)
            final_output['media_links'] = media_json

        return final_output
