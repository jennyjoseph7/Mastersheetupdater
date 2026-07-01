from abc import ABC, abstractmethod
import logging

logging.basicConfig(level=logging.INFO)


class BaseCRMClass(ABC):

    def __init__(self, crm_name=None):
        self.crm_name = crm_name
        self.connected = False


    def connect(self):
        self.connected=True
        logging.info(f"{self.crm_name} connected")


    def validate_payload(self,data):
        
        if not isinstance(data,dict):
            raise ValueError("Payload must be dictionary")

        if len(data)==0:
            raise ValueError("Payload empty")

        return True


    def not_implemented(self,method):
        logging.info(
           f"{method} not implemented for {self.crm_name}"
        )
        return {
            "status":"not_implemented"
        }
        

    @abstractmethod
    def read_leads_from_sheet(self):
        pass


    @abstractmethod
    def find_lead_by_phone_number(self, lead_id):
        pass

    @abstractmethod
    def update_row_by_phone_number(self, phone_number, data):
        pass

    @abstractmethod
    def update_status_for_matching_rows(self, lead_id, data):
        pass


