import os, sys
try:
    from .base_agent import BaseAgent, gryd
except ImportError:
    from base_agent import BaseAgent, gryd 

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from autocrm_db_helper.PGConnector import AutoCRMPGConnector
pg = AutoCRMPGConnector(enterprise_id="autocrm")
mlogger = gryd.hp.get_logger(gryd.SERVICE)

class data_attribute_retriever(BaseAgent):
    """This agent collects the data of the campaign uploaded by the dealership for the particular campaign based on campaign id from pre and post sales lead model and will give all the distinct types of attribute list"""

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        
        # Validate source
        if not source or not isinstance(source, dict):
            raise ValueError("source must be a non-empty dictionary")
        
        self.source = source
        self.id = source.get("id")
        self.campaign_type = source.get("campaign_type","")
        self.campaign_objective_id = source.get("campaign_objective_id")
        

    def get_data_from_model(self):
        logger = mlogger

        records = []  # ensure variable always exists


        if self.id is not None and self.campaign_type in ["pre-sale","pre-sales", "pre_sale", "pre_sales"]:
            try:
                records = list(pg.list(
                    table_name="pre_sales_lead",
                    where={"pre_sales_lead_id": self.id}
                ))
            except Exception as e:
                raise ValueError(f"Could not retrieve data from the pre sales lead model: {e}")
            
        elif self.campaign_objective_id is not None and self.campaign_type in ["pre-sale","pre-sales", "pre_sale", "pre_sales"]:
            try:
                records = list(pg.list(
                    table_name="pre_sales_lead",
                    where={"campaign_objective_id": self.campaign_objective_id}
                ))
            except Exception as e:
                raise ValueError(f"Could not retrieve data from the pre sales lead model: {e}")

        elif self.id is not None and self.campaign_type in ["post-sales", "post_sale", "post_sales"]:
            try:
                records = list(pg.list(
                    table_name="post_sales_lead",
                    where={"post_sales_lead_id": self.id}
                ))
            except Exception as e:
                raise ValueError(f"Could not retrieve data from the post sales lead model: {e}")
            
        elif self.campaign_objective_id is not None and self.campaign_type in ["post-sales", "post_sale", "post_sales"]:
            try:
                records = list(pg.list(
                    table_name="post_sales_lead",
                    where={"campaign_objective_id": self.campaign_objective_id}
                ))
            except Exception as e:
                raise ValueError(f"Could not retrieve data from the post sales lead model: {e}")

        else:
            raise ValueError(f"Invalid campaign_type: {self.campaign_type}")

        if not records:
            raise logger.info("No records found for given ID and campaign type.")

        return records

    
    
    def get_data_attributes(self, records:list):
        seen = set()
        distinct_sets = []

        for record in records:
            # Start with top-level keys
            attrs = set(record.keys())

            #Add person_name if inside persons_involved
            persons = record.get("persons_involved", [])
            if isinstance(persons, list):
                for person in persons:
                    if isinstance(person, dict) and "person_name" in person:
                        attrs.add("person_name")
                        break

            # Convert to sorted tuple for uniqueness
            attrs_tuple = tuple(sorted(attrs))

            if attrs_tuple not in seen:
                seen.add(attrs_tuple)
                distinct_sets.append(list(attrs_tuple))

        return distinct_sets

    
    def remove_unwanted_attributes(self, distinct_sets):
        """
        Removes attributes that:
        - contain 'id' (case insensitive), e.g., 'vehicle_id', 'UserId', 'lead_id'
        - OR appear in CUSTOM_REMOVABLE_ATTRIBUTES list
        """
        if self.campaign_type in ["pre-sales", "pre_sale", "pre_sales"]:
            CUSTOM_REMOVABLE_ATTRIBUTES = [
                'post_sales_lead',
                'region_name',
                'region_level_guardrails',
                'dealer_group_name',
                'dealer_group_guidelines',
                'dealer_group_description',
                'dealership_guidelines',
                'dealership_guardrails',
                'dealership_description',
                'supported_brands',
                'supported_brand_names',
                'supported_brands_guidelines',
                'campaign_type',
                'campaign_sub_type',
                'campaign_description',
                'campaign_objective_name',
                'campaign_objective_description',
                'campaign_objective_type',
                'conversation_tone',
                'custom_attributes',
                'campaign_guardrails_guidelines',
                'reasons_users_may_not_be_interested',
                'reasons_for_non_applicability',
                'other_important_information',
                'ctas',
                'lead_tags',
                'service_history',
                'service_advisor',
                'service_frequency',
                'service_feedback',
                'feedback_rating',
                'feedback_sentiment_score',
                'tyre_change_details',
                'repair_notes',
                'vehicle_persona_summary',
                'finance_loan_status',
                'ownership_status',
                'persons_involved',
                'customer_score',
                'workshop_full_name',
                'workshop_type',
                'workshop_email',
                'workshop_address',
                'workshop_geolocation',
                'workshop_operating_hours',
                'workshop_days_open',
                'workshop_facilities_available',
                'workshop_services_offered',
                'workshop_level_guidelines',
                'workshop_level_guardrails',
                'last_session_status',
                'last_session_date',
                'prioritization_score',
                'prioritization_category',
                'disposition',
                'disposition_detail',
                'lead_summary',
                'scheduled_timestamp',
                'created',
                'updated',
                'campaign_name',
                'vin_number',
                
            ]

        elif self.campaign_type in ["post-sales", "post_sale", "post_sales"]:
            CUSTOM_REMOVABLE_ATTRIBUTES = [
                'post_sales_lead',
                'region_name',
                'region_level_guidelines',
                'region_level_guardrails',
                'dealer_group_name',
                'dealer_group_guidelines',
                'dealer_group_description',
                'dealership_guidelines',
                'dealership_guardrails',
                'dealership_description',
                'supported_brands',
                'supported_brand_names',
                'supported_brands_guidelines',
                'campaign_type',
                'campaign_sub_type',
                'campaign_description',
                'campaign_objective_name',
                'campaign_objective_description',
                'campaign_objective_type',
                'conversation_tone',
                'custom_attributes',
                'campaign_guardrails_guidelines',
                'reasons_users_may_not_be_interested',
                'reasons_for_non_applicability',
                'other_important_information',
                'ctas',
                'lead_tags',
                'service_history',
                'service_advisor',
                'service_frequency',
                'service_feedback',
                'feedback_rating',
                'feedback_sentiment_score',
                'tyre_change_details',
                'repair_notes',
                'vehicle_persona_summary',
                'finance_loan_status',
                'ownership_status',
                'persons_involved',
                'customer_score',
                'workshop_full_name',
                'workshop_type',
                'workshop_email',
                'workshop_address',
                'workshop_geolocation',
                'workshop_operating_hours',
                'workshop_days_open',
                'workshop_facilities_available',
                'workshop_services_offered',
                'workshop_level_guidelines',
                'workshop_level_guardrails',
                'last_session_status',
                'last_session_date',
                'prioritization_score',
                'prioritization_category',
                'disposition',
                'disposition_detail',
                'lead_summary',
                'scheduled_timestamp',
                'created',
                'updated',
                'campaign_name',
                'vin_number',
            ]

        cleaned_sets = []
        for attrs in distinct_sets:
            new_attr_list = []
            for attr in attrs:
                # Remove fields containing 'id'
                if "_id" in attr.lower():
                    continue
                # Remove custom unwanted fields
                if attr in CUSTOM_REMOVABLE_ATTRIBUTES:
                    continue
                new_attr_list.append(attr)
            cleaned_sets.append(new_attr_list)
        return cleaned_sets
        

    def run(self):

        records = self.get_data_from_model()
        distinct_sets = self.get_data_attributes(records)
        distinct_sets = self.remove_unwanted_attributes(distinct_sets)

        return distinct_sets


@gryd.is_a_task('get_customer_data', logger_param='logger', job_param='job')
def get_customer_data(campaign_data = None, id=None,campaign_type=None, logger=None,job=None):
    logger = logger or gryd.hp.get_logger(__name__)
    logger.info("Getting customer data...")


    try:

        campaign_data = campaign_data or {}
        updates = {
            "id": id,
            "campaign_type": campaign_type
        }

        for key, val in updates.items():
            if val is not None:
                campaign_data[key] = val
        
        agent = data_attribute_retriever(source=campaign_data, logger=logger)
        result = agent.run()
        return result

    except Exception as e:
        logger.error(f"Data retrieval failed {str(e)}")
        raise