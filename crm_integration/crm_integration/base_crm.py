from abc import ABC, abstractmethod
import logging

logging.basicConfig(level=logging.INFO)


class BaseCRMClass(ABC):

    def __init__(self, crm_name=None):
        self.crm_name = crm_name
        self.connected = False


    # shared logic 1
    def connect(self):
        self.connected=True
        logging.info(f"{self.crm_name} connected")


    # shared logic 2
    def validate_payload(self,data):
        
        if not isinstance(data,dict):
            raise ValueError("Payload must be dictionary")

        if len(data)==0:
            raise ValueError("Payload empty")

        return True


    # shared logic 3
    def not_implemented(self,method):
        logging.info(
           f"{method} not implemented for {self.crm_name}"
        )
        return {
            "status":"not_implemented"
        }


    ##################################
    # abstract methods
    ##################################

    @abstractmethod
    def post_pre_sales_lead(self,data):
        pass


    @abstractmethod
    def list_pre_sales_leads(self):
        pass


    @abstractmethod
    def post_post_sales_lead(self,data):
        pass

    # -------------------------
    # PRE SALES LEADS
    # -------------------------

    @abstractmethod
    def list_pre_sales_leads(self):
        pass


    @abstractmethod
    def get_pre_sales_lead(self, lead_id):
        pass


    @abstractmethod
    def post_pre_sales_lead(self, data):
        pass


    @abstractmethod
    def patch_pre_sales_lead(self, lead_id, data):
        pass



    # -------------------------
    # POST SALES LEADS
    # -------------------------

    @abstractmethod
    def list_post_sales_leads(self):
        pass


    @abstractmethod
    def get_post_sales_lead(self, lead_id):
        pass


    @abstractmethod
    def post_post_sales_lead(self, data):
        pass


    @abstractmethod
    def patch_post_sales_lead(self, lead_id, data):
        pass



    # -------------------------
    # CUSTOMER
    # -------------------------

    @abstractmethod
    def list_customers(self):
        pass


    @abstractmethod
    def get_customer(self, customer_id):
        pass


    @abstractmethod
    def post_customer(self, data):
        pass


    @abstractmethod
    def patch_customer(self, customer_id, data):
        pass