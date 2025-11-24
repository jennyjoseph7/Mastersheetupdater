import os
import sys
from ai_service import ai_service_app
from gryd_worker import gryd
from flask import Flask, jsonify
from recommendation_agent import *
gryd.SERVICE = os.environ.get("AUTOBOT_CONVERSATION_SERVICE_NAME","autocrm-agent")
gryd.set_queue_manager()
logger = gryd.hp.get_logger(__name__)

@gryd.is_a_task(
        
)
def car_recommendation(**kwargs):
    """
    Car recommendation function.

    This function takes in keyword arguments and performs car recommendation based on the user's preferences and profile.
    Parameters:
        user_profile (list, optional): A list of user preferences and profile information. Defaults to an empty list.
        user_preference (list, optional): A list of user preferences. Defaults to an empty list.
        collection (str, optional): The name of the collection to query for car data. Defaults to "autobot_test_22".
        collection_filter (str, optional): The name of the collection to query for car filter data. Defaults to "autobot_summary_test_22".
        max_n (int, optional): The maximum number of recommendations to return. Defaults to None.
        free_text (str, optional): Free text for car search. Defaults to None.
        offset (int, optional): The offset for pagination. Defaults to 0.
        default_limit (int, optional): The default number of recommendations to return. Defaults to 20.
        eg;
        data = {
          "user_profile": [
              {
                  "question": "Got a budget in mind?",
                  "answer": [
                      678894557
                  ]
              }
          ],
          "user_preference": [],
          "free_text": "I want good comfort, I am interested in scorpio",
          "max_n": 5,
          "collection": "autocrm_recommendation",
          "default_limit": 5
        }



    Returns:
        dict: A dictionary containing the recommended car data.
    """
    logger.info(f"Data Got>>>>> {kwargs}---")
    user_profile=kwargs.get('user_profile',[])
    user_preference=kwargs.get('user_preference',[])
    collection=kwargs.get("collection","autobot_test_22")
    collection_filter=kwargs.get("collection_filter","autobot_summary_test_22")
    max_n=kwargs.get('Max number',None)
    offset=int(kwargs.get('offset',0))
    default_limit=int(kwargs.get('default_limit',20))

    user_interaction=kwargs.get('user_interaction',{
        "user_message":"I am looking for safety",
        "question":"",
        "intent":""
    })
    recommendation_history=kwargs.get("recommendation_history",{
        "affinity":[],
        "positive_filters": [],
        "negative_filters": [],
        "intent": []
    })

    data={
        "user_profile": user_profile,
        "user_preference": user_preference,
        "collection": collection,
        "Max number": max_n,
        "default_limit": default_limit,
        "collection_filter": collection_filter,
        "offset": offset,
        "recommendation_history": recommendation_history,
        "user_interaction":user_interaction
    }
    try:
        agent = RecommendationAgent()
        result=agent.main(data)

    except KeyError as e:
        return jsonify({"error": f"Trait not found: {e}"}), 400

    logger.info(f">>> Sent {result}")
    result["next_offset"] = offset+20
    logger.info(f"set offset to {offset+20}")
    da=(json.dumps(result, indent=4, default=str))
    with open("recommendation_output.json", "w") as f:
        f.write(da)

    return result






