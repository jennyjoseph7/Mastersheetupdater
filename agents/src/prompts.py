

def index_prompt(user_query):
    return f"""
Your role is to analyze the user's input about a car and assign a numerical score 
(between -1.0 and 1.0) for each relevant attribute in the vector model.

Scoring Scale:
-1.0 → Very poor / negative sentiment / does not meet expectation  
 0.0 → Neutral / not enough information provided  
+1.0 → Excellent / very strong / meets or exceeds expectation  

Intermediate values (e.g., 0.3, 0.7, -0.5) should reflect partial strength or weakness.







Guidelines:
1. Extract specific details (e.g., '400 bhp', '1998 cc', '10-inch touchscreen') 
   and map them to the corresponding attributes.
2. Score related attributes consistently:
   - High power usually implies good engine performance.  
   - A premium interior often correlates with comfort & convenience.  
   - Eco-friendly features may align with fuel efficiency.  
3. If an attribute is not mentioned explicitly, infer from context if possible, 
   otherwise assign 0.0.
4. Negative mentions (e.g., 'poor mileage', 'uncomfortable seats') should lower 
   the corresponding scores.
5. Use proportional scoring when possible:
   - Example: Boot space of 208 Litres in a sports car → high score, 
     but in a family SUV → medium/low score.  
   - Efficiency like '453 km per charge' for EVs → high score.  
6. Consider dependencies:
   - Engine specs affect both `engine` and `engine_performance`.  
   - Safety features may also reflect on comfort & convenience.  
   - Fuel capacity links with fuel efficiency and vehicle type.  
   - Exterior design may connect with aerodynamics (dimension + performance).  
7. Always return a dictionary-like JSON with attribute: score pairs 
   so downstream systems can parse it.

User Input:
{user_query}
"""


def prompts_to_fix_llm(data, user_input):
    system_prompt = (
        "You are a precise matching assistant. "
        "Your task is to find the single closest match in the given dataset to the user input. "
        "You must ALWAYS return exactly one key from the dataset — never combine or merge multiple entries. "
        "Return the key exactly as it appears in the dataset (preserve original case, spacing, punctuation, and symbols). "
        "Do NOT reformat, modify, or partially join dataset values. "
        "If no perfect match is found, return the single closest key only. "
        "Examples:\n"
        "- Dataset has ['Volvo-1', 'Toyota', 'Ford Focus'] and input is 'voluo' → Return 'Volvo-1'\n"
        "- Dataset has ['Mahindra & Mahindra', 'Scorpio', 'S7 120 2WD 7 STR'] and input is 'mahindra' → Return 'Mahindra & Mahindra'\n"
        "Never output multiple items or merge values together."
        "Never return key always return the corrected value"
    )

    user_prompt = f"""Dataset: {data}

User input: "{user_input}"

Return exactly one dataset key that best matches the intent. 
Do not merge or combine multiple dataset items. 
Return only one key, exactly as written in the dataset.
"""
    return system_prompt, user_prompt



def prompt_vector_gen(user_query: str):
    system_prompt = (
        "You are a highly intelligent assistant trained to interpret user preferences and car details "
        "from natural language queries.\n\n"
        "Your task is to infer a contextual score (between -1.0 and 1.0) for each of the following traits:\n\n"
        "1. power: Rate power output preference (e.g., '400 bhp').\n"
        "2. engine: Rate engine specifications (e.g., '1998 cc, 4 Cylinders Inline').\n"
        "3. torque: Rate torque delivery (e.g., '430 Nm @ 3000-6500 rpm').\n"
        "4. dimension: Rate vehicle dimensions (length, width, height).\n"
        "5. wheelbase: Rate wheelbase importance (e.g., '2575 mm').\n"
        "6. boot_space: Rate boot space practicality (e.g., '208 Litres').\n"
        "7. technology: Rate onboard technology (e.g., '10-inch touchscreen, CarPlay, Android Auto').\n"
        "8. eco_friendly: Rate eco-friendliness (e.g., 'Regenerative Braking, Idle Start-Stop').\n"
        "9. fuel_capacity: Rate fuel tank capacity (e.g., '52 Litres').\n"
        "10. safety_feature: Rate safety features (e.g., 'ABS, Driver Assistance, Crash Protection').\n"
        "11. exterior_feature: Rate exterior aesthetics and design (e.g., 'Aerodynamic profile, forged wheels').\n"
        "12. interior_feature: Rate interior quality and comfort (e.g., 'Premium materials, infotainment').\n"
        "13. engine_and_performance: Rate overall performance package (e.g., 'Turbo engine, 0-62 mph in 4s').\n"
        "14. comfort_and_convenience: Rate comfort and convenience (e.g., 'Suspension tuning, amenities').\n"
        "15. fuel_efficiency: Rate efficiency (e.g., '453 km per charge').\n"
        "16. price: Rate price-to-value ratio (affordability vs luxury).\n\n"
        "Scoring Guidelines:\n"
        "- Traits not mentioned explicitly but implied by context should still be scored.\n"
        "- A score near **1.0** = strongly values trait.\n"
        "- A score near **-1.0** = strongly dislikes trait.\n"
        "- A score near **0.0** = neutral, irrelevant, or insufficient information.\n"
        "- Ensure all attributes are included in the output even if 0.0.\n"
        "- Interpret subtle intent:\n"
        "   • 'Premium experience' → higher scores for technology, interior, safety, exterior, engine_performance, comfort.\n"
        "   • 'Practical family car' → higher scores for boot_space, safety, comfort_convenience, fuel_efficiency.\n"
        "   • 'Sports performance' → higher scores for power, engine, torque, dimension, wheelbase, engine_performance.\n"
        "   • 'Eco-conscious' → higher scores for eco_friendly, fuel_efficiency, technology.\n"
        "- Use proportional scoring:\n"
        "   • Small boot space in a sports car may still get a decent score, but low in an SUV context.\n"
        "   • High bhp implies strong power and performance, but may reduce eco_friendly score.\n\n"
        "Output Requirements:\n"
        "- Return a JSON-like dictionary with all attributes as keys and float values between -1.0 and 1.0.\n"
        "- No explanations, only the dictionary output.\n"
    )

    user_prompt = f"User Query:\n{user_query}"

    return system_prompt, user_prompt








def car_traits_prompt(user_query: str):
    system_prompt = (
        "You are a highly intelligent assistant trained to analyze car specifications "
        "and user preferences. Your task is to assign a score between 0 and 1 for each "
        "trait below, based on the user’s query. Use the examples and guidelines provided.\n\n"
        "Traits and Scoring Instructions:\n\n"
        "1. power: Rate the Power output of the car from -1 to 1. "
        "Example: '400 bhp'. Higher values = higher horsepower and performance potential.\n\n"

        "2. engine: Rate the Engine specifications from -1 to 1. "
        "Example: '1998 cc, 4 Cylinders Inline, 4 Valves/Cylinder'. "
        "Factors include displacement, arrangement, refinement.\n\n"

        "3. torque: Rate Torque delivery from -1 to 1. "
        "Example: '430 Nm @ 3000-6500 rpm'. Higher = better acceleration & pulling power.\n\n"

        "4. dimension: Rate car Dimensions from -1 to 1. "
        "Example: 'Length 4412 mm, Width 1895 mm, Height 1225 mm'. "
        "Affects space, aerodynamics, and presence.\n\n"

        "5. wheelbase: Rate Wheelbase length from -1 to 1. "
        "Example: '2575 mm'. Longer = better stability and cabin space.\n\n"

        "6. boot_space: Rate Boot Space from -1 to 1. "
        "Example: '208 Litres'. Reflects luggage practicality.\n\n"

        "7. technology: Rate onboard Technology & Infotainment from -1 to 1. "
        "Example: '10-inch touchscreen, Apple CarPlay, Android Auto'. "
        "Higher = more modern in-car tech.\n\n"

        "8. eco_friendly: Rate Eco-Friendliness from -1 to 1. "
        "Example: 'Regenerative Braking, Idle Start-Stop'. "
        "Higher = greener, more sustainable.\n\n"

        "9. fuel_capacity: Rate Fuel Tank Capacity from -1 to 1. "
        "Example: '52 Litres'. Larger = more range but more weight.\n\n"

        "10. safety_feature: Rate Safety from -1 to 1. "
        "Example: 'ABS, Driver Assistance, Crash Protection'.\n\n"

        "11. exterior_feature: Rate Exterior design/features from -1 to 1. "
        "Example: 'Aerodynamic profile, 20-inch forged wheels'.\n\n"

        "12. interior_feature: Rate Interior quality/features from -1 to 1. "
        "Example: 'Premium materials, ergonomic layout'.\n\n"

        "13. engine_and_performance: Rate Engine & Performance package from -1 to 1. "
        "Example: '2.0L turbo, 400 hp, 0-62 mph in 4s'.\n\n"

        "14. comfort_and_convenience: Rate Comfort & Convenience from -1 to 1. "
        "Example: 'Sports suspension, Launch control, amenities'.\n\n"

        "15. fuel_efficiency: Rate Fuel Efficiency from -1 to 1. "
        "Example: '453 km per charge' or '20 km/l'.\n\n"

        "16. price: Rate Price value from -1 to 1. "
        "Higher = affordable relative to features, lower = luxury pricing.\n\n"

        "Return the output as a JSON object with keys as traits and values as floats "
        "between 0 and 1.\n\n"
        "Example output:\n"
        "{\n"
        '  "power": 0.9,\n'
        '  "engine": 0.85,\n'
        '  "torque": 0.88,\n'
        '  "safety": 0.95,\n'
        '  "technology": 0.92,\n'
        '  "fuel_efficiency": 0.6,\n'
        '  "price": 0.7\n'
        "}"
    )

    user_prompt = f"User query: {user_query}\n\nPlease rate each trait from -1 to 1."

    return system_prompt, user_prompt



def mergerFreeTextPrompt(user_text: str):
    system_prompt = """
    You are a precise and intelligent assistant that extracts structured information from unstructured user text related to car buying preferences and user background.

    ## 🎯 OBJECTIVE:
    You must analyze the user's sentence and extract:
    1. **user_profile** → general, lifestyle, background, or behavioral information.
    2. **user_preference** → structured filters directly related to car attributes.

    ## ⚙️ CLASSIFICATION RULE:
    Only the following intents are valid for **user_preference**:
    ["brand_name", "product_name","brand_name", "model_name", "variant_name", "transmission", "seating", "price_range", "budget", "fuel_type", "vehicle_type", "color"]

    ➤ Anything outside this list (e.g., "comfort", "safety", "health", "family", "student", "back pain", "long drive", etc.) should go under **user_profile**.

    ## 🧠 DEFINITIONS:
    - **user_preference** = Filters that can be used in search or recommendation systems.
      Examples:
        - "I like Mahindra" → brand_name
        - "7 seater" → seating
        - "petrol" → fuel_type
        - "SUV" → vehicle_type
        - "black" → color
        - "Z2 Diesel MT 7 STR (ESP)" → variant_name
        - "Mahindra" → brand_name
        - "manual transmission" → transmission
        - "5 seater" → seating
        - "Scorpio" → product_name
        - "under 10 lakh" → price_range
    
    - **user_profile** = Contextual or personal insights about the user.
      Examples:
        - "I’m a student"
        - "I have back pain so I need comfortable seats"
        - "My family goes on long trips often"
        - "I’ll exchange my old car to finance it"
    
    ## 🧩 RESPONSE FORMAT:
    Always return in **strict JSON format only**, with this structure:
    {
      "user_profile": [
          {"intent": "...","statement": "...", "answer": ["..."]}
      ],
      "user_preference": [
          {"intent": "...", "statement": "...", "answer": ["..."]}
      ]
    }

    - If no data is found, return an empty array for that section.
    - Each entry in both sections must include `"statement"` → the original or rephrased user statement or intent behind the extracted data.
    - Avoid any explanation outside of JSON.
    - All intent names in user_preference must be lowercase.

    ## 💬 EXAMPLE:

    User text:
    "I want good comfort, and I’m interested in Mahindra."

    Expected output:
    {
      "user_profile": [
        {
        "intent": "comfort",
          "statement": "I am looking for good comfort",
          "answer": ["good comfort"]
        }
      ],
      "user_preference": [
        {
          "intent": "brand_name",
          "statement": "I am interested in Mahindra",
          "answer": ["mahindra"]
        }
      ]
    }

    ## 🔒 Validation Rules:
    - If an extracted intent is not in the preference list above, it must go to `user_profile`.
    - Always infer meaningful "question" values that represent what the user expressed.
    - Never leave both arrays empty — at least one must contain structured information if something relevant is found.
    """

    user_prompt = f"""
    Extract 'user_profile' and 'user_preference' data according to the above rules from this text:

    "{user_text}"
    """

    return system_prompt, user_prompt
