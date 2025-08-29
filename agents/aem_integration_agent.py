from typing import Union, Dict, Any
try:
    from .base_agent import BaseAgent
except:
    from base_agent import BaseAgent
    
class AEMIntegrationAgent(BaseAgent):
    def __init__(self, source: dict, model_identifier='azure-gpt-4o'):
        self.source = self._load_json(source=source)
        self.model_identifier = model_identifier

    def fetch_aem_data(self):
        customer_uuid = self.source.get("uuid", None)
        interaction_data = self.fetch_from_aem_by_uuid(customer_uuid)
        self.source.update(interaction_data)
        return self.source

    def fetch_from_aem_by_uuid(self, uuid: str) -> dict:
        # TODO: Replace this stub with actual fetch logic from AEM DB / API
        mock_interactions = {
            "123e4567-e89b-12d3-a456-426614174000": {
                "model": "Grand Vitara",
                "url": "https://www.nexaexperience.com/grand-vitara",
                "date": "2025-07-24",
                "time": "16:30 +530",
                "hd_view": "off",
                "exterior": True,
                "interior": False,
                "performance": False,
                "technology": True,
                "safety": True,
                "configure": False,
                "suzuki_connect": False,
                "colours": ["Arctic White", "Opulent Red"],
                "final_colour": ["Arctic White"],
                "exterior_views": 3,
                "technology_views": ["EV mode", "Head Up Display", "Wireless Charging"],
                "safety_views": ["6 Airbags As Standard", "Hill-descent Control"],
                "variants": [],
                "brochure_download": False,
                "variants_and_pricing": True,
                "build_your_own": False,
                "transmission_types": ["all"],
                "powertrains": ["strong_hybrid"],
                "compared_cars": ["invicto", "fronx"],
                "finance_and_offer": False,
                "locate_dealer": True,
                "book_test_drive": True
            },
            "8b92e674-6b43-4a8f-bc14-7b3f92a1d9cb": {
                "model": "Grand Vitara",
                "url": "https://www.nexaexperience.com/grand-vitara",
                "date": "2025-08-10",
                "time": "15:45 +530",
                "hd_view": "on",
                "exterior": True,
                "interior": True,
                "performance": True,
                "technology": True,
                "safety": True,
                "configure": True,
                "suzuki_connect": True,
                "colours": ["Nexa Blue", "Grandeur Grey", "Arctic White"],
                "final_colour": ["Nexa Blue"],
                "exterior_views": 5,
                "technology_views": ["Head Up Display", "Wireless Charging", "360 View Camera"],
                "safety_views": ["6 Airbags As Standard", "ABS with EBD", "Hill-hold Assist"],
                "brochure_download": True,
                "variants_and_pricing": True,
                "build_your_own": True,
                "transmission_types": ["manual", "automatic"],
                "powertrains": ["mild_hybrid", "strong_hybrid"],
                "compared_cars": ["fronx", "hyryder", "seltos"],
                "finance_and_offer": True,
                "locate_dealer": True,
                "book_test_drive": True
            },
            "456b7890-f12c-34d5-b678-901234567890": {
                "model": "Fronx",
                "url": "https://www.nexaexperience.com/fronx",
                "date": "2025-07-25",
                "time": "14:15 +530",
                "hd_view": "on",
                "exterior": True,
                "interior": True,
                "performance": True,
                "technology": False,
                "safety": True,
                "configure": True,
                "suzuki_connect": True,
                "colours": ["Brave Khaki", "Splendid Silver", "Earthen Brown"],
                "final_colour": ["Brave Khaki", "Splendid Silver"],
                "exterior_views": 5,
                "interior_views": ["Dashboard", "Seats", "Boot Space"],
                "performance_views": ["Turbo Engine", "Fuel Efficiency"],
                "safety_views": ["ABS with EBD", "Dual Airbags", "ESP"],
                "brochure_download": True,
                "variants_and_pricing": True,
                "build_your_own": True,
                "transmission_types": ["manual", "automatic"],
                "powertrains": ["petrol", "cng"],
                "compared_cars": ["baleno", "swift"],
                "finance_and_offer": True,
                "locate_dealer": True,
                "book_test_drive": False
            },
            "789c0123-d45e-67f8-9012-345678901234": {
                "model": "Invicto",
                "url": "https://www.nexaexperience.com/invicto",
                "date": "2025-07-26",
                "time": "10:45 +530",
                "hd_view": "on",
                "exterior": False,
                "interior": True,
                "performance": True,
                "technology": True,
                "safety": False,
                "configure": False,
                "suzuki_connect": True,
                "colours": ["Grandiose White", "Intenso Brown"],
                "final_colour": ["Grandiose White"],
                "interior_views": ["Captain Seats", "Premium Dashboard", "Ambient Lighting"],
                "performance_views": ["Hybrid Powertrain", "AWD System"],
                "technology_views": ["10-inch Infotainment", "360-degree Camera", "Premium Audio"],
                "brochure_download": True,
                "variants_and_pricing": False,
                "build_your_own": False,
                "transmission_types": ["cvt"],
                "powertrains": ["hybrid"],
                "compared_cars": ["grand_vitara", "xl6"],
                "finance_and_offer": True,
                "locate_dealer": False,
                "book_test_drive": True
            },
            "012d3456-e78f-90ab-cdef-567890123456": {
                "model": "Baleno",
                "url": "https://www.nexaexperience.com/baleno",
                "date": "2025-07-27",
                "time": "18:20 +530",
                "hd_view": "off",
                "exterior": True,
                "interior": False,
                "performance": False,
                "technology": True,
                "safety": True,
                "configure": True,
                "suzuki_connect": False,
                "colours": ["Premium Silver", "Phoenix Red", "Grandeur Grey"],
                "final_colour": ["Premium Silver"],
                "exterior_views": 4,
                "technology_views": ["SmartPlay Pro+", "Cruise Control"],
                "safety_views": ["Dual Airbags", "ABS", "Reverse Parking Sensors"],
                "brochure_download": False,
                "variants_and_pricing": True,
                "build_your_own": True,
                "transmission_types": ["manual", "amt"],
                "powertrains": ["petrol"],
                "compared_cars": ["fronx", "swift"],
                "finance_and_offer": False,
                "locate_dealer": True,
                "book_test_drive": True
            }
        }
        return mock_interactions.get(uuid, {})

    def run(self):
        return self.fetch_aem_data()
