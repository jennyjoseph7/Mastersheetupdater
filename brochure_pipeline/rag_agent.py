import rag_agent
from ai_service import ai_service
from bp_utils import GRYD_SERVICE, get_logger
import json
import ast

logger = get_logger(__name__)

class RAGAgentWrapper:
    def __init__(self, vec_db_identifier=None, collection_name=None, rag_agent=None):
        """
        Initialize the wrapper with the RAG agent instance.
        :param rag_agent: The underlying RAG agent to be wrapped.
        """
        self.vec_db_identifier=vec_db_identifier if vec_db_identifier else "qdrant-test-databricks-qwen-qwen3-0.6b"
        self.rag_agent = rag_agent
        self.collection_name = collection_name

    def fix_filters(self,filters):
        pass
    def get_answer(self, filters, question,n_result=15):
        """
        Answer questions about specific vehicle models.
        :param model_name: Name of the vehicle model.
        :param question: The question to be answered.
        :return: Answer from the RAG agent.
        """

        with open("prompt/rag_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()

        with open("prompt/final_prompt_rag.txt", "r", encoding="utf-8") as f:
            system_prompt_rag = f.read().strip()


        messages=[
            {"role": "user", "content": f""" 
             This is user question:{question}
             Follow the intructions to answer the user question
            """},
            {"role": "system", "content": system_prompt}
        ]

        ai_agent=ai_service.get_llm_response(
            messages=messages,
            model_identifier="gcp-gemini-2.5-flash"
        )
        logger.info(f"Raw LLM Response: {ai_agent[:500]}...")
        fetched_data = ast.literal_eval(ai_agent)
        
        filters=fetched_data.get("filters",None)
        intent=fetched_data.get("intent","")
        language=fetched_data.get("language","en")
        logger.info(f"Extracted filters: {filters}, intent: {intent}, language: {language}")
        
        if filters:
            fixed_filter=self.fix_filters(filters)
        else:
            fixed_filter=None

        output=rag_agent.doc_search(
            query=question,
            vec_db_identifier=self.vec_db_identifier,
            collection_name=self.collection_name,
            filters=fixed_filter,
            n_result=n_result,
            is_debug=True
        )




        messages=[
            {"role": "user", "content": f""" 
             This is user question:{question},
             This is the filters:{intent}
             Follow the intructions to answer the user question
            """},
            {"role": "system", "content": system_prompt_rag}
        ]
        ai_agent=ai_service.get_llm_response(
            messages=messages,
            model_identifier="gcp-gemini-2.5-flash"
        )
        return ai_agent



