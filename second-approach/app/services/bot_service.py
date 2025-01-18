import os
import logging
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import Document
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import ChatPromptTemplate
from pinecone import Pinecone
from openai import OpenAI

logger = logging.getLogger(__name__)

class BotService:
    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        pinecone_api_key = os.environ.get('PINECONE_API_KEY')
        index_name = os.environ.get('PINECONE_INDEX_NAME', 'chatgenius')

        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not pinecone_api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required")

        logger.info(f"Initializing BotService with index: {index_name}")

        # Initialize Pinecone with new syntax
        pc = Pinecone(api_key=pinecone_api_key)
        
        # Initialize components
        self.embeddings = OpenAIEmbeddings(api_key=api_key)
        self.vectorstore = PineconeVectorStore(
            index=pc.Index(index_name),
            embedding=self.embeddings,
            text_key="text"
        )
        
        self.chat = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.7,
            api_key=api_key
        )
        
        self.system_prompt = """You are a helpful AI assistant with access to a knowledge base about the Peloponnesian War by Thucydides. 
        Use the provided context to answer questions accurately.
        Be concise and clear in your responses.
        If you're not sure about something or if the context doesn't help, say so.
        If a question is unclear, ask for clarification.
        Always cite specific events, battles, or quotes from the text when possible."""

        self.rag_prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("system", "Context information is below:\n{context}"),
            ("human", "{question}")
        ])

    async def get_response(self, message_content: str) -> str:
        """Get a response from the LangChain chat model with RAG"""
        try:
            logger.info(f"Processing question: {message_content}")
            
            # Search for relevant documents
            docs = await self.vectorstore.asimilarity_search_with_score(message_content, k=3)
            logger.info(f"Found {len(docs)} relevant documents")
            
            # Extract just the documents without scores
            docs_only = [doc[0] for doc in docs]
            context = "\n".join(doc.page_content for doc in docs_only)
            logger.debug(f"Retrieved context: {context[:200]}...")  # Log first 200 chars of context
            
            # Create messages with context
            prompt_value = await self.rag_prompt.ainvoke({
                "context": context,
                "question": message_content
            })
            
            response = await self.chat.ainvoke(prompt_value)
            logger.info("Generated response successfully")
            return response.content
            
        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error while processing your question. Please try again."

# Create a singleton instance
bot_service = BotService() 