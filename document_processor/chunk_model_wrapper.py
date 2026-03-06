import os
import json
import logging
from gryd_worker import gryd
from gryd_worker import gryd_helpers as hp
try:
    from models import model as base_model
except ImportError:
    import models.model as base_model

logger = hp.get_logger(__name__)

class ModelWrapper:
    def __init__(self, model_name="chunk_saver", enterprise_id="autocrm", service="rag_agentic"):
        self.model_name = model_name
        self.enterprise_id = enterprise_id
        self.service = service
        self.model = base_model.Model(self.model_name, self.enterprise_id)
        self.enterprise = base_model.Enterprise(self.enterprise_id)
    
    def load_gryd_model(self, base_dir=None):
        """
        Load the Gryd model definition into the worker runtime.
        """
        if base_dir is None:
             base_dir = os.path.dirname(os.path.abspath(__file__))
        
        logger.info(f"Loading gryd model: {self.model_name}")
        return gryd.load_gryd_model(
            model_name=self.model_name,
            enterprise_id=self.enterprise_id,
            service=self.service,
            base_dir=base_dir
        )

    def setup_model(self, model_json_path=None):
        """
        Post the model definition to the Gryd system (creating the schema).
        """
        if model_json_path is None:
             base_dir = os.path.dirname(os.path.abspath(__file__))
             model_json_path = os.path.join(base_dir, "data", f"{self.model_name}.json")
            
        logger.info(f"Posting model definition from {model_json_path}")
        try:
            with open(model_json_path, "r") as f:
                model_def = json.load(f)
            
            response = self.enterprise.post_model(model_name=self.model_name, model=model_def)
            logger.info(f"Model {self.model_name} setup response: {response}")
            return response
        except Exception as e:
            logger.exception(f"Failed to setup model {self.model_name}")
            raise e

    def post_object(self, data: dict):
        """
        Post a new object (record) to the model.
        """
        try:
            logger.info(f"Posting object to {self.model_name}")
            response = self.model.post(data)
            return response
        except Exception as e:
            logger.exception(f"Failed to post object to {self.model_name}")
            raise e

    def update_object(self, object_id: str, data: dict):
        """
        Update an existing object (record).
        """
        try:
            logger.info(f"Updating object {object_id} in {self.model_name}")
            response = self.model.put(object_id, data)
            return response
        except Exception as e:
             logger.exception(f"Failed to update object {object_id} in {self.model_name}")
             raise e
