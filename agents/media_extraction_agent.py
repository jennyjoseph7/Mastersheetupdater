from typing import Dict, List
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from ai_service import ai_service_app
from agents.base_agent import BaseAgent


class MediaExtractionAgent(BaseAgent):

    def __init__(self, url: str, model_identifier='azure-gpt-4o'):
        self.model_identifier = model_identifier
        self.llm = lambda messages: ai_service_app.get_llm_response(
            messages=messages,
            model_identifier=self.model_identifier
        )
        self.url = url

    def fetch_page(self) -> str:
        """Downloads the raw HTML content from the URL."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(self.url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text

    def extract_media(self) -> Dict[str, List[str]]:
        """Extracts all image and video URLs from the webpage."""
        html = self.fetch_page()
        soup = BeautifulSoup(html, "html.parser")

        images = set()
        videos = set()

        # --- Extract Images ---
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-original")
            if src:
                full_url = urljoin(self.url, src)
                images.add(full_url)

        # Extract images inside <source> tags (for <picture>)
        for source in soup.find_all("source"):
            src = source.get("srcset") or source.get("src")
            if src:
                full_url = urljoin(self.url, src.split(" ")[0])
                images.add(full_url)

        # --- Extract Videos ---
        for video in soup.find_all("video"):
            # direct video src
            if video.get("src"):
                videos.add(urljoin(self.url, video.get("src")))

            # check <source> inside <video>
            for source in video.find_all("source"):
                src = source.get("src")
                if src:
                    videos.add(urljoin(self.url, src))

        # Additional check: common video file formats in links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if any(href.lower().endswith(ext) for ext in [".mp4", ".mov", ".webm", ".m4v"]):
                videos.add(urljoin(self.url, href))

        return {
            "images": list(images),
            "videos": list(videos)
        }

    def run(self) -> Dict[str, List[str]]:
        """Main method to run the extraction."""
        try:
            media = self.extract_media()
            return media
        except Exception as e:
            return {"error": str(e)}



