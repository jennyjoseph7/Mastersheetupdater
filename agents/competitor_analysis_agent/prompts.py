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

