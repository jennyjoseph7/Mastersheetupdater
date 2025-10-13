import os 
import sys 
import traceback
from typing import Union, Dict, Any
from urllib.parse import urlparse
import requests
import json

class BaseAgent:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def _load_json(self, source : Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Load JSON from a dict, local path, or URL."""
        if isinstance(source, (dict, list)):
            return source 

        if isinstance(source, str):
            parsed = urlparse(source)
            if parsed.scheme in ("http", "https"):
                response = requests.get(source)
                response.raise_for_status()
                return response.json()
            elif os.path.isfile(source):
                with open(source, 'r') as f:
                    return json.load(f)

        raise ValueError(f"Invalid JSON source: {source}")
    
    def extract_json_from_llm_response(self, response: str) -> dict:
        stack, start = [], None
        for i, ch in enumerate(response):
            if ch in "{[":
                if not stack:
                    start = i
                stack.append(ch)
            elif ch in "}]":
                if not stack:
                    continue
                opening = stack.pop()
                if (opening == "{" and ch != "}") or (opening == "[" and ch != "]"):
                    return None
                if not stack:
                    json_str = response[start:i + 1]
                    try:
                        return json.loads(json_str)
                    except Exception:
                        return None
        return None

# import os 
# import sys 
# import traceback
# from typing import Union, Dict, Any, List
# from urllib.parse import urlparse
# import requests
# import json

# class BaseAgent:
#     def __init__(self):
#         pass

#     def _load_json(self, source: Union[Dict[str, Any], List[Any], str]) -> Union[Dict[str, Any], List[Any]]:
#         """
#         Load JSON from a dict, list, local path, or URL with comprehensive error handling.
#         """
#         # If source is already a dict or list, return it directly
#         if isinstance(source, (dict, list)):
#             return source 

#         if isinstance(source, str):
#             parsed = urlparse(source)
            
#             # Handle HTTP/HTTPS URLs
#             if parsed.scheme in ("http", "https"):
#                 try:
#                     response = requests.get(source, timeout=30)
#                     response.raise_for_status()
#                     return response.json()
#                 except requests.exceptions.RequestException as e:
#                     raise ValueError(f"Failed to fetch JSON from URL {source}: {e}")
#                 except json.JSONDecodeError as e:
#                     raise ValueError(f"Invalid JSON received from URL {source}: {e}")
            
#             # Handle local file paths
#             else:
#                 # Resolve relative paths to absolute
#                 absolute_path = os.path.abspath(source)
                
#                 # Check if file exists
#                 if not os.path.exists(absolute_path):
#                     # If file doesn't exist, check if this is one of the known hardcoded data files
#                     hardcoded_data = self._get_hardcoded_data(absolute_path)
#                     if hardcoded_data is not None:
#                         return hardcoded_data
#                     raise ValueError(f"JSON file not found: {absolute_path}")
                
#                 # Check if it's actually a file
#                 if not os.path.isfile(absolute_path):
#                     raise ValueError(f"Path is not a file: {absolute_path}")
                
#                 # Check file size
#                 file_size = os.path.getsize(absolute_path)
#                 if file_size == 0:
#                     # If file is empty, check for hardcoded data
#                     hardcoded_data = self._get_hardcoded_data(absolute_path)
#                     if hardcoded_data is not None:
#                         return hardcoded_data
#                     raise ValueError(f"JSON file is empty: {absolute_path}")
                
#                 # Try to read and parse the file
#                 try:
#                     with open(absolute_path, 'r', encoding='utf-8') as f:
#                         return json.load(f)
#                 except json.JSONDecodeError as e:
#                     # If JSON parsing fails, check for hardcoded data
#                     hardcoded_data = self._get_hardcoded_data(absolute_path)
#                     if hardcoded_data is not None:
#                         return hardcoded_data
#                     raise ValueError(f"Invalid JSON in file {absolute_path}: {e}")
#                 except Exception as e:
#                     raise ValueError(f"Error reading file {absolute_path}: {e}")

#         raise ValueError(f"Invalid JSON source type: {type(source)}")

#     def _get_hardcoded_data(self, file_path: str) -> Union[Dict, List, None]:
#         """
#         Return hardcoded data for known files if they exist in the function.
#         This handles the case where data is hardcoded in load_special_json().
#         """
#         filename = os.path.basename(file_path)
        
#         # Map filenames to their hardcoded data
#         hardcoded_data_map = {
#             'fronx.json': [
#                 {
#       "price": 800000.0,
#       "fuel_type": "Petrol",
#       "product_id": "fronx-sigma-1.2l-petrol",
#       "brand_name": "Maruti Suzuki",
#       "model_name": "Fronx",
#       "variant_name": "Sigma 1.2L",
#       "product_name": "Fronx Sigma 1.2L",
#       "general": "5-seater compact SUV, manual transmission, warranty up to 2 years, based on Suzuki HEARTECT platform.",
#       "branding_and_looks": "Length 3995 mm, Width 1765 mm, Height 1550 mm, Wheelbase 2520 mm, steel wheels with wheel covers, halogen projector headlamps, NEXWave grille, connected LED RCL (non-lit centre).",
#       "safety_and_environment": "Dual airbags, ABS with EBD, ESP, hill-hold assist, ISOFIX child seat anchors, pedestrian protection compliance, BS-VI norms.",
#       "comfort_and_convenience": "Manual AC, tilt steering, power windows (front & rear), driver window auto up/down with anti-pinch, 60:40 split rear seats, central locking with keyless entry.",
#       "technology_and_performance": "1.2L K-Series Dual Jet Dual VVT petrol engine, 1197 cc, max power 89.73 PS @ 6000 rpm, torque 113 Nm @ 4400 rpm, 5MT gearbox, mileage 21.79 kmpl, fuel tank 37L, MacPherson Strut front & Torsion Beam rear suspension.",
#       "infotainment_and_connectivity": "Basic audio unit with speakers, gear shift indicator (MT only), seatbelt reminders, MID display."
#     },
#     {
#       "price": 900000.0,
#       "fuel_type": "Petrol / CNG",
#       "product_id": "fronx-delta-1.2l-petrol-cng",
#       "brand_name": "Maruti Suzuki NEXA",
#       "model_name": "Fronx",
#       "variant_name": "Delta 1.2L",
#       "product_name": "Fronx Delta 1.2L",
#       "general": "5-seater compact SUV available in petrol MT/AMT and CNG MT, warranty up to 2 years, built on Suzuki HEARTECT platform.",
#       "branding_and_looks": "Dual-tone interiors, halogen projector headlamps, LED DRLs, NEXWave grille, steel wheels with wheel covers, roof spoiler.",
#       "safety_and_environment": "Dual airbags, ABS with EBD, ESP, hill-hold assist, ISOFIX, rear parking sensors, rear defogger, high-tensile steel body structure.",
#       "comfort_and_convenience": "Manual AC with heater, tilt steering, electrically adjustable ORVMs, steering-mounted audio controls, power windows, 60:40 split rear seats.",
#       "technology_and_performance": "1.2L K-Series petrol engine with Idle Start Stop (ISS), petrol: 89.73 PS & 113 Nm, CNG: 77.5 PS & 98.5 Nm, 5MT/AMT, fuel efficiency 22.89 kmpl (petrol AMT), 28.51 km/kg (CNG), 37L petrol tank or 55L CNG tank, MacPherson Strut & Torsion Beam suspension.",
#       "infotainment_and_connectivity": "17.78 cm SmartPlay Pro touchscreen, wireless Android Auto & Apple CarPlay, 4 speakers, voice assistant ('Hi Suzuki'), OTA updates, USB & Bluetooth connectivity."
#     },
#     {
#       "price": 1100000.0,
#       "fuel_type": "Petrol (Turbo)",
#       "product_id": "fronx-alpha-1.0l-turbo-petrol",
#       "brand_name": "Maruti Suzuki NEXA",
#       "model_name": "Fronx",
#       "variant_name": "Alpha 1.0L Turbo",
#       "product_name": "Fronx Alpha 1.0L Turbo",
#       "general": "Top-end compact SUV with 1.0L Turbo Boosterjet petrol engine, available in MT/AT with paddle shifters, warranty up to 2 years.",
#       "branding_and_looks": "Length 3995 mm, Width 1765 mm, Height 1550 mm, Wheelbase 2520 mm, precision cut alloy wheels, LED multi-reflector headlamps with NEXTre’ DRLs, full connected LED RCL (lit centre), dual-tone body options, shark fin antenna, premium chrome accents.",
#       "safety_and_environment": "6 airbags (front, side, curtain), ESP, hill-hold assist, ABS with EBD, 360-view camera, rear parking sensors with infographic display, ISOFIX, TPMS, Suzuki Connect telematics, BS-VI norms.",
#       "comfort_and_convenience": "Automatic climate control, rear AC vents, wireless charger, cruise control, push start/stop with smart key, tilt & telescopic steering, height-adjustable driver seat, rear fast charging sockets (Type A & C), leather-wrapped flat-bottom steering wheel, 60:40 folding seats.",
#       "technology_and_performance": "998 cc Boosterjet turbo engine, max power 100.06 PS @ 5500 rpm, torque 147.6 Nm @ 2000-4500 rpm, 5MT & 6AT with paddle shifters, Smart Hybrid system with torque assist & regenerative braking, mileage 20.01 kmpl (AT), 21.5 kmpl (MT), 37L tank, MacPherson Strut & Torsion Beam suspension, ventilated disc front & drum rear brakes.",
#       "infotainment_and_connectivity": "22.86 cm SmartPlay Pro+ HD touchscreen, ARKAMYS Surround Sense premium audio, 6 speakers & tweeters, wireless Android Auto & Apple CarPlay, onboard voice assistant, HUD, 360-degree camera, Suzuki Connect with Alexa & smartwatch integration."
#     }
#             ],
#             'grand_vitara.json': [
#                 {
#       "price": 1050000.0,
#       "fuel_type": "Petrol",
#       "product_id": "grand-vitara-sigma-petrol",
#       "brand_name": "Maruti Suzuki NEXA",
#       "model_name": "Grand Vitara",
#       "variant_name": "Sigma",
#       "product_name": "Grand Vitara Sigma",
#       "general": "5-seater SUV, petrol engine with manual transmission, 2WD, warranty up to 2 years.",
#       "branding_and_looks": "Length 4345 mm, Width 1795 mm, Height 1645 mm, Wheelbase 2600 mm, projector headlamps with LED DRLs, LED tail lamps, shark fin antenna, alloy wheels (215/60 R17).",
#       "safety_and_environment": "6 airbags standard, ABS with EBD, ESP, Hill Hold Assist, TPMS, Suzuki TECT platform with high tensile steel, complies with BS-VI norms.",
#       "comfort_and_convenience": "Manual AC with rear AC vents, adjustable tilt steering, keyless entry with push start/stop button, power windows, fabric seats.",
#       "technology_and_performance": "1462 cc petrol engine, max power 103.06 PS @ 6000 rpm, torque 136.8 Nm @ 4400 rpm, mileage 21.11 kmpl (MT), 45L fuel tank, MacPherson strut front, torsion beam rear suspension.",
#       "infotainment_and_connectivity": "17.78 cm SmartPlay Pro touchscreen, Android Auto & Apple CarPlay, steering-mounted controls, MID with fuel consumption and gear shift indicator."
#     },
#     {
#       "price": 1450000.0,
#       "fuel_type": "Petrol / Hybrid",
#       "product_id": "grand-vitara-alpha+-petrol-hybrid",
#       "brand_name": "Maruti Suzuki NEXA",
#       "model_name": "Grand Vitara",
#       "variant_name": "Alpha+",
#       "product_name": "Grand Vitara Alpha+",
#       "general": "Premium SUV with Intelligent Electric Hybrid system, 5-seater, e-CVT automatic transmission, 2WD, warranty up to 2 years.",
#       "branding_and_looks": "Length 4345 mm, Width 1795 mm, Height 1645 mm, Wheelbase 2600 mm, dual-tone exterior options, panoramic sunroof, ambient lighting, leatherette upholstery.",
#       "safety_and_environment": "6 airbags, 360 view camera, ABS with EBD, ESP, Hill Hold Assist, electronic parking brake with auto hold, Suzuki TECT crash compliance, ISOFIX child seat anchors.",
#       "comfort_and_convenience": "Ventilated seats, 8-way powered driver seat, auto AC with rear vents, wireless charger, rear door sunshades, paddle shifters, keyless entry with push start.",
#       "technology_and_performance": "1490 cc petrol hybrid engine, system max power 115.56 PS, e-CVT automatic transmission, EV/Normal/Power drive modes, fuel efficiency 27.97 kmpl, 45L fuel tank, MacPherson strut front and torsion beam rear suspension.",
#       "infotainment_and_connectivity": "22.86 cm SmartPlay Pro+ touchscreen with wireless Android Auto & Apple CarPlay, Clarion premium sound system, 7-inch TFT multi-information display, head-up display, Suzuki Connect with smartwatch & Alexa compatibility."
#     },
#     {
#       "price": 1550000.0,
#       "fuel_type": "Petrol (ALLGRIP)",
#       "product_id": "grand-vitara-alpha-allgrip-petrol",
#       "brand_name": "Maruti Suzuki",
#       "model_name": "Grand Vitara",
#       "variant_name": "Alpha ALLGRIP",
#       "product_name": "Grand Vitara Alpha ALLGRIP",
#       "general": "SUV with Suzuki ALLGRIP Select 4WD technology, petrol engine, available with manual and automatic transmission, 5-seater, warranty up to 2 years.",
#       "branding_and_looks": "Length 4345 mm, Width 1795 mm, Height 1645 mm, Wheelbase 2600 mm, roof rails, skid plates, LED DRLs, LED projector headlamps, alloy wheels.",
#       "safety_and_environment": "6 airbags, ABS with EBD, ESP, Hill Descent Control, TPMS, ISOFIX, Suzuki TECT crash energy absorption platform.",
#       "comfort_and_convenience": "Panoramic sunroof, ventilated seats, rear AC vents, 60:40 folding rear seats, adjustable tilt & telescopic steering, push start/stop, cruise control.",
#       "technology_and_performance": "1462 cc petrol engine, max power 103.06 PS @ 6000 rpm, torque 136.8 Nm, mileage 19.20 kmpl (ALLGRIP AT), 45L fuel tank, selectable drive modes (Auto, Sport, Snow, Lock).",
#       "infotainment_and_connectivity": "SmartPlay Pro+ touchscreen, wireless charging, 7-inch TFT MID, head-up display, premium Clarion sound, Suzuki Connect with real-time telematics and alerts."
#     }
#             ],
#             'baleno.json': [
#                 {
#       "price": 700000.0,
#       "fuel_type": "Petrol",
#       "product_id": "baleno-sigma-mt-petrol",
#       "brand_name": "Maruti Suzuki NEXA",
#       "model_name": "Baleno",
#       "variant_name": "Sigma MT",
#       "product_name": "Baleno Sigma MT",
#       "general": "Premium hatchback, 5-seater, manual transmission, based on HEARTECT platform, 2 years standard warranty.",
#       "branding_and_looks": "Length 3990 mm, Width 1745 mm, Height 1500 mm, Wheelbase 2520 mm, Steel wheels with full covers, Halogen projector headlamps, basic exterior styling, Nexa Signature LED tail lamps.",
#       "safety_and_environment": "Dual front airbags, ABS with EBD, ESP with Hill Hold, seatbelt pre-tensioners with force limiters, ISOFIX child seat anchors, pedestrian protection compliance, BS-VI engine.",
#       "comfort_and_convenience": "Manual AC, tilt steering, all power windows, driver side auto up/down with anti-pinch, central locking, rear defogger, 60:40 split rear seat, MID with segment display.",
#       "technology_and_performance": "1.2L K-Series Dual Jet Dual VVT engine, 1197 cc, max power 89.7 PS @ 6000 rpm, torque 113 Nm @ 4400 rpm, 5MT, fuel efficiency 22.35 kmpl, fuel tank 37L, MacPherson Strut front, Torsion Beam rear suspension, disc front & drum rear brakes.",
#       "infotainment_and_connectivity": "Basic SmartPlay Studio with 2 speakers, Android Auto & Apple CarPlay (wired), USB & Bluetooth connectivity, gear shift indicator."
#     },
#     {
#       "price": 820000.0,
#       "fuel_type": "Petrol / CNG",
#       "product_id": "baleno-delta-mt-amt-cng",
#       "brand_name": "Maruti Suzuki NEXA",
#       "model_name": "Baleno",
#       "variant_name": "Delta MT/AMT, CNG MT",
#       "product_name": "Baleno Delta",
#       "general": "Premium hatchback, available in petrol (MT/AMT) and CNG (MT), 5-seater, warranty up to 2 years.",
#       "branding_and_looks": "Steel wheels with covers, body-coloured ORVMs with indicators, NEXWave grille, halogen projector headlamps, rear spoiler, LED DRLs.",
#       "safety_and_environment": "Dual airbags, ABS with EBD, ESP with Hill Hold, seatbelt reminders, rear parking sensors, ISOFIX anchors, high-speed alert system, CNG with stainless steel pipes and microswitch safety.",
#       "comfort_and_convenience": "Manual AC with heater, electrically adjustable ORVMs, steering-mounted audio controls, rear fast charging USB (Type A & C), power windows, central locking, height-adjustable driver seat.",
#       "technology_and_performance": "1.2L petrol engine: 89.7 PS & 113 Nm; CNG: 77.5 PS & 98.5 Nm, 5MT/5AMT, mileage 22.94 kmpl (AMT petrol), 30.61 km/kg (CNG), fuel tank: Petrol 37L, CNG 55L (water equivalent).",
#       "infotainment_and_connectivity": "SmartPlay Pro with 17.78 cm touchscreen, 4 speakers, Android Auto & Apple CarPlay, OTA updates, voice assistant, Bluetooth & USB."
#     },
#     {
#       "price": 950000.0,
#       "fuel_type": "Petrol / CNG",
#       "product_id": "baleno-zeta-mt-amt-cng",
#       "brand_name": "Maruti Suzuki NEXA",
#       "model_name": "Baleno",
#       "variant_name": "Zeta MT/AMT, CNG MT",
#       "product_name": "Baleno Zeta",
#       "general": "Premium hatchback, higher variant with advanced features, available in petrol MT/AMT and CNG MT, warranty up to 2 years.",
#       "branding_and_looks": "Alloy wheels (painted), LED projector headlamps, DRLs, NEXWave grille with chrome, LED fog lamps with garnish, chrome door handles, back door chrome garnish, 195/55 R16 tyres.",
#       "safety_and_environment": "ESP with Hill Hold, 4 airbags, rear camera, 3-point seatbelts for all occupants, ISOFIX, Suzuki TECT body, BS-VI engine compliance.",
#       "comfort_and_convenience": "Auto climate control, rear AC vents, sliding front armrest, height-adjustable driver seat, push start/stop button, cruise control, rear wiper with washer, rear defogger, tilt & telescopic steering.",
#       "technology_and_performance": "1.2L petrol engine: 89.7 PS & 113 Nm, AMT with ISS, CNG: 77.5 PS & 98.5 Nm, fuel efficiency 22.35–22.94 kmpl (petrol), 30.61 km/kg (CNG), suspension same as lower trims, kerb weight ~955 kg (petrol), 1035 kg (CNG).",
#       "infotainment_and_connectivity": "SmartPlay Pro+ with 22.86 cm HD display, ARKAMYS Surround Sense audio with 6 speakers + 2 tweeters, wireless Android Auto & Apple CarPlay, 360° camera, head-up display, voice assistant, OTA updates."
#     },
#     {
#       "price": 1050000.0,
#       "fuel_type": "Petrol",
#       "product_id": "baleno-alpha-mt-amt-petrol",
#       "brand_name": "Maruti Suzuki",
#       "model_name": "Baleno",
#       "variant_name": "Alpha MT/AMT",
#       "product_name": "Baleno Alpha",
#       "general": "Top-end premium hatchback variant, petrol MT/AMT, 5-seater, warranty up to 2 years.",
#       "branding_and_looks": "Precision cut alloy wheels, LED projector headlamps, NEXTre’ LED DRLs, NEXWave grille with chrome, chrome garnish, LED fog lamps, shark fin antenna, body-coloured bumpers.",
#       "safety_and_environment": "6 airbags (front, side, curtain), ESP with Hill Hold, Suzuki Connect safety alerts, reverse parking camera, ISOFIX, TPMS, pedestrian protection compliance.",
#       "comfort_and_convenience": "Auto dimming IRVM, auto folding ORVMs, auto climate control, cruise control, rear AC vents, sliding armrest, push start/stop, leather-wrapped steering, rear fast charging USB ports.",
#       "technology_and_performance": "1.2L K-Series engine with ISS, 1197 cc, 89.7 PS @ 6000 rpm, 113 Nm torque @ 4400 rpm, 5MT/5AMT, mileage ~22.35–22.94 kmpl, 37L fuel tank, disc front brakes, torsion beam rear, kerb weight ~960 kg.",
#       "infotainment_and_connectivity": "SmartPlay Pro+ 9-inch HD screen, ARKAMYS Surround Sense, wireless Android Auto & Apple CarPlay, head-up display, 360° view camera, Suzuki Connect with Alexa & smartwatch compatibility, 6 speakers + 2 tweeters."
#     }
#             ],
#             'invicto.json': [
#                 {
#       "price": 1000000.0,
#       "fuel_type": "Petrol / Hybrid",
#       "product_id": "invicto-zeta+-petrol-hybrid",
#       "brand_name": "Maruti Suzuki NEXA",
#       "model_name": "Invicto",
#       "variant_name": "Zeta+",
#       "product_name": "Invicto Zeta+",
#       "general": "7/8-seater premium MPV with e-CVT transmission, Intelligent Electric Hybrid system, warranty up to 2 years, 2WD drive type.",
#       "branding_and_looks": "Length 4755 mm, Width 1845 mm, Height 1795 mm, Wheelbase 2850 mm, alloy wheels 215/60 R17, panoramic sunroof with ambient lighting, bold NEXWave grille, NEXTre DRLs, LED tail lamps.",
#       "safety_and_environment": "Dual airbags, ABS with EBD, 6 airbags, Vehicle Stability Control with Hill Start Assist, ISOFIX, rear parking sensors, BS-VI compliant, Suzuki Connect with eCall emergency support.",
#       "comfort_and_convenience": "One-touch powered tailgate, ventilated front seats, multi-zone climate control (front and rear), captain seats in 2nd row (7-seater) or 60:40 split seats (8-seater), keyless entry, electric ORVMs, smart key with push start.",
#       "technology_and_performance": "1987 cc petrol engine, max power 112 kW @ 6000 rpm, torque 188 Nm @ 4400-5200 rpm, hybrid system max power 137 kW, multiple drive modes (Eco/Normal/Power), EV mode, 52L fuel tank, Macpherson Strut front suspension, torsion beam rear, ventilated disc brakes front, solid disc rear.",
#       "infotainment_and_connectivity": "20.32 cm SmartPlay Magnum touchscreen, Apple CarPlay & Android Auto, digital + analogue MID with 7-inch TFT display, gear shift indicator, TPMS, low fuel and seatbelt alerts, steering-mounted controls, Suzuki Connect remote operations."
#     },
#     {
#       "price": 1200000.0,
#       "fuel_type": "Petrol / Hybrid",
#       "product_id": "invicto-alpha+-petrol-hybrid",
#       "brand_name": "Maruti Suzuki",
#       "model_name": "Invicto",
#       "variant_name": "Alpha+",
#       "product_name": "Invicto Alpha+",
#       "general": "7-seater luxury MPV with e-CVT transmission, Intelligent Electric Hybrid, advanced comfort and safety features, warranty up to 2 years.",
#       "branding_and_looks": "Length 4755 mm, Width 1850 mm, Height 1790 mm, Wheelbase 2850 mm, precision cut 17-inch alloys, premium interiors with champagne gold accents, leatherette seats, panoramic sunroof, ambient roof lighting.",
#       "safety_and_environment": "6 airbags, ABS with EBD, VSC with Hill Start Assist, electronic parking brake with auto hold, front & rear disc brakes, 360-view camera with dynamic guide lines, ISOFIX, TPMS, Suzuki Connect with emergency call.",
#       "comfort_and_convenience": "Ventilated seats, 8-way powered driver seat with memory function, captain seats with side tables, rear climate control (2nd zone), powered tailgate, retractable sunshades, walk-in slide and recline seats, cruise control with paddle shifters.",
#       "technology_and_performance": "1987 cc petrol hybrid engine, max system power 186.2 PS, AC synchronous motor with 83.73 kW power and 206 Nm torque, ECO/Normal/Power drive modes, EV mode, 52L fuel tank, front Macpherson Strut, rear torsion beam, ventilated + solid disc brakes.",
#       "infotainment_and_connectivity": "25.65 cm SmartPlay Magnum+ touchscreen, wireless Apple CarPlay, Android Auto, 6 speakers, digital MID themes based on drive mode, tyre pressure monitoring system, door/window/seatbelt alerts, Alexa & smartwatch connectivity, Suzuki Connect full remote features."
#     }
#             ]
#         }
        
#         return hardcoded_data_map.get(filename)

#     def _debug_file_content(self, file_path: str) -> None:
#         """Helper method to debug file content"""
#         absolute_path = os.path.abspath(file_path)
#         print(f"\n=== DEBUG FILE: {absolute_path} ===")
#         print(f"Exists: {os.path.exists(absolute_path)}")
#         if os.path.exists(absolute_path):
#             print(f"Is file: {os.path.isfile(absolute_path)}")
#             print(f"Size: {os.path.getsize(absolute_path)} bytes")
#             try:
#                 with open(absolute_path, 'r', encoding='utf-8') as f:
#                     content = f.read()
#                     print(f"Content (first 200 chars): {repr(content[:200])}")
#             except Exception as e:
#                 print(f"Error reading file: {e}")
#         print("=== END DEBUG ===\n")