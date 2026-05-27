
import os
import sys
from os.path import dirname, abspath
BASE_DIR = dirname(dirname(abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from gryd_worker import gryd
from gryd_worker import gryd_helpers as hp
from config import (
    AutocrmModel,
    post_autocrm_model,
    AUTOCRM_APP_ENTERPRISE_ID,
    AUTOCRM_DOCUMENT_PROCESSOR_PIPELINE_SERVICE_NAME,
)

logger = hp.get_logger(__name__)


class ModelWrapper:
    """
    Thin wrapper around AutocrmModel for the chunk_saver model.

    Uses AutocrmModel from config.py so that the correct enterprise ID,
    permissions, and logging patterns are applied consistently across the
    whole AutoCRM platform.
    """

    def __init__(
        self,
        model_name: str = "chunk_saver",
        enterprise_id: str = AUTOCRM_APP_ENTERPRISE_ID,
        service: str = AUTOCRM_DOCUMENT_PROCESSOR_PIPELINE_SERVICE_NAME,
    ):
        self.model_name = model_name
        self.enterprise_id = enterprise_id
        self.service = service
        self._autocrm = AutocrmModel(model_name, logger=logger)

    def load_gryd_model(self, base_dir=None):
        """Load the Gryd model definition into the worker runtime."""
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"Loading gryd model: {self.model_name}")
        return gryd.load_gryd_model(
            model_name=self.model_name,
            enterprise_id=self.enterprise_id,
            service=self.service,
            base_dir=base_dir,
        )

    def setup_model(self):
        """
        Post the model definition to the AutoCRM system (creates the schema).

        Delegates to post_autocrm_model from config.py, which reads the
        model JSON from the canonical data/ directory and applies any
        permissions defined in permissions.json.
        """
        logger.info(f"Setting up model via AutoCRM: {self.model_name}")
        try:
            response = post_autocrm_model(self.model_name, logger=logger)
            logger.info(f"Model {self.model_name} setup response: {response}")
            return response
        except Exception as e:
            logger.exception(f"Failed to setup model {self.model_name}")
            raise

    def post_object(self, data: dict):
        """Post a new object (record) to the model via AutocrmModel."""
        return self._autocrm.post(data)

    def update_object(self, object_id: str, data: dict):
        """Update an existing object (record) via AutocrmModel."""
        return self._autocrm.update(object_id, data)

    def get_object(self, object_id: str):
        """Retrieve an object by ID via AutocrmModel."""
        return self._autocrm.get(object_id)

    def delete_object(self, object_id: str):
        """Delete an object by ID via AutocrmModel."""
        return self._autocrm.delete(object_id)

    def list_objects(self, **kwargs):
        """List objects with optional filters via AutocrmModel."""
        return self._autocrm.list(**kwargs)

    def filter_objects(self, **kwargs):
        """Yield objects matching filters via AutocrmModel."""
        return self._autocrm.filter(**kwargs)

    def count_objects(self, **kwargs):
        """Count objects matching filters via AutocrmModel."""
        return self._autocrm.count(**kwargs)
