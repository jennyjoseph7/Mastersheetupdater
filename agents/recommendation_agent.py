import re
import time
import json
import logging
import requests
import numpy as np
import pandas as pd

from urllib.parse import urlparse
from gensim.models.fasttext import FastText
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    Range,
    PointStruct,
    MatchAny,
)

from ai_service import ai_service, ai_service_app

# Try/except import for flexible module context
try:
    from .base_agent import BaseAgent
except ImportError:
    from base_agent import BaseAgent

# Local imports
from src.prompts import *


def get_logger(name , log_level = 'info'):
    log_level = log_level.upper()
    if log_level not in ["DEBUG","INFO","WARNING","ERROR","CRITICAL"]:
        raise ValueError("Invalid log level .please use one of DEBUG,INFO,WARNING,ERROR,CRITICAL")
    logging.basicConfig(
        format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
        level = getattr(logging,log_level))
    logging.Formatter.converter = time.gmtime
    logger = logging.getLogger(name)
    return logger

logger = get_logger(__name__)

with open("agents/src/recommendation_utils.json", "r") as f:
    filter_json = json.load(f)    
key_order = ['power', 'engine', 'torque', 'dimension', 
'wheelbase', 'boot_space', 'technology', 'eco_friendly', 'fuel_capacity', 'safety_feature', 
'fuel_efficiency', 'exterior_feature', 'interior_feature', 'engine_and_performance',
'comfort_and_convenience','price']

model = FastText(
    sentences=["test"],
    vector_size=100, 
    window=3,
    min_count=1,
    sg=1  
)

# client = QdrantClient(host="localhost", port=6333)
client = QdrantClient(url="http://216.48.189.12:6333")

def upsert_dealership(brand_name,dealership_ids,collection="autobot_test_22"):

    hits = client.search(
        collection_name=collection,
        query_vector=[0.1, 0.1, 0.1,0.1 , 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="brand_name",
                    match=models.MatchAny(any=[brand_name])
                )
            ]
        ),
        limit=5000

    )

    kd=[]
    for i in hits:
        kd.append(i.id)

    client.set_payload(
        collection_name=collection,
        payload={
            "operating_brands": dealership_ids,
        },
        points=kd,
    )




def extract_json_from_text(text: str):
    """
    Extracts the first JSON object found in the text using regex.
    Returns a Python dict if successful, otherwise None.
    """
    try:
        pattern = r"\{[\s\S]*?\}"
        match = re.search(pattern, text)
        
        if match:
            json_str = match.group(0)
            logger.info("JSON string found, attempting to parse...")
            
            try:
                data = json.loads(json_str)
                logger.info("JSON successfully parsed.")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON: {e}")
                return None
        else:
            logger.warning("No JSON object found in the text.")
            return None

    except Exception as e:
        logger.exception(f"Unexpected error while extracting JSON: {e}")
        return None
def get_vec(user_query):
    syst,user = car_traits_prompt(user_query)
    messages=[
        {"role": "system", "content": syst},
        {"role": "user", "content": user}
    ]
    chain=ai_service.get_llm_response(messages=messages, model_identifier="azure-gpt-4o-mini")
    logger.info("generated json "+chain)
    result = extract_json_from_text(chain)
    
    return [result[k] for k in key_order]



def get_vector(raw_dict):
    if any(col in raw_dict for col in key_order):
        try:
            vec = get_vec(str(raw_dict))
            raw_dict['vector'] = vec
        except Exception as e:
            logger.info("kind of errror"+e)
            raw_dict['vector'] = None
    return raw_dict




def get_collection(collection):
    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=100, distance=Distance.COSINE),
        )
import numpy as np

def normalize(v):
    norm = np.linalg.norm(v)
    return v / norm if norm != 0 else v

def merge_vectors(vectors):
    # Normalize each vector
    normalized = [normalize(v) for v in vectors]
    # Average
    merged = np.mean(normalized, axis=0)
    # Normalize final
    return normalize(merged)






class MetadataRecommendation:
    def __init__(self,collection="autobot_summary_test_collection_2",model_identifier="azure-gpt-4o-mini"):
        get_collection(collection)
        self.collection_name=collection
        self.model_identifier=model_identifier



    def recommend_models(self,inp,default_limit=20):


        vec=model.wv[inp].tolist()

        hits = client.search(
            collection_name=self.collection_name,
            query_vector=vec,
            limit=default_limit,

        )

        return [i.payload for i in hits ]
    def fix_by_llm(self, user_input):
        data=self.recommend_models(user_input)
        logger.info(f"filter_data: {data}")
        kd=[]
        for i in data:
            kd.extend(i.values())

        system_prompt,user_prompt=  prompts_to_fix_llm(kd,user_input)
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}]
        output=ai_service.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        
        return output

 



def extract_json(text: str):
    match = re.search(r"\{.*?\}", text, flags=re.DOTALL)
    if not match:
        return None
    candidate = match.group(0)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None



def extract_json_block(text: str):
    """
    Extracts structured JSON-like content from text.

    Expected format:
    {
      "user_profile": [...],
      "user_preference": [...]
    }

    Returns parsed dict or None if not found.
    """
    try:
        # Try to find JSON-like block in text
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        
        json_str = match.group(0)
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError:
        # Try to fix common issues and reattempt parsing
        try:
            fixed = (
                text.replace("“", "\"")
                    .replace("”", "\"")
                    .replace("‘", "'")
                    .replace("’", "'")
            )
            match = re.search(r"\{[\s\S]*\}", fixed)
            if match:
                return json.loads(match.group(0))
        except Exception:
            return None
    return None




def get_traits(user_query,model_identifier="azure-gpt-4o-mini"):
    system_prompt,user_prompt=  prompt_vector_gen(user_query)
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}]

    output=ai_service.get_llm_response(messages=messages, model_identifier=model_identifier)
    
    return extract_json(output)


def mergerFreeText(user_query,model_identifier="azure-gpt-4o-mini"):
    system_prompt,user_prompt=  mergerFreeTextPrompt(user_query)
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}]

    output=ai_service.get_llm_response(messages=messages, model_identifier=model_identifier)
    output=output.replace("statement","question")
    return extract_json_block(output)





def merge_traits(lists):
    logger.info(f"input traits {lists}")
    mean_elementwise = [sum(values) / len(values) for values in zip(*lists)]

    CustomerAffinity = np.array(mean_elementwise)
    logger.info(f"CustomerAffinity (before norm): {CustomerAffinity}")
    
    norm = np.linalg.norm(CustomerAffinity)
    if norm == 0:
        return np.zeros_like(CustomerAffinity)  # or return CustomerAffinity as-is
    CustomerAffinity = CustomerAffinity / norm
    return CustomerAffinity




def filter_data(filters, affinity,freeText=None):
    filter = {}
    vectors = []    
    if filters:
        for data in filters:
            if data['intent'] in filter_json.keys():
                logger.info(f"from filter .json{data}")
                # if data["intent"]=="price_range":
                #     filter[data['intent']] = data['answer'][0]
                
                d=filter_json[data['intent']]

                filter[data['intent']] = d[data['answer'][0]]
            else:
                filter[data['intent']] = data['answer']

                # dict_scores = get_traits(f"question: {str(data['question'])} \n chosen answer: {str(data['answer'])}")   
                # vectors.append([dict_scores[k] for k in key_order])
    else:
        filter = {}
            
    if affinity:
            for data in affinity:
                logger.info(f"Not from filter .json{data}")
                dict_score=get_traits(str(data['answer']))
                vectors.append([dict_score[k] for k in key_order])
    else:
        vectors.append([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    if freeText:
        pass

    return filter, merge_traits(vectors)




def filter_data2(metadata):
    filter = {}
    vectors = []    

    for data in metadata:
        if data.get("filter"):

            if data['intent'] in filter_json.keys():
                logger.info(f"from filter .json{data}")

                if data["intent"]=="price_range":
                    filter[data['intent']] = data['answer'][0]
                else:
                    d=filter_json[data['intent']]

                    filter[data['intent']] = d[data['answer'][0]]
            else:
                filter[data['intent']] = data['answer']

            dict_scores = get_traits(f"question: {str(data['question'])} \n chosen answer: {str(data['answer'])}")   
            vectors.append([dict_scores[k] for k in key_order])
            
        else:
            logger.info(f"Not from filter .json{data}")
            dict_score=get_traits(str(data['answer']))
            vectors.append([dict_score[k] for k in key_order])

    return filter, merge_traits(vectors)






def get_collection(collection):

    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=16, distance=Distance.DOT),
        )

class RecommendationWrapper:
    def __init__(self,collection="autobot_test_22"):
        self.count_res=0
        get_collection(collection)
        self.collection=collection
        self.history_filter=[]

    def recommend_models(self,CustomerAffinity, default_limit,collection_filter,filters=None,fix_filters=None, offset_value=None):
        metadata = {}
        filter_ = []
        results = []
        
        self.history_filter.append(filters)
        if fix_filters and filters is not None:
            rw=MetadataRecommendation(collection_filter)

            logger.info(f"fix filter collection>>>{(collection_filter)}")
            for key,value in fix_filters.items():
                logger.info(f"key>> {key}")
                if key in ["model_name","product_name","brand_name","vehicke_type","vehicle_type","variant_name"]:
                        da=rw.fix_by_llm(f"key is {key} and value is {value[0]}")
                        logger.info("fixed value>>>"+da)   
                        fix_filters[key]=[da]

            filters=fix_filters
        logger.info(f"???{filters}")

        if filters is not None:
            for key, value in filters.items():
                if key == "available_colours":
                    filter_.append(
                        FieldCondition(
                            key="available_colours[]",
                            match=MatchAny(any=value)
                        )
                    )

                elif key == "fuel_capicity":
                    filter_.append(
                        FieldCondition(
                            key="fuel_capicity_range",
                            range=Range(
                                lte=value.get("lte", 20),
                                gte=value.get("gte")
                            )
                        )
                    )
                elif key == "price_range":
                    filter_.append(
                        FieldCondition(
                            key="price",
                            range=Range(
                                lte=value.get("lte", 500000),
                                gte=value.get("gte")
                            )
                        )
                    )
                else:
                    match_any_key = []
                    for i in value:
                        if isinstance(i, str):
                            match_any_key.append(i) # lower.key was there
                        else:
                            logger.info(f"this is ien{i}")
                            match_any_key.append(i)

                    filter_.append(
                        FieldCondition(
                            key=key.replace(" ", "_").lower(),
                            match=models.MatchAny(any=match_any_key)
                        )
                    )
        logger.info(f"filter >>> {filter_}")
        logger.info(f"input vectors >>> {CustomerAffinity}")
        logger.info(f"recommendation from collection >>> {self.collection}")
        hits = client.search(
            collection_name=self.collection,
            query_vector=CustomerAffinity,
            query_filter=Filter(must=filter_) if filters else None,
            limit=default_limit,
            offset=offset_value
        )
        logger.info(f"hits >>> {hits}")

        count_resp = client.count(
            collection_name=self.collection,
            count_filter=Filter(must=filter_) if filters else None,
            exact=True
        )

        if hits:
            logger.info(self.history_filter[0])
            if {"product_name", "model_name"} & self.history_filter[0].keys():
                logger.info("it has model name or product name")
                output = []

                for hit in hits:
                    # logger.info(hit)
                    logger.info("html>>>")
                    logger.info(type(hit))
                    logger.info("html>>>")

                    payL = hit.payload

                    metadata = {
                        "id": hit.id,
                        "brand": payL.get("brand", payL.get("brand_name")),
                        "metadata": payL,
                    }
                    logger.info("metadata")
                    output.append(metadata)

            else:
                top_variants = {}
                logger.info("it does not have model name or product name")

                for hit in hits:
                    
                    payL = hit.payload
                    product_name = payL.get("product_name")

                    # Build metadata once
                    metadata = {
                        "id": hit.id,
                        "brand": payL.get("brand", payL.get("brand_name")),
                        "metadata": payL,
                        "variant_name": payL.get("variant_name"),
                        "score": hit.score,
                    }

                    # If product not seen OR current score is higher -> update
                    if product_name not in top_variants or hit.score > top_variants[product_name]["score"]:
                        top_variants[product_name] = metadata

                # Get only the top variant data for each product_name
                output = list(top_variants.values())

                # logger.info(f"Top Variants :::> {output}")



            return {"result":output,
                    
                "total_result":count_resp.count}
        else:
            if self.count_res>1:
                return []
            self.count_res+=1
            logger.info("fixing filters")
            return self.recommend_models(CustomerAffinity=CustomerAffinity, default_limit=default_limit,filters=filters,collection_filter=collection_filter, fix_filters=filters,offset_value=offset_value)


        # return {"result":results,

    def get_trait(lists):
        mean_elementwise = [sum(values) / len(values) for values in zip(*lists)]
        CustomerAffinity = np.array(mean_elementwise)
        CustomerAffinity = CustomerAffinity / np.linalg.norm(CustomerAffinity)
        return CustomerAffinity

    def recommend(self,Affinity,filters,collection_filter="autobot_summary_test_collection_2",default_limit=None,offset_value=None):

        filters_applied,trait_affinities = filter_data(filters,Affinity)
        logger.info(f"filter applied {filters_applied}")
        logger.info(f"trait_affinities {trait_affinities}")
        return self.recommend_models(
            CustomerAffinity=trait_affinities,
            default_limit=default_limit,
            filters=filters_applied,
            collection_filter=collection_filter,
            offset_value=offset_value
        )
    
    def run(self,Affinity,filters,free_text=None ,collection_filter="autobot_summary_test_collection_2",default_limit=None,max_n=None,offset_value=None):

        if free_text:
            json_data=mergerFreeText(free_text)
            new_filters=json_data.get("user_preference")
            new_Affinity=json_data.get("user_profile")

            Affinity=Affinity+new_Affinity
            filters=filters+new_filters

        rec=self.recommend(Affinity,filters,collection_filter=collection_filter,default_limit=default_limit,offset_value=offset_value)
        recs=type(rec)
        logger.info(f">>{recs}")
        kd = []
        int_ = []
        if not rec:
            return {
                "top_vehicles":[],
                "status":"failed",
                "total_vehicles_found":0,}
        if max_n:
            if max_n<50:
                
                path = "agents/src/recommendation_questions.json"
                with open(path, "r") as f:
                    metadata_qna = json.load(f)

                for i, j in zip(Affinity, filters):
                    kd.append(i.get("question"))
                    int_.append(j.get("intent"))

                for i in metadata_qna:
                    question = i.get("question")
                    if question in kd:
                        int_.append(i.get("intent"))

                # Collect metadata where intent matches
                metadata_ = [
                    {
                        "question": i.get("question"),
                        "options": i.get("options"),
                        "intent": i.get("intent"),
                    }
                    for i in metadata_qna
                    if not i.get("intent") in int_
                ]


                if not rec:
                    return {
                        "top_vehicles":[],
                        "status":"failed",
                        "total_vehicles_found":0,}
                # rec = [hit.dict() for hit in rec]  # Qdrant returns a list of models
                # logger.info("??")
                # logger.info(rec.get("result"))
                # logger.info("??")

                    # "total_vehicles_found":rec.get("total_result"),
                return {
                    "top_vehicles":rec.get("result"),
                    "total_vehicles_found":rec.get("total_result"),
                    "match_refining_questions":metadata_
                }
            return {
                "top_vehicles":rec.get("result"),
                "total_vehicles_found":rec.get("total_result"),
                }
        return {
                "top_vehicles":rec.get("result"),
                "total_vehicles_found":rec.get("total_result"),
        }

















def build_intent_filter_prompts(brand_model_name: str, questions: list):
    """
    Create prompts that instruct the LLM to classify each question into an intent
    and decide whether it should be asked or not, returning only:
    {
      "not_ask": [...],
      "ask": [...]
    }
    """

    system_prompt = f"""
You are GPT-5.

Your task:
- Receive a brand/model name and a list of user-provided questions.
- Map each question to a HIGH-LEVEL INTENT (examples: pricing, warranty, safety, compatibility, preferences).
- DO NOT output questions.
- DO NOT output reasoning.
- DO NOT output explanations.
- Only extract **intents**.
- Then classify each intent as either "ask" or "not_ask".

Final output MUST be ONLY valid JSON with EXACT structure:

{{
  "not_ask": ["<intent>", "<intent>", ...],
  "ask": ["<intent>", "<intent>", ...]
}}

Rules:
- "ask" = relevant for determining user's needs for {brand_model_name}
- "not_ask" = irrelevant, redundant, or unnecessary
- All intents must be lowercase, snake_case.
- No trailing commas.
- No free text outside JSON.
"""

    user_prompt = f"""
Brand/Model: {brand_model_name}

Questions (JSON list):
{questions}

Extract intents → classify → output ONLY the JSON result.
"""
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    chain=ai_service.get_llm_response(messages=messages, model_identifier="azure-gpt-4o-mini")
    return chain



class RecommendationAgent(BaseAgent):
    def __init__(self, source=None, model_identifier='azure-gpt-4o') -> None:
        """
        Initializes a RecommendationAgent object.

        Parameters:
        source (dict or str, optional): A JSON object or path to a JSON file containing customer interaction data. Defaults to None.
        model_identifier (str, optional): The identifier of the Large Language Model to use for generating code based on human instructions. Defaults to 'azure-gpt-4o'.
        """
        self.model_identifier : str = model_identifier
        # self.data : Union[dict, list] = self._load_json(source=source)
    

    def _extract_pattern(self,data):
              


      formater={
        "brand_preference": "brand_name",
        "variant_preference": "variant_name",
        "color_preference": "available_colours",
        "model_preference": "product_name",
        "engine_type_preference": "engine",
        "transmission_preference": "transmission_type",
        "range_preference": "price",
        # "feature_preferences": "comfort_and_convenience",
        "seating_capacity_preference": "seating",
        "segment_preference": "vehicle_type"
        }
      fix_keys=[j for j in formater.keys()]
      for filter in data['user_preference']:
          intent=filter.get("intent")

          if intent in fix_keys:
            logger.info("fixing the input intent")
            filter['intent']=[formater[intent]]
      return data

    def _request_data(self, data:dict) -> list[dict]:

      user_preference=data.get("user_preference",[])
      user_profile=data.get("user_profile",[])
      limit=data.get("default_limit",20)
      offset=data.get("offset_value")
      max_n=data.get("Max number")
      collection=data.get("collection","autobot_test_22")
      collection_filter=data.get("collection_filter","autobot_summary_test_22")
      max_n=data.get('Max number',None)
      free_text=data.get('free_text',None)
      offset=int(data.get('offset',0))
      default_limit=int(data.get('default_limit',20))



      rw=RecommendationWrapper(collection=collection)
      try:
          result=rw.run(Affinity=user_profile,filters=user_preference,free_text=free_text,collection_filter=collection_filter,max_n=max_n,offset_value=offset,default_limit=default_limit)

          logger.info("result")
          if "error" in result:
              return {"error": "error"}
      except Exception as e:
          return {"error": str(e)}
        
      path = "agents/src/recommendation_questions.json"
      with open(path, "r") as f:    
            list_questions0 = json.load(f) 

      if result:
          if result.get("match_refining_questions"):
              
              list_questions=[ i for i in result.get("match_refining_questions") if i.get("intent") in ["seating","vehicle_type","fuel_type","transmission","price_range"]]
              brand_model = f"{result.get('top_vehicles')[0].get('brand')} {result.get('top_vehicles')[0].get('metadata').get('product_name')}"          
              logger.info(f"brand_model {brand_model}")
              asound=build_intent_filter_prompts(questions=list_questions,
              brand_model_name=brand_model)
              asound = json.loads(asound) if isinstance(asound, str) else asound
              not_asked = asound.get("not_ask", [])
              logger.info(f"not_asked {not_asked}")
              result["match_refining_questions"] = [
                    q for q in list_questions if q.get("intent") not in not_asked
                ]
          return result
      else:
          return [] 

    def main(self,data):

        data = self._extract_pattern(data)
        result = self._request_data(data)
        logger.info("result")
        # logger.info(result)

        return result






if __name__ == "__main__":

    filters = [
        {"intent":"seating","question":"Got a budget in mind?","answer":["4 to 5 people"],"filter":True},
            #    {"intent":"product_name","question":"Got a budget in mind?","answer":["Lauraa"],"filter":True}
               ]
    user_profile=[
        {"question":"Got a budget in mind?","answer":["678894557"]},
                  {"question":"my preferecne?","answer":["I am six fit tall"]}
                  ]
    user_preference=[
        #{  "intent":"brand_name","answer":["mahindra"]},
        {"intent":"price_range","question":"Got a budget in mind?","answer":["₹25 lakh – ₹50 lakh"]},

                # {"intent":"price_range","answer":["₹25 lakh – ₹50 lakh"]}
                ]
    collection="autobot_test_22"
    collection_filter="autobot_summary_test_22"
    free_text="I want good confort, I am interested in scorpio"

    # results = RecommendationWrapper(collection=collection)

    offset=20
    limit=10
    max_n=10





      

    
    agent = RecommendationAgent()

    data= {
    "user_profile": [
      {
        "question": "Got a budget in mind?",
        "answer": [
          678894557
        ]
      }
    ],
    "user_preference": [
      {
        "intent": "brand_name",
        "answer": [
          "Mahindra & Mahindra"
        ]
      },
      {
        "intent": "product_name",
        "answer": [
          "Bolero"
        ]
      }
    ],
    "Max number":   5,
    "collection": "autobot_test_22",
    "default_limit": 5
    } 

    res=agent.main(data)
    da=(json.dumps(res, indent=4, default=str))
    # print(res)
    with open("recommendation_output.json", "w") as f:
        f.write(da)



    # result=results.run(filters=user_preference,Affinity=user_profile,collection_filter=collection_filter,default_limit=limit,offset_value=offset)
    # print(result)
