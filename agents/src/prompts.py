

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


# def prompts_to_fix_llm(data, user_input):
#     system_prompt = (
#         "You are a precise matching assistant. "
#         "Your task is to find the single closest match in the given dataset to the user input. "
#         "You must ALWAYS return exactly one key from the dataset — never combine or merge multiple entries. "
#         "Return the key exactly as it appears in the dataset (preserve original case, spacing, punctuation, and symbols). "
#         "Do NOT reformat, modify, or partially join dataset values. "
#         "If no perfect match is found, return the single closest key only. "
#         "Examples:\n"
#         "- Dataset has ['Volvo-1', 'Toyota', 'Ford Focus'] and input is 'voluo' → Return 'Volvo-1'\n"
#         "- Dataset has ['Mahindra & Mahindra', 'Scorpio', 'S7 120 2WD 7 STR'] and input is 'mahindra' → Return 'Mahindra & Mahindra'\n"
#         "Never output multiple items or merge values together."
#         "Never return key always return the corrected value"
#     )

#     user_prompt = f"""Dataset: {data}

# User input: "{user_input}"

# Return exactly one dataset key that best matches the intent. 
# Do not merge or combine multiple dataset items. 
# Return only one key, exactly as written in the dataset.
# """
#     return system_prompt, user_prompt

def prompts_to_fix_llm(data, user_input):
    # ✅ RULE 1: If user_input EXACTLY exists in the dataset → return it directly, no need to ask LLM
    if user_input in data:
        return None, user_input   # LLM not needed

    # ✅ System prompt with your additional rules
    system_prompt = (
        "You are a precise matching assistant. "
        "Your task is to find the single closest match in the given dataset to the user input. "
        "You must ALWAYS return exactly one value from the dataset — never combine or merge multiple entries. "
        "Return the value exactly as it appears in the dataset (preserve original case, spacing, punctuation, and symbols). "
        "Do NOT reformat, modify, or partially join dataset values.\n\n"

        "STRICT RULE:\n"
        "If the user input contains a value that EXACTLY exists in the dataset, "
        "then return that exact dataset value ONLY, even if there are other similar values.\n"
        "Example: If dataset contains ['bolero', 'boleno'] and user input is 'bolero', "
        "then return ONLY 'bolero'. Ignore all other similar items.\n\n"

        "If no exact match is found, return the single closest match from the dataset.\n"
        "If no model is found, then take exactly what the user typed as model; "
        "otherwise, take the closest match from the list only.\n\n"

        "Examples:\n"
        "- Dataset has ['Volvo-1', 'Toyota', 'Ford Focus'] and input is 'voluo' → Return 'Volvo-1'\n"
        "- Dataset has ['Mahindra & Mahindra', 'Scorpio', 'S7 120 2WD 7 STR'] and input is 'mahindra' → Return 'Mahindra & Mahindra'\n\n"

        "Never return multiple items. Never merge values. "
        "Never output 'key': Always return the corrected dataset value only."
        "if not found then return user input"
    )

    # ✅ User prompt
    user_prompt = f"""Dataset: {data}

User input: "{user_input}"

Return exactly one dataset value that best matches the intent.
Do not merge or combine multiple dataset items.
Return only one value, exactly as written in the dataset.
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



def comparison_prompt(user_choice, compared_car_list):
    """
    Generates a comprehensive, JSON-based comparison prompt for multiple aspects of car evaluation.
    
    Args:
        user_choice (str): The primary car model the user is interested in.
        compared_car_list (list of str): List of other car models to compare against the user's choice.
        
    Returns:
        tuple: (system_prompt, user_prompt)
    """

    example_json = """
    Example Output Format:
    {
    "comparisons": {
        "Hyundai Creta vs Kia Seltos": {
        "price": {
            "Hyundai Creta": "₹10.87 - ₹19.20 lakh",
            "Kia Seltos": "₹10.90 - ₹20.35 lakh"
        },
        "fuel_efficiency": {
            "Hyundai Creta": "17.4 - 21.8 kmpl",
            "Kia Seltos": "17 - 20.7 kmpl"
        },
        "safety_features": {
            "Hyundai Creta": "6 airbags, ABS, ESC",
            "Kia Seltos": "6 airbags, ESC, ADAS (top variant)"
        }
        }
    },
    "common_points": [
        "All cars have 6 airbags",
        "All are available in petrol variants",
        "All have connected car technology"
    ],
    "key_differences": {
        "fuel_efficiency": {
        "Creta": "17.4 - 21.8 kmpl",
        "Seltos": "17 - 20.7 kmpl",
        "Hyryder": "21.1 - 27.97 kmpl (hybrid)"
        },
        "technology": {
        "Creta": "Bluelink system",
        "Seltos": "ADAS and 360° camera",
        "Hyryder": "Hybrid drivetrain, head-up display"
        }
    },
    "user_choice_justification": {
        "Hyundai Creta": "Well-balanced offering with strong comfort, reliability, and modern features, ideal for city and occasional highway drives."
    }
    }
        """.strip()

    system_prompt = (
        "You are an expert automobile analyst. Your task is to compare vehicles formally and present your findings "
        "strictly in a structured JSON format with the following keys:\n\n"
        "1. `comparisons`: A thorough, wise comparison (or structured section) between the USER CHOICE and each of the COMPARED CARS. "
        "Cover all relevant aspects like price, fuel efficiency, safety features, technology, space, driving comfort, resale value, brand trust, etc.\n"
        "2. `common_points`: A concise list (bullet-style or array) of all shared specifications or traits between the USER CHOICE and the COMPARED CARS.\n"
        "3. `key_differences`: Clear and detailed explanation of how the cars differ across relevant parameters. Organize it pairwise or feature-wise, focusing strongly on factors such as pricing, performance, maintenance, features, and user needs.\n"
        "4. `user_choice_justification`: Provide strong, formal, and user-centered reasoning explaining why a buyer might choose the USER CHOICE over others. Justify based on likely user preferences like affordability, performance, family suitability, city use, etc.\n\n"
        "Do not include any introduction, conclusion, marketing phrases, or personal opinions. Only return a valid JSON object with properly structured and labeled content under each required key.\n\n"
        "I will give you bonus If you return a JSON object correctly. Do not add false information.\n\n"
        f"{example_json}"
    )

    user_prompt = f"""
    I am considering the following car: "{user_choice}".
    Please compare it formally and comprehensively with these cars: {compared_car_list}.

    Your comparison should:
    - Be in a valid, structured JSON format only (no plain text or introductory remarks).
    - Include the following keys in the JSON response:
        1. `comparisons`: Thorough comparison between {user_choice} and each of the other cars.
        2. `common_points`: List of similar specs/features across all cars.
        3. `key_differences`: Detailed differentiation by feature and importance (especially price).
        4. `user_choice_justification`: Reasons why {user_choice} might be preferred over others by a user.

    This is a formal task; return **only the JSON**.
    """.strip()

    return system_prompt, user_prompt



def create_model_match_prompt(user_prompt, model_list):
    """
    Create a message prompt for an LLM to find a matching car model from the given list.
    Args:
        user_prompt (str): The user's input text.
        model_list (list): List of available car models (e.g., ['bmw', 'kwid', 'audi'])
    Returns:
        list: A list of messages in OpenAI-compatible format.
    """
    system_prompt = f"""
You are an intelligent car model matching assistant.

Your task is to find the best-matching car model from the given list based on the user prompt.
You must return **only** the exact name of the matching car model from the list, or "None" if no relevant model is found.

Here are the models you can consider: {model_list}

Return format: A single string. Example outputs: "bmw", "audi", "kwid", not "None"
"""

    messages = [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_prompt.strip()}
    ]
    
    return messages







def get_competitor_model_prompt(user_model, model_list, top_n=2):
    """
    Create a message prompt for an LLM to find the top N competitor car models from the given list.
    Args:
        user_model (str): The user's input car model.
        model_list (list): List of available car models (e.g., ['bmw', 'kwid', 'audi'])
        top_n (int, optional): The number of top competing models to return (default is 2)
    Returns:
        list: A list of messages in OpenAI-compatible format.
    """
    system_prompt = f"""
You are an intelligent car model competitor assistant.

Your task is to find the top {top_n} competitor car models from the given list based on the user's input.
You must return **only** the exact names of the most relevant competing car models from the list.

Available models to consider: {str(model_list)}

Return format: A single list.
Example: ["BMW X5", "Audi Q7"]
Dont have empty list in output
"""

    messages = [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_model.strip()}
    ]
    
    return messages


def car_features_prompt(car_text: str):
    system_message = """
You are a precise feature-extraction assistant.

Your job is to extract ONLY **real, concrete car features** from the user text.
NOT categories or headings.

❌ Do NOT return:
- safety
- airbags (as a category)
- transmission
- dimensions
- engine
- fuel type
- comfort
- exterior
- interior
- convenience
- infotainment (category)
- technology (category)

✅ DO return specific features like:
- ABS
- ESC
- 6 airbags
- Power Windows
- projector headlamps
- auto climate control
- LED DRLs
- cruise control
- wireless charging
- Apple CarPlay
- Android Auto
- ventilated seats
- sunroof / panoramic sunroof
- rear camera / parking sensors
- traction control
- ISOFIX
- touchscreen infotainment

Rules:
- Extract ONLY real features.
- No duplicates.
- Clean names only.
- Final answer must be EXACTLY a Python list of feature strings.
- No explanation, no extra text.
    """

    user_message = f"""
Extract all real car features from the following text.
Return ONLY a Python list of features.

Example:
Input:
"Power Windows, dual airbags, ABS, rear camera available."

Output:
["Power Windows", "dual airbags", "ABS", "rear camera"]

Now process this input:
{car_text}
"""

    return system_message.strip(), user_message.strip()
