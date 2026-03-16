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
            },
            "123e4567-e89b-12d3-a456-426614174698": {
                "model": "Seltos",
                "url": "https://www.kia.com/in/our-vehicles/seltos/showroom.html",
                "date": "2025-07-24",
                "time": "16:30 +530",
                "hd_view": "off",
                "exterior": True,
                "interior": True,
                "performance": True,
                "technology": True,
                "safety": True,
                "configure": True,
                "suzuki_connect": False,
                "colours": ["Pewter Olive (Green)", "Clear White", "Sparkling Silver", "Gravity Grey", "Imperial Blue", "Intense Red"],
                "final_colour": ["Pluton Blue"],
                "exterior_views": 5,
                "interior_views": ["Dashboard", "Seats", "Boot Space"],
                "performance_views": ["Turbo Engine", "Fuel Efficiency"],
                "safety_views": ["6 Airbags As Standard", "ESC", "VSM", "HAC"],
                "variants_and_pricing": True,
                "build_your_own": True,
                "transmission_types": ["manual", "automatic", "dct"],
                "powertrains": ["petrol", "diesel"],
                "compared_cars": ["creta", "harrier", "Grand Vitara"],
                "finance_and_offer": True,
                "locate_dealer": True,
                "book_test_drive": True
            },
            "8b92e674-6b43-4a8f-bc14-7b3f92a1d8cb": {
                "model": "Sonet",
                "url": "https://www.kia.com/in/our-vehicles/sonet/showroom.html",
                "date": "2025-08-10",
                "time": "15:45 +530",
                "hd_view": "on",
                "exterior": True,
                "interior": True,
                "performance": False,
                "technology": True,
                "safety": True,
                "configure": True,
                "suzuki_connect": False,
                "colours": ["Intense Red", "Beige Gold", "Aurora Black Pearl", "Steel Silver", "Intense Red"],
                "final_colour": ["Intense Red"],
                "exterior_views": 5,
                "interior_views": ["Dashboard", "Seats", "Boot Space"],
                "performance_views": ["Turbo Engine", "Fuel Efficiency"],
                "safety_views": ["6 Airbags As Standard", "ESC", "VSM", "HAC"],
                "variants_and_pricing": True,
                "build_your_own": True,
                "transmission_types": ["manual", "automatic", "dct"],
                "powertrains": ["petrol", "diesel"],
                "compared_cars": ["breeze", "venue","Taigun"],
                "finance_and_offer": True,
                "locate_dealer": True,
                "book_test_drive": True
            },
            "456b7890-f12c-34d5-b678-101234569890": {
                "model": "Carens",
                "url": "https://www.kia.com/in/our-vehicles/carens/showroom.html",
                "date": "2025-07-25",
                "time": "14:15 +530",
                "hd_view": "on",
                "exterior": True,
                "interior": True,
                "performance": False,
                "technology": True,
                "safety": True,
                "configure": True,
                "suzuki_connect": False,
                "colours": ["Pewter Olive (Green)", "Clear White", "Sparkling Silver", "Gravity Grey", "Imperial Blue"],
                "final_colour": ["mperial Blue"],
                "exterior_views": 5,
                "interior_views": ["Dashboard", "Seats", "Boot Space"],
                "performance_views": ["Turbo Engine", "Fuel Efficiency"],
                "safety_views": ["6 Airbags As Standard", "ESC", "VSM", "HAC"],
                "variants_and_pricing": True,
                "build_your_own": True,
                "transmission_types": ["manual", "automatic", "dct"],
                "powertrains": ["petrol", "diesel"],
                "compared_cars": ["XL6", "Ertiga"],
                "finance_and_offer": True,
                "locate_dealer": True,
                "book_test_drive": True
            },
            "789c0123-d45e-67g8-9012-345678991284": {
                "model": "Carnival",
                "url": "https://www.kia.com/in/our-vehicles/carnival/showroom.html",
                "date": "2025-07-26",
                "time": "10:45 +530",
                "hd_view": "on",
                "exterior": True,
                "interior": True,
                "performance": False,
                "technology": True,
                "safety": True,
                "configure": True,
                "suzuki_connect": False,
                "colours": ["Glacier White Pearl", "Fusion Black"],
                "final_colour": ["Intense Red"],
                "exterior_views": 5,
                "interior_views": ["Dashboard", "Seats", "Boot Space"],
                "performance_views": ["Turbo Engine", "Fuel Efficiency"],
                "safety_views": ["6 Airbags As Standard", "ESC", "VSM", "HAC"],
                "variants_and_pricing": True,
                "build_your_own": True,
                "transmission_types": ["manual", "automatic", "dct"],
                "powertrains": ["petrol", "diesel"],
                "compared_cars": ["Vellfire", "Hycross"],
                "finance_and_offer": True,
                "locate_dealer": True,
                "book_test_drive": True
            },
            "012d3656-e78f-90vb-cdef-567890123656": {
                "model": "EV6",
                "url": "https://www.kia.com/in/our-vehicles/ev6/showroom.html",
                "date": "2025-07-27",
                "time": "18:20 +530",
                "hd_view": "off",
                "exterior": True,
                "interior": True,
                "performance": True,
                "technology": True,
                "safety": True,
                "configure": True,
                "suzuki_connect": False,
                "colours": ["Moonscape", "Aurora Black Pearl", "Snow White Pearl", "Runway Red", "Yacht Blue"],
                "final_colour": ["Moonscape"],
                "exterior_views": 4,
                "interior_views": ["Dashboard", "Seats", "Boot Space"],
                "performance_views": ["Turbo Engine", "Fuel Efficiency"],
                "safety_views": ["6 Airbags As Standard", "ESC", "VSM", "HAC"],
                "variants_and_pricing": True,
                "build_your_own": True,
                "transmission_types": ["automatic"],
                "powertrains": ["electric"],
                "compared_cars": ["BYD Seal", "Curvv EV"],
                "finance_and_offer": True,
                "locate_dealer": True,
                "book_test_drive": True
            },
            "9999e1234-abcd-56ef-9012-3456fc3ac01":{
                "model": "C5 Aircross",
                "url": "https://www.citroen.in/c5-aircross",
                "date": "2025-11-17",
                "time": "19:00 +530",
                "hd_view": "on",
                "exterior": True,
                "interior": True,
                "performance": True,
                "technology": True,
                "safety": True,
                "configure": True,
                "citroen_connect": True,
                "colours": ["Pearl White","Cumulus Grey","Platinum Grey","Perla Nera Black","Eclipse Blue","Pearl White with Black Roof","Cumulus Grey with Black Roof"],
                "final_colour": ["Pearl White with Black Roof"],
                "exterior_views": 6,
                "interior_views": ["Advanced Comfort Seats with High-Density Foam","Progressive Hydraulic Cushions Suspension","Best-in-Class Rear Seat Modularity (Sliding / Reclining)","Panoramic Sunroof","12.3-inch Digital Instrument Cluster","10-inch Touchscreen with Wireless Connectivity"],
                "performance_views": ["2.0L Diesel Engine (177 PS, 400 Nm, 8AT)","Multi-Drive Modes (Eco, Normal, Sport)","18-inch Alloy Wheels for Enhanced Ride Comfort"],
                "safety_views": ["6 Airbags Standard","ABS with EBD and ESP","Blind Spot Monitoring","Front & Rear Park Assist with 180° Camera","Advanced Driver Attention Alert"],
                "variants_and_pricing": True,
                "build_your_own": True,
                "transmission_types": ["automatic"],
                "powertrains": ["diesel"],
                "compared_cars": ["Hyundai Tucson","Jeep Compass","Volkswagen Tiguan","Skoda Kodiaq"],
                "finance_and_offer": True,
                "locate_dealer": True,
                "book_test_drive": True
                },
            "789e1234-abcd-56ef-9012-3456789c3ac01": {
                "model": "C3 Aircross",
                "url": "https://www.citroen.in/c3-aircross",
                "date": "2025-11-17",
                "time": "19:20 +530",
                "hd_view": "on",
                "exterior": True,
                "interior": True,
                "performance": True,
                "technology": True,
                "safety": True,
                "configure": True,
                "citroen_connect": False,
                "colours": ["Polar White","Cosmo Blue","Platinum Grey","Steel Grey","Zesty Orange","Polar White with Zesty Orange Roof","Cosmo Blue with Platinum Grey Roof"],
                "final_colour": ["Polar White with Zesty Orange Roof"],
                "exterior_views": 6,
                "interior_views": ["Dual-Tone Premium Dashboard","3rd Row Modular Seating","Large Panoramic Windows","Best-in-Segment 511L Boot Space","Ambient Lighting","Rear AC Vents"],
                "performance_views": ["1.2L PureTech Turbo Engine (110 PS, 190 Nm)","1.2L PureTech Turbo Engine (110 PS, 205 Nm AT)","Fuel Efficiency 18.5–19.3 kmpl","0–100 kmph in 10.2 sec"],
                "safety_views": ["High Strength Body Structure","6 Airbags Standard","ESP with Hill Hold Assist","Tyre Pressure Monitoring System (TPMS)","Rear Parking Camera & Sensors"],
                "variants_and_pricing": True,
                "build_your_own": True,
                "transmission_types": ["manual", "automatic"],
                "powertrains": ["petrol"],
                "compared_cars": ["Honda Elevate","MG Astor","Nissan Kicks","Kia Seltos","Toyota Urban Cruiser Hyryder"],
                "finance_and_offer": True,
                "locate_dealer": True,
                "book_test_drive": True
                },
            "789e7890-abcd-56ef-9982-3456789c3ac01":{
                "model": "Toyota Camry",
                "url": "https://www.toyotabharat.com/showroom/camry/",
                "date": "2025-07-24",
                "time": "16:30 +530",
                "hd_view": "off",
                "exterior": True,
                "interior": True,
                "performance": True,
                "technology": True,
                "safety": True,
                "configure": True,
                "toyota_connect": False,
                "colours": [
                    "Platinum White Pearl",
                    "Attitude Black"
                ],
                "final_colour": [
                    "Platinum White Pearl"
                ],
                "exterior_views": 4,
                "technology_views": [
                    "Hybrid System Display",
                    "Wireless Apple CarPlay",
                    "Premium JBL Audio"
                ],
                "safety_views": [
                    "Toyota Safety Sense",
                    "Blind Spot Monitor"
                ],
                "variants": [],
                "brochure_download": True,
                "variants_and_pricing": True,
                "build_your_own": False,
                "transmission_types": [
                    "automatic"
                ],
                "powertrains": [
                    "strong_hybrid"
                ],
                "compared_cars": [
                    "Honda Accord",
                    "Skoda Superb"
                ],
                "finance_and_offer": False,
                "locate_dealer": False,
                "book_test_drive": True
            },
        "789e1234-abcd-56ef-9012-30056789c9ac09":{
            "model": "Hyundai Exter",
            "url": "https://www.hyundai.com/in/en/find-a-car/exter/highlights",
            "date": "2025-07-24",
            "time": "16:30 +530",
            "hd_view": "off",
            "exterior": True,
            "interior": True,
            "performance": False,
            "technology": True,
            "safety": True,
            "configure": False,
            "suzuki_connect": False,
            "colours": [
                "Atlas White",
                "Ranger Khaki"
            ],
            "final_colour": [
                "Atlas White"
            ],
            "exterior_views": 3,
            "technology_views": [
                "Voice Enabled Smart Controls",
                "Dashcam with Dual Camera",
                "Wireless Charging"
            ],
            "safety_views": [
                "6 Airbags",
                "Electronic Stability Control"
            ],
            "variants": [],
            "brochure_download": False,
            "variants_and_pricing": True,
            "build_your_own": False,
            "transmission_types": [
                "manual",
                "AMT"
            ],
            "powertrains": [
                "petrol",
                "CNG"
            ],
            "compared_cars": [
                "Tata Punch",
                "Maruti Ignis"
            ],
            "finance_and_offer": False,
            "locate_dealer": True,
            "book_test_drive": True
            },
        "789e1d23s4-abcd-56ef-9012-3805878dcd9acd09":{
            "model": "Jeep Wrangler",
            "url": "https://www.jeep-india.com/wrangler-jl.html",
            "date": "2025-07-24",
            "time": "16:30 +530",
            "hd_view": "off",
            "exterior": True,
            "interior": True,
            "performance": True,
            "technology": True,
            "safety": True,
            "configure": False,
            "suzuki_connect": False,

            "colours": [
                "Bright White",
                "Black",
                "Firecracker Red",
                "Granite Crystal",
                "Hydro Blue"
            ],
            "final_colour": [
                "Bright White"
            ],

            "exterior_views": 5,
            "interior_views": 4,

            "performance_views": [
                "2.0L Turbo Petrol Engine",
                "4x4 Off-Road Capability",
                "Command-Trac 4WD System",
                "Rubicon Off-Road Package"
            ],

            "technology_views": [
                "UConnect Touchscreen",
                "Apple CarPlay & Android Auto",
                "Premium Alpine Music System",
                "Digital Instrument Cluster"
            ],

            "safety_views": [
                "Dual Front Airbags",
                "Electronic Stability Control",
                "Hill Start Assist",
                "Rear Parking Camera & Sensors"
            ],

            "variants": [
                "Wrangler Unlimited",
                "Wrangler Rubicon"
            ],

            "brochure_download": True,
            "variants_and_pricing": True,
            "build_your_own": False,

            "transmission_types": [
                "Automatic"
            ],

            "powertrains": [
                "Petrol"
            ],

            "compared_cars": [
                "Land Rover Defender",
                "Toyota Fortuner",
                "Ford Bronco (Global)"
            ],

            "finance_and_offer": True,
            "locate_dealer": True,
            "book_test_drive": True
        }


            
        }
        return mock_interactions.get(uuid, {})

    def run(self):
        return self.fetch_aem_data()
