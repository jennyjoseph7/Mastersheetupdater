
import os,sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from gryd_worker import gryd
gryd.SERVICE = os.environ.get("AUTOBOT_CONVERSATION_SERVICE_NAME","autocrm-conversation")
import json
from autocrm_db_helper import get_pg_connector
from ai_service import ai_service_app

mlogger = gryd.hp.get_logger(__name__)

def yield_primary_prompt(*args, **kwargs):
    mlogger.info("yield_primary_prompt called with data \n {} \n\n ---------------".format(kwargs))
    request_data = kwargs.get("request_data")

    ###TODO check prompt template model to find the correct prompt for this user and campaign
    yield {"prompt":setup_primary_prompt(*args, **kwargs)}

def specific_prompt(*args, **kwargs):
    ###TODO find prompt based on filters provided
    yield {"prompt":"Hello World get_specific_prompt"}



def execute_orchestrator(*args, **kwargs):
    pass


def run_prompt_sync(user_query="",system_prompt="",history="", messages=[], **kwargs):
    request_data = kwargs.get("request_data")
    resp = ""
    if messages:
        resp = ai_service_app.get_llm_response(messages=messages,audit_params={"session_id":request_data.get("session_id")},**{"model_identifier":request_data.get("temporary_data",{ }).get("model_identifier","gcp-gemini-2.5-flash-lite")})
    else:
        resp = ai_service_app.get_llm_response(user_query=user_query,system_prompt=system_prompt,history=history,audit_params={"session_id":kwargs.get("session_id")},**{"model_identifier":request_data.get("temporary_data",{}).get("model_identifier","gcp-gemini-2.5-flash-lite")})
    
    ###TODO write valid json detector and retry if not valid
    return resp

def get_document_data(*args, **kwargs):
    return """
    Maruti Ciaz Data -
    Maruti Suzuki Ciaz - Complete Information
1. General Overview
The Maruti Suzuki Ciaz is a premium mid-size sedan offering a perfect balance of elegance, technology, and efficiency. It boasts spacious interiors, a refined design, and a smooth driving experience.

2. Variant-wise Details
Sigma: Base variant with essential features
Delta: Mid-variant with additional tech and convenience features
Zeta: Higher-end variant with premium offerings
Alpha: Top variant with all advanced features
3. Dimensions and Capacity
Length: 4490 mm
Width: 1730 mm
Height: 1485 mm
Wheelbase: 2650 mm
Boot Space: 510 L
Seating Capacity: 5
4. Engine and Performance
Petrol Engine

Engine: 1.5L K15 Smart Hybrid Petrol
Power: 104.6 PS @ 6000 rpm
Torque: 138 Nm @ 4400 rpm
Transmission: 5-speed MT / 4-speed AT
Fuel Efficiency: ~20.65 km/l (MT) / ~20.04 km/l (AT)
5. Safety Features
Dual Front Airbags
ABS with EBD
Electronic Stability Program (ESP)
Hill Hold Assist
ISOFIX Child Seat Anchors
Reverse Parking Sensors and Camera
Speed Alert System
6. Comfort and Convenience
Automatic Climate Control
Rear AC Vents
Cruise Control
Keyless Entry with Push Start-Stop Button
Height Adjustable Driver Seat
Rear Sunshade
Footwell Lamps
7. Technology and Connectivity
7-inch SmartPlay Infotainment System
Android Auto & Apple CarPlay
Voice Command System
Steering-mounted Audio and Calling Controls
Smart Hybrid Technology (Idle Start-Stop, Torque Assist, Brake Energy Regeneration)
8. Exterior Features
LED Projector Headlamps with DRLs
Chrome Accents on Front Grille
16-inch Alloy Wheels (Precision Cut in Alpha Variant)
LED Rear Combination Lamps
Body-Colored ORVMs with Turn Indicators
9. Interior Features
Dual-Tone Premium Interiors
Leather-Wrapped Steering Wheel (Alpha Variant)
Rear Center Armrest with Cup Holders
Adjustable Rear Headrests
Wooden Finish on Dashboard (with Satin Chrome Finish)
10. Technical Specifications
Suspension: MacPherson Strut (Front), Torsion Beam (Rear)
Brakes: Disc (Front), Drum (Rear)
Ground Clearance: ~170 mm
11. Eco-Friendly Features
BS6-Compliant Engine
Smart Hybrid Technology for Reduced Emissions

Maruti Invicto Document

Maruti Suzuki Invicto - Complete Overview
1. General Overview
The Maruti Suzuki Invicto is a premium MPV designed for sophistication and practicality. It combines luxury, cutting-edge technology, and a spacious cabin to provide an unparalleled driving experience. Built on a robust platform, it ensures top-tier safety and comfort for every journey.

2. Variants
The Invicto is available in the following variants:

Zeta+ 2.0L Strong Hybrid (7-Seater, 8-Seater)
Alpha+ 2.0L Strong Hybrid (7-Seater)
3. Dimensions and Capacity
Length: 4755 mm
Width: 1850 mm
Height: 1790 mm
Wheelbase: 2850 mm
Boot Space: 239 L (Expandable)
Seating Capacity: 7 / 8
Turning Radius: 5.4 m
4. Engine and Performance
2.0L Strong Hybrid Engine

Power: 112 kW @ 6000 rpm (Engine) + 113 kW (Motor Output)
Torque: 188 Nm @ 4400-5200 rpm (Engine) + 206 Nm (Motor Output)
Fuel Efficiency: 23.24 km/l
5. Safety Features
6 Airbags (Front, Side, Curtain)
Electronic Stability Program (ESP)
Hill-Hold Assist
Rear Parking Sensors & Camera
ISOFIX Child Seat Anchors
3-Point ELR Seat Belts for All Seats
ABS with EBD & Brake Assist
Suzuki TECT Body for enhanced safety
6. Comfort and Convenience
Ventilated Front Seats
Powered Ottoman Seats (Alpha+ Only)
Panoramic Sunroof
Tri-Zone Automatic Climate Control
Powered Tailgate & Sliding Doors
Adjustable Second-Row Captain Seats
Wireless Charging & Multiple USB Ports
7. Technology and Connectivity
10.1-inch SmartPlay Pro+ Infotainment System (Wireless Apple CarPlay & Android Auto)
360-degree Camera View
Heads-Up Display
Digital Driver Display
Connected Car Technology (Suzuki Connect)
8. Exterior Features
LED Headlamps & DRLs
Signature NEXA Grille with Chrome Accents
Dual-Tone Alloy Wheels
Auto-Folding ORVMs
9. Interior Features
Premium Quilted Leather Upholstery
Wooden & Metal Finish Dashboard Accents
Adjustable Ambient Lighting
Leather-Wrapped Steering Wheel
10. Technical Specifications
Transmission Options: e-CVT
Brakes: Disc (Front & Rear)
Suspension: MacPherson Strut (Front), Torsion Beam (Rear)
Tyres: 215/60 R17
11. Eco-Friendly Features
Strong Hybrid Technology (Lithium-Ion Battery, Regenerative Braking, EV Mode)
Idle Start Stop (ISS) Technology
12. Color Options
Single Tone: NEXA Blue, Stellar Bronze, Mystic White, Majestic Silver, Midnight Black


Maruti WagonR Document
Maruti Suzuki WagonR: Comprehensive Details
1. General Overview
The WagonR is a tall-boy hatchback offering a spacious and practical design for urban driving. It is designed with bold styling, a floating roof, and dual-tone exterior options to match modern aesthetics. Available in Petrol and CNG variants to cater to diverse driving needs.

2. Variants and Pricing
Variants Available

LXi: Entry-level variant with essential features.
VXi: Mid-range variant with additional comfort and convenience.
ZXi: Enhanced features for a better driving experience.
ZXi+: Top-end variant with premium offerings.
Available in Manual Transmission (MT) and Auto Gear Shift (AGS) options.

3. Dimensions and Capacity
Length: 3655 mm
Width: 1620 mm
Height: 1675 mm
Wheelbase: 2435 mm
Boot Space:
Petrol: 341 liters
CNG: 180 liters (water equivalent)
Seating Capacity: 5 persons
4. Engine and Performance
Engine Options

1.0L K-Series Dual Jet, Dual VVT Engine
1.2L K-Series Engine
Displacement

998 cc / 1197 cc
Power Output

1.0L: 49 kW (66.62 PS) @ 5500 rpm
1.2L: 65.5 kW (88.5 PS) @ 6000 rpm
Torque

1.0L: 89 Nm @ 3500 rpm
1.2L: 113 Nm @ 4200 rpm
Fuel Efficiency

Petrol: Up to 25.19 km/l
CNG: 33.48 km/kg
Transmission

5-speed Manual and AGS
5. Safety Features
Dual airbags (driver and passenger)
ABS with EBD
Electronic Stability Program (ESP) for improved control
Hill Hold Assist (AGS variants)
Reverse Parking Assist Sensors
Speed-sensitive auto door lock
Seatbelt pre-tensioners with force limiters
HEARTECT platform for enhanced crash safety
6. Comfort and Convenience
Interior Features

Dual-tone interiors with premium upholstery
Tilt steering adjustment
60:40 split rear seats for added flexibility
Convenience Features

Engine push start-stop button (ZXi+)
Steering-mounted audio and phone controls
Power windows (front and rear)
Electrically adjustable and foldable ORVMs with turn indicators
7. Technology and Connectivity
Infotainment System

17.78 cm SmartPlay Studio touchscreen with Android Auto and Apple CarPlay
Smartphone navigation integration
Four-speaker audio system
Smart Features

Idle Start-Stop technology for fuel efficiency
Remote keyless entry
Alerts for speed, door open, and parking assistance
8. Exterior Features
Design Elements

Floating roof design
Dual-tone color options with black roof
Stylish alloy wheels
LED DRLs and projector headlamps
Bold front grille with chrome accents

End Of Document Data
"""

def get_who_are_you(*args, **kwargs):
    return "You are a digital sales assistant bot."   

def get_who_you_represent(*args, **kwargs):
    session_data = kwargs.get("session_data",{})
    campaign_data = kwargs.get("campaign_data",{})
    dealership_name = "Autobot"
    if not campaign_data and session_data.get("campaign_id","inbound") and session_data.get("campaign_id","inbound") != "inbound" and session_data.get("campaign_model","inbound"):
        with get_pg_connector() as pg:
            campaign_data = pg.get(session_data.get("campaign_model","inbound"),f"{session_data.get('campaign_model')}_id",session_data.get("campaign_id","inbound")) 
    if not campaign_data:
        return "You represent Autobot and all dealers listed with the platform."
    dealership_name = campaign_data.get("dealer_name")
    dealer_type = ""
    shop_details = ""
    if campaign_data.get("campaign_type") == "pre-sales":
        dealer_type = "showroom"
        shop_details = campaign_data.get("showroom_name","")
    if campaign_data.get("campaign_type") == "post-sales":
        dealer_type = "workshop"
        shop_details = campaign_data.get("workshop_name","")
    
    dealer_details = "They have a {dealer_type} called {shop_details}.".format(dealer_type=dealer_type,shop_details=shop_details) if shop_details else "They have a {dealer_type}".format(dealer_type=dealer_type)
    return "You represent {dealership_name}.{dealer_details}".format(dealership_name=dealership_name,dealer_details=dealer_details)   

def get_user_info(*args, **kwargs):
    user_data = kwargs.get("user_data")

    return "The following is all the information we currently have about the customer: \n{}\n\n".format(user_data)

def get_purpose_and_steps(*args, **kwargs):
    session_data_cache_data = kwargs.get("session_data_cache",{})
    campaign_data = session_data_cache_data.get("campaign_data",{})
    user_data = session_data_cache_data.get("user_data")
    campaign_type = campaign_data.get("campaign_type","inbound")

    purpose_dict = {
        "test_drive" : ["- Full Name \n- Interested Model \n- Dealer (help match based on pincode provided by customer)\n- Date & Time "],
        "service" : ["- Full Name \n- Car Model \n- Dealer (help match based on pincode provided by customer)\n- Date & Time \n- Service Type"]
        }

    ###TODO create a way to detect the flow to push
    flow = "service" if campaign_type == "post-sales" else "either test drive at the showroom or at home"

    if flow == "service":
        steps = ["- Full Name \n- Car Model \n- Date & Time \n- Service Type"]
    else:
        steps = ["- Full Name \n- Interested Model\n- Date & Time "]
    if campaign_type == "inbound":
        return "Your overall purpose is to help the customer with the information about cars that they desire while also trying to gather as much information about the user like their Name, approximate location, features of a car they like or require, their budget if applicable. Do not be pushy."
    return f"The overall purpose of your conversation with the user is to help them book {flow}. Here are the details you should gather from the user when booking {flow}  :- \n{steps}\n\n.You should help answer any and all questions that the customer asks about cars that are related to the dealer. You should always try to move the user to your original purpose but do not be pushy."

def get_example_states_and_solutions(*args, **kwargs):
    examples = [
        "If the customer shows displeasure in the dealer or their services or cars, be polite and if they are reasonable, you should ask them for why they feel the way they do. if they provide the details of the complaint, you can then try and urge them to go ahead with your purpose.",
        ""
    ]
    return ", ".join(examples)


def get_rules(*args, **kwargs):
    return "Always be polite, be helpful, if the customer is rude, avoid confrontation, do not be pushy."

def get_tone_and_style(*args, **kwargs):
    return "be descriptive in your explanations, give examples and explanations when asking the user to select any options. try to acheive your goal but dont force the customer."

def get_output_format(*args, **kwargs):
    return "" if "voice" in kwargs.get("request_data",{}).get("response_channel","text") else "text"


def setup_primary_prompt(*args, **kwargs):
    '''
    Prompt sections -
    - Who are you
    - Who/what do you represent
    - Who is the customer
    - What is your purpose (flow and steps)
    - Possible states of the conversation and how to handle
    - Rules
    - Tone and style
    - Documents
    - output format

    '''
    
    
    
    session_data_cache_data = kwargs.get("session_data_cache",{}).get("data",{})
    campaign_data = session_data_cache_data.get("campaign_data")
    user_data = session_data_cache_data.get("user_data")
    campaign_type = campaign_data.get("campaign_type")
    campaign_name = campaign_data.get("campaign_name")
    campaign_objective = campaign_data.get("campaign_objective")
    dealer_name = campaign_data.get("workshop_name")
    dealer_description = "{dealer_name} is a dealer who sells cars from their showrooms".format(dealer_name=dealer_name) if campaign_type == "pre-sales" else "{dealer_name} has a service center.".format(dealer_name=dealer_name)
    dealership_id = campaign_data.get("workshop_id")
    showroom_workshop_desc = ""
    if not campaign_data:
        campaign_name = "inbound"
        campaign_objective = "inbound"
        campaign_type = "inbound"
        campaign_data = {"campaign_name":campaign_name,"campaign_objective":campaign_objective,"campaign_type":campaign_type}

    
    with get_pg_connector() as pg:
        model_fetch = "showroom" if campaign_type == "pre-sales" else "workshop"
        showroom = pg.get(model_fetch,f"{model_fetch}_id",dealership_id)
    if showroom:
        showroom_workshop_desc = "The following are the {showroom_workshop} of {dealer_name} :{showrooms}".format(showroom_workshop=model_fetch,dealer_name=dealer_name,showrooms = json.dumps(showroom))



    


    purpose_and_steps = get_purpose_and_steps(*args,**{"session_data_cache_data":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data})
    doc_data = get_document_data(*args,**{"session_data_cache_data":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data})
    who_are_you =  get_who_are_you(*args,**{"session_data_cache_data":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data})
    who_you_represent = get_who_you_represent(*args,**{"session_data_cache_data":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data})
    who_is_the_customer = get_user_info(*args,**{"session_data_cache_data":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data})
    possible_states_and_solutions = get_example_states_and_solutions(*args,**{"session_data_cache_data":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data})
    rules = get_rules(*args,**{"session_data_cache_data":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data})
    tone_and_style = get_tone_and_style(*args,**{"session_data_cache_data":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data})
    output_format = get_output_format(*args,**{"session_data_cache_data":session_data_cache_data,"campaign_data":campaign_data,"user_data":user_data})


    primary_prompt = f"""
    Who you are -
    {who_are_you}
    Who you represent -
    {who_you_represent}
    Who is the customer -
    {who_is_the_customer}
    The purpose of this conversation -
    {purpose_and_steps}
    Possible states of the conversation and how to handle -
    {possible_states_and_solutions}
    Rules -
    {rules}
    Tone and style -
    {tone_and_style}
    Dealer description -
    {showroom_workshop_desc}
    Documents Data -
    {doc_data}
    Output Format -
    {output_format}
    """
    return primary_prompt


def check_if_visited(*args, **kwargs):
    messages = kwargs.get("messages")
    session_id = kwargs.get("session_id")
    if not messages and not session_id:
        return
    with get_pg_connector() as pg:
        session = pg.get("session","session_id",session_id)
        if not session:
            return
        
        campaign_model = session.get("campaign_model")
        campaign_id = session.get("campaign_id")
        campaign_data = pg.get(campaign_model,f"{campaign_model}_id",campaign_id)

        showroom_workshop = "showroom" if session.get("campaign_type") == "pre_sales" else "workshop"
        prompt = """
        You are a helpful agent that detects if a customer has visited the {showroom_workshop}.
        The customer was expected to visit my {showroom_workshop}.

        The following is the transcript of my discussion with the user.

        Your only task is to detect if the user said anything that implies they already visited the {showroom_workshop}.

        {messages}

        Your response should be only 'yes' or 'no'.
        """.format(
            showroom_workshop = showroom_workshop,
            messages = json.dumps(messages)
        )
        
        xx = run_prompt_sync(user_query="",system_prompt=prompt,history=[], messages=[], **kwargs)
        mlogger.info("xx == {}".format(xx))
        pass