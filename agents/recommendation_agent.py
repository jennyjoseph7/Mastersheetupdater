import re
import time
import json
import logging
import numpy as np
from urllib.parse import urlparse
import ast
from qdrant_client import QdrantClient, models
import itertools
from ai_service import ai_service, ai_service_app # type: ignore
from qdrant_client import models
from qdrant_client.models import (
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    Range,
    PointStruct,
    MatchAny,
)

try:
    from .base_agent import BaseAgent
except ImportError:
    from base_agent import BaseAgent
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




# client = QdrantClient(host="localhost", port=6333)
client = QdrantClient(url="http://216.48.189.12:6333")



def generate_case_permutations(text):
    tokens = re.findall(r"[A-Za-z]+|[^A-Za-z]+", text)

    variations = []
    for t in tokens:
        if t.isalpha():
            variations.append([t.lower(), t.capitalize()])
        else:
            variations.append([t])

    output = ["".join(p) for p in itertools.product(*variations)]
    return list(set(output))



def get_vec_from_llm(user_query):
    syst,user = car_traits_prompt(user_query)
    messages=[
        {"role": "system", "content": syst},
        {"role": "user", "content": user}
    ]
    chain=ai_service.get_llm_response(messages=messages, model_identifier="gcp-gemini-2.5-flash-lite")
    logger.info("generated json "+chain)
    result = parse_json().extract_json_from_text(chain)
    
    return [result[k] for k in key_order]



def get_vector(raw_dict):
    if any(col in raw_dict for col in key_order):
        try:
            vec = get_vec_from_llm(str(raw_dict))
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

class MetadataRecommendation:
    def __init__(self,collection="autobot_summary_test_collection_2",model_identifier="gcp-gemini-2.5-flash-lite"):
        """
        Initializes a MetadataRecommendation object.

        Parameters:
        - collection (str): Qdrant collection name (default: autobot_summary_test_collection_2)
        - model_identifier (str): LLM model identifier (default: gcp-gemini-2.5-flash-lite)

        Returns:
        - None
        """
        get_collection(collection)
        self.collection_name=collection
        self.model_identifier=model_identifier

    def recommend_models(self,inp,default_limit=30):
        from gensim.models.fasttext import FastText
        model=FastText(
                sentences=["test"],
                vector_size=100,
                window=3,
                min_count=1,
                sg=1,
            )


        vec=model.wv[inp].tolist()

        hits = client.search(
            collection_name=self.collection_name,
            query_vector=vec,
            limit=default_limit)
        return [i.payload for i in hits ]
    def fix_by_llm(self, user_input):
        data=self.recommend_models(user_input)
        kd=[]
        for i in data:
            kd.extend(i.values())
        kd=list(set(kd))
        logger.info(f"filter_data: {kd}")

        system_prompt,user_prompt=  prompts_to_fix_llm(kd,user_input)
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}]
        output=ai_service.get_llm_response(messages=messages, model_identifier=self.model_identifier)
        
        return output


class parse_json:
    def extract_json_from_text(self,text: str):
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
    def extract_json(self, text: str):
        match = re.search(r"\{.*?\}", text, flags=re.DOTALL)
        if not match:
            return None
        candidate = match.group(0)

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None



    def extract_json_block(self,text: str):

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



def get_traits(user_query,model_identifier="gcp-gemini-2.5-flash-lite"):

    """
    Get car traits from user query using LLM.

    Args:
        user_query (str): User's input text.
        model_identifier (str, optional): Model identifier to use for LLM. Defaults to "gcp-gemini-2.5-flash-lite".

    Returns:
        dict: JSON object containing user's trait scores.
    """

    
    system_prompt,user_prompt=  prompt_vector_gen(user_query)
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}]

    output=ai_service.get_llm_response(messages=messages, model_identifier=model_identifier)
    
    return parse_json().extract_json(output)

def generate_markdown_clean(data):

    """
    Generate clean markdown documentation for the car preference configuration.

    Parameters:
        data (dict): Dictionary containing the car preference configuration data.

    Returns:
        str: Markdown string containing the documentation.

    The function takes the input data and generates a markdown string that can be used to document the car preference configuration.
    It iterates through the input data and generates a markdown string with the following format:
    # Car Preference Configuration Documentation

    ## Section 1
    ### Key 1
    - Includes:
        - Item 1
        - Item 2
    ### Key 2
    - Range: Key 2

    ## Section 2
    ### Key 1
    - Includes:
        - Item 1
        - Item 2
    ### Key 2
    - Range: Key 2

    The function then returns the markdown string as a str object.
    """

    
    md = "# Car Preference Configuration Documentation\n\n"
    for section, content in data.items():
        md += f"## {section.replace('_', ' ').title()}\n\n"
        
        if isinstance(content, dict):
            for k, v in content.items():
                md += f"### {k}\n"                
                if isinstance(v, list):
                    md += "- Includes:\n"
                    for item in v:
                        md += f"  - {item}\n"
                elif isinstance(v, dict):
                    md += f"- Range: {k}\n"   # Just show the label, not the rules
                md += "\n"
        md += "\n"
    return str(md)

def mergerFreeText(user_query,model_identifier="gcp-gemini-2.5-flash-lite"):
    """
    This function takes a user query and generates a markdown string that can be used to document the car preference configuration.
    It calls the mergerFreeTextPrompt function to generate the system and user prompts, and then calls the ai_service.get_llm_response function to generate the output.
    The output is then processed to replace the "statement" key with "question", and the processed output is returned as a str object.
    
    Parameters:
        user_query (str): The user query to be processed.
        model_identifier (str): The identifier for the model to be used for processing the query. Defaults to "gcp-gemini-2.5-flash-lite".
    
    Returns:
        str: The processed output as a markdown string.
    """
    
    filter_data_=generate_markdown_clean(filter_json)
    system_prompt,user_prompt=  mergerFreeTextPrompt(user_text=user_query,formal_filters=filter_data_)
    
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}]

    output=ai_service.get_llm_response(messages=messages, model_identifier=model_identifier)
    output=output.replace("statement","question")
    logger.info(f"free text output>>{output}")
    return parse_json().extract_json_block(output)



def merge_traits(lists):
    """
    Merge the given list of traits into a single vector.

    Parameters:
        lists (list): List of lists, where each sublist contains trait values.

    Returns:
        np.ndarray: The merged trait vector.
    """
    logger.info(f"input traits {lists}")
    mean_elementwise = [sum(values) / len(values) for values in zip(*lists)]

    CustomerAffinity = np.array(mean_elementwise)
    logger.info(f"CustomerAffinity (before norm): {list(CustomerAffinity)}")
    
    norm = np.linalg.norm(CustomerAffinity)
    if norm == 0:
        return np.zeros_like(CustomerAffinity)  # or return CustomerAffinity as-is
    CustomerAffinity = CustomerAffinity / norm
    logger.info(f"this is CustomerAffinity after norm>>>{list(CustomerAffinity)}")
    return CustomerAffinity




def filter_data(filters=None, affinity=None,negative_filters=None):
    """
    Filter data based on the given filters and affinity.

    Parameters:
        filters (list): List of filter data, where each item is a dictionary containing 'intent' and 'answer' keys.
        affinity (list): List of affinity data, where each item is a dictionary containing 'answer' key.
        negative_filters (list): List of negative filter data, where each item is a dictionary containing 'intent' and 'answer' keys.

    Returns:
        tuple: A tuple containing the filtered data and the merged trait vector.
    """
    
    filter = {}
    iintent=[]
    vectors = []    
    if negative_filters:
        for data in negative_filters:
            if data['intent'] in filter_json.keys():
                logger.info(f"from filter .json{data}")
                d=filter_json[data['intent']]

                filter[data['intent']] = d[data['answer'][0]]
            else:
                filter[data['intent']] = data['answer']
        return filter
    if filters:
        for data in filters:
            if data['intent'] in filter_json.keys():
                logger.info(f"from filter .json{data}")
                # if data["intent"]=="price_range":
                #     filter[data['intent']] = data['answer'][0]
                d=filter_json[data['intent']]
                ddd=d[data['answer'][0]]
                logger.info(f"will be passed>>{ddd}")

                filter[data['intent']] = ddd
            else:
                filter[data['intent']] = data['answer']
    else:
        filter = {}
            
    if affinity:
            
            for data in affinity:
                logger.info(f"Not from filter .json{data}")
                dict_score=get_traits(str(data['answer']))
                iintent.append(data.get("intent"))
                vectors.append([dict_score[k] for k in key_order])
    else:

        vectors.append([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])



    return filter,( merge_traits(vectors),iintent)




def get_collection_recommendation(collection):

    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=16, distance=Distance.DOT),
        )

def get_fixed_filter(fix_filters,collection_filter):

    """
    This function takes in a dictionary of fixed filters and returns a new dictionary with the values fixed using the LLM model.
    
    Parameters:
        fix_filters (dict): A dictionary of fixed filters where the keys are the filter names and the values are lists of values to be fixed.
    
    Returns:
        dict: A dictionary with the fixed filters.
    """

    logger.info("here")
    rw=MetadataRecommendation(collection_filter)

    logger.info(f"fix filter collection>>>{(collection_filter)}")
    for key,value in fix_filters.items():
        if key in ["model_name","product_name","brand_name","vehicke_type","vehicle_type","variant_name"]:
                logger.info(f"key>> {key}")
                logger.info(f"value>> {value}")
                da=rw.fix_by_llm(f"key is {key} and value is {value[0]}")
                logger.info("fixed value>>>"+da)   
                fix_filters[key]=[da]
    return fix_filters




class RecommendationWrapper:
    def __init__(self,collection="autocrm_recommendation",dealership_id=None,history=None):
        self.count_res=0
        get_collection_recommendation(collection)
        self.collection=collection
        self.history=history
        self.dealership_id=dealership_id
        if history is None or not history:
            self.history={
                "affinity":[],
                "positive_filters":[],
                "negative_filters":[],
                "intent":[],
            }

    def recommend_models(self,CustomerAffinity, default_limit,collection_filter,filters=None,fix_filters=None, offset_value=None,negative_filters=None):

        metadata = {}
        filter_ = []
        negative_filter_ = []
        if fix_filters and filters is not None:
            logger.info(f"fix_filters>>>ppppp{fix_filters}")
            filters=get_fixed_filter(fix_filters,collection_filter)
        else:

            if self.history :
                self.history["intent"].extend(CustomerAffinity[1])

                poss=self.history.get("positive_filters")
                for pos in poss:
                    for i, j in pos.items():
                        filters[i] = j
                
                negg=self.history.get("negative_filters")
                for neg in negg:
                    for i, j in neg.items():
                        negative_filters[i] = j

                aff=self.history.get("affinity")
                if aff:

                    logger.info(f"CustomerAffinity>>>{CustomerAffinity}")
                    aff.append(CustomerAffinity[0].tolist())
                    CustomerAffinity=merge_traits(aff)
                    self.history["affinity"]=CustomerAffinity.tolist()

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
                                lte=value.get("lte"),
                                gte=value.get("gte")
                            )
                        )
                    )
                else:
                    match_any_key = []
                    for i in value:
                        ii=[]

                        if isinstance(i, str):
                            logger.info(f"before permutation {i}")
                            iss = generate_case_permutations(i)
                            logger.info(f"after permutation {iss}")

                            match_any_key.extend(iss) 
                        else:

                            for ia in generate_case_permutations(i):
                                ii.append(ia)
                            
                            match_any_key.append(i)
                    filter_.append(
                        FieldCondition(
                            key=key.replace(" ", "_").lower(),
                            match=models.MatchAny(any=match_any_key)
                        )
                    )
                if self.dealership_id:
                    filter_.append(
                            FieldCondition(
                                key="dealership_id",
                                match=models.MatchAny(any=self.dealership_id)
                            ))
                    



        if negative_filters:
            negative_filters=(get_fixed_filter(negative_filters,collection_filter))

            for key, value in negative_filters.items():

                logger.info(f"Negative value>>> {value}")
                negative_filter_.append(
                        FieldCondition(
                            key=key.replace(" ", "_").lower(),
                            match=models.MatchAny(any=value)
                        )
                    )
                

        logger.info(f"to be passed in search")
        logger.info(f"input vectors >>> {list(CustomerAffinity)}")
        logger.info(f"positive filter >>> {filter_}")
        logger.info(f"negative filter >>> {negative_filter_}")
        logger.info(f"recommendation from collection >>> {self.collection}")
        
        
            
        hits = client.search(
            collection_name=self.collection,
            query_vector=CustomerAffinity,
            query_filter=Filter(must=filter_ if filters else None,must_not=negative_filter_ if negative_filters else None),
            limit=default_limit,
            offset=offset_value
        )
        logger.info(f"hits >>> {(hits)}")

        count_resp = client.count(
            collection_name=self.collection,
            count_filter=Filter(must=filter_ if filters else None,must_not=negative_filter_ if negative_filters else None),

            exact=True
        )

        if hits:

            if filters:

                self.history["positive_filters"]=[filters]

                self.history["intent"].extend(filters.keys())

            if negative_filters:

                self.history["negative_filters"]=[negative_filters]

            if any(key in pf for pf in self.history["positive_filters"] for key in ("product_name", "model_name")):
                logger.info("it has model name or product name")
                output = [
                    {
                        "id": hit.id,
                        "brand": (payL := hit.payload).get("brand", payL.get("brand_name")),
                        "metadata": payL,
                    }
                    for hit in hits
                ]

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
                    "recommendation_history":self.history,
                    
                "total_result":count_resp.count}
        else:
            if self.count_res>1:
                return []
            self.count_res+=1
            logger.info("fixing filters")
            return self.recommend_models(CustomerAffinity=CustomerAffinity, default_limit=default_limit,filters=filters,collection_filter=collection_filter, fix_filters=filters,offset_value=offset_value,negative_filters=negative_filters)


        # return {"result":results,

    def get_trait(lists):
        mean_elementwise = [sum(values) / len(values) for values in zip(*lists)]
        CustomerAffinity = np.array(mean_elementwise)
        CustomerAffinity = CustomerAffinity / np.linalg.norm(CustomerAffinity)
        return CustomerAffinity



    def upsert_dealership(self,brand_name,dealership_ids,collection="autocrm_recommendation"):
        '''
        this will update the dealerships for a particular brand in qdrant'''
        hits = client.search(
            collection_name=self.collection,
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



    def upsert_features(self,collection="autocrm_recommendation"):
        '''
        this function will upsert features in qdrant
        '''
        def extract_selected_features(metadata: dict):
            keys_needed = [
                "comfort_and_convenience",
                "engine_and_performance",
                "interior_feature",
                "exterior_feature",
                "safety_feature",
                "technology",
                "engine"
            ]

            return {key: metadata.get(key) for key in keys_needed if key in metadata}

        hits = client.search(
            collection_name=self.collection,
            query_vector=[0.1, 0.1, 0.1,0.1,0.1,0.1,0.1 , 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
            limit=5000
        )

        for hit in hits:
            payL = hit.payload
            metadata = {
                "id": hit.id,
                "model":payL.get("model_name",payL.get("product_name")),
                "brand": payL.get("brand", payL.get("brand_name")),
                "variant":payL.get("variant_name",""),
                "metadata": payL,
            }

            metadata_=extract_selected_features(metadata=metadata.get("metadata"))
            syst,user=car_features_prompt(car_text=metadata_)
            messages=[
                {"role": "system", "content": syst},
                {"role": "user", "content": user}
            ]
            agent_to_get_features=ai_service_app.get_llm_response(messages=messages, model_identifier="gcp-gemini-2.5-flash-lite")

            lagent_to_get_featuresst = ast.literal_eval(agent_to_get_features)

            feature_keys=lagent_to_get_featuresst

            client.set_payload(
                collection_name=collection,
                payload={"car_features": feature_keys},
                points=[metadata.get("id")]
            )


    def recommend(self,Affinity,filters,collection_filter="autobot_summary_test_collection_2",default_limit=None,offset_value=None,negative_filters=None):

        filters_applied,trait_affinities = filter_data(filters=filters,affinity=Affinity)
        if negative_filters:
            negative_filter = filter_data(negative_filters=negative_filters)
        else:
            negative_filter = None

        return self.recommend_models(
            CustomerAffinity=trait_affinities,
            default_limit=default_limit,
            filters=filters_applied,
            collection_filter=collection_filter,
            offset_value=offset_value,
            negative_filters=negative_filter
        )

    def run(self,Affinity,filters,free_text=None ,collection_filter="autobot_summary_test_collection_2",default_limit=None,max_n=None,offset_value=None):
        path = "agents/src/recommendation_questions.json"
        with open(path, "r") as f:
            metadata_qna = json.load(f)
        
        if free_text:

            json_data = mergerFreeText(free_text)
            new_filters = json_data.get("user_preference", [])
            new_affinity = json_data.get("user_profile", [])
            negative_filters = json_data.get("negative_filters", [])

            # def normalize_transmission(filter_list):
            #     transmission_map = {
            #         "manual": "Prefer manual",
            #         "automatic": "Prefer automatic",
            #         "both": "I’m open to both automatic and manual",
            #         "hybrid": "Prefer hybrid"
            #     }
            #     for f in filter_list:
            #         intent = f.get("intent")
            #         logger.info(f">>>>>>>>>>>>>>>>{f}")
            #         if intent=="transmission_type":
            #             f["answer"] = [transmission_map.get(f.get("answer")[0], "Other")]
            #     return filter_list

            # if new_filters or  negative_filters:
            #     normalize_transmission(new_filters)
            #     normalize_transmission(negative_filters)

            Affinity=Affinity+new_affinity
            filters=filters+new_filters
            negative_filters+=negative_filters
            logger.info(f"Affinity {Affinity}")
            logger.info(f"positive filters {filters}")
            logger.info(f"negative_filters {negative_filters}")
        if not Affinity and not filters and not negative_filters:

            metadata_ = [
                {
                    "question": i.get("question"),
                    "options": i.get("options"),
                    "intent": i.get("intent"),
                }
                for i in metadata_qna

            ]
            import random

            random.shuffle(metadata_)


            return {
                "match_refining_questions":[metadata_[0]],
                "top_vehicles":[],
                "status":"passed",
                "total_vehicles_found":0,}
        
        rec=self.recommend(Affinity,filters,collection_filter=collection_filter,default_limit=default_limit,offset_value=offset_value,negative_filters=negative_filters)

        kd = []
        int_ = []
        if not rec:
            return {
                "top_vehicles":[],
                "status":"failed",
                "total_vehicles_found":0,}
        if max_n:
            if max_n<50:

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

                return {
                    "top_vehicles":rec.get("result"),
                    "status":"success",
                    "total_vehicles_found":rec.get("total_result"),
                    "match_refining_questions":metadata_,
                    "recommendation_history":rec.get("recommendation_history"),

                }
            return {
                "top_vehicles":rec.get("result"),
                "status":"success",
                "total_vehicles_found":rec.get("total_result"),
                "recommendation_history":rec.get("recommendation_history"),

                }
        return {
                "top_vehicles":rec.get("result"),
                "status":"success",
                "total_vehicles_found":rec.get("total_result"),
                "recommendation_history":rec.get("recommendation_history"),
        }




def  build_intent_filter_agent(questions,brand_model_name):
    
    """
    Builds an agent that filters user questions into intents.

    Args:
        questions (list): A list of user questions.
        brand_model_name (str): The brand and model name of the car.

    Returns:
        dict: The output from the GCP Gemini 2.5 Flash Lite model.
    """

    system_prompt,user_prompt=  build_intent_filter_prompts(brand_model_name=brand_model_name,questions=questions)
    messages=[    
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    chain=ai_service.get_llm_response(messages=messages, model_identifier="gcp-gemini-2.5-flash-lite")
    return chain


class RecommendationAgent(BaseAgent):
    def __init__(self, dealership_id=None, model_identifier='azure-gpt-4o') -> None:
        """
        Initializes a RecommendationAgent object.

        Parameters:
        source (dict or str, optional): A JSON object or path to a JSON file containing customer interaction data. Defaults to None.
        model_identifier (str, optional): The identifier of the Large Language Model to use for generating code based on human instructions. Defaults to 'azure-gpt-4o'.
        """
        self.model_identifier : str = model_identifier
        self.dealership_id : str = dealership_id
    

    def _extract_pattern(self,data):
        history=data.get("recommendation_history")
        user_interaction=data.get("user_interaction")
        if user_interaction:
            user_message=user_interaction.get("user_message")
            question=user_interaction.get("question")
            if not user_interaction.get("free_text"):
                user_interaction['free_text']=user_message  if not question else question+" "+user_message
            intent = user_interaction.get("intent")
            if intent in ["free_text","error"]:
                return
        if history:
            if history.get(""):
                pass


            # asked_intent=[] 
            # history=data.get("history")
            # if history:
            #     data["history_intent"] = []
            #     for key in history:
            #         intent = key.get("intent")
            #         if intent in ["free_text","error"]:
            #             continue
            #         asked_intent.append(intent)
            #     logger.info(data)
            #     data['history_intent'].extend(asked_intent)

            
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
      collection=data.get("collection","autocrm_recommendation")
      collection_filter=data.get("collection_filter","autobot_summary_test_22")
      max_n=data.get('Max number',None)
      user_interaction=data.get("user_interaction",None)
      free_text=user_interaction.get('free_text',None)
      offset=int(data.get('offset',0))
      default_limit=int(data.get('default_limit',20))
      history=data.get("recommendation_history")
      rw=RecommendationWrapper(collection=collection,dealership_id=self.dealership_id,history=history)
      try:
          result=rw.run(Affinity=user_profile,filters=user_preference,free_text=free_text,collection_filter=collection_filter,max_n=max_n,offset_value=offset,default_limit=default_limit)
          if "error" in result:
              return {"error": "error"}
      except Exception as e:
          return {"error": str(e)}
        

    #   path = "agents/src/recommendation_questions.json"
    #   with open(path, "r") as f:
    #         list_questions0 = json.load(f)

      
      if result:
          if result.get("match_refining_questions"):
              
              logger.info(f"match_refining_questions {result.get('match_refining_questions')}")
              list_questions=[ i for i in result.get("match_refining_questions") if i.get("intent") in ["seating","vehicle_type","fuel_type","transmission","price_range"]]
              brand_model = (f"{result.get('top_vehicles')[0].get('brand')} {result.get('top_vehicles')[0].get('metadata', {}).get('product_name')}" 
                        if result.get("top_vehicles") else None)
              logger.info(f"brand_model {brand_model}")
              if not brand_model:
                  return result
              asound=build_intent_filter_agent(questions=list_questions,
              brand_model_name=brand_model)
              asound = json.loads(asound) if isinstance(asound, str) else asound
              not_asked = asound.get("not_ask", [])
              logger.info(f"not_asked {not_asked}")

              mrq=[
                    q for q in result.get("match_refining_questions") if q.get("intent") not in not_asked
                ]
              if history:
                  mrq_=[i for i in mrq if i.get("intent") not in history.get("intent")][0]
              else:
                  mrq_=mrq[0]
              question=mrq_.get("question")
              options=mrq_.get("options")
              temp=template_prompt(question,options)

              result["match_refining_questions"] = mrq_
              result["Answer Validation Prompt"]=temp
          return result
      else:
          return [] 

    def main(self,data):

        data = self._extract_pattern(data)
        result = self._request_data(data)
        logger.info("result")
        # logger.info(result)
        # result['identifier']=template_prompt()
        return result



if __name__ == "__main__":

    collection="autocrm_recommendation"
    collection_filter="autobot_summary_test_22"
    free_text="I want good confort, I am interested in scorpio"
    offset=20
    limit=10 
    max_n=10
    agent = RecommendationAgent()
    data= {
    # "user_profile": [
    #   {
    #     "question": "Got a budget in mind?",
    #     "answer": [
    #       678894557
    #     ]
    #   }
    # ],
    "user_profile": [],
    "user_preference": [],
    # "user_preference": [
    #   {
    #     "intent": "brand_name",
    #     "answer": [
    #       "Mahindra"
    #     ]
    #   },
    #   {
    #     "intent": "product_name",
    #     "answer": [
    #       "Bolero"
    #     ]
    #   }
    # ],
    # "free_text": "i am short heighted suggest me a car for my budget  20 lakhs ",
    "Max number":   5,
    "collection": "autocrm_recommendation",
    # "question": "What’s your preference when it comes to transmission?",
    # "intent": "transmission_type",
    "user_interaction": {"user_message": "i dont want Automatic transmission and I am short heighted"},
    "default_limit": 5,
    "recommendation_history":  {
        "affinity": [
            [0.0,
            0.0,
            0.0,
            -0.7378647873726218,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            -0.5270462766947299,
            0.0,
            0.0,
            -0.42163702135578396,
            0.0]
        ],
        "positive_filters": [
        ],
        "negative_filters": [],
        "intent": [
            "height",
            "price_range",
            "purchase_reason"
        ]
    },
    } 





    import time
    t1=time.time()
    res=agent.main(data)
    logger.info(f"{time.time()-t1:.6f}")


    da=(json.dumps(res, indent=4, default=str))
    # print(res)
    with open("recommendation_output.json", "w") as f:
        f.write(da)

    # result=results.run(filters=user_preference,Affinity=user_profile,collection_filter=collection_filter,default_limit=limit,offset_value=offset)
    # print(result)
