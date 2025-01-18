import os
import asyncio
from pathlib import Path
import argparse
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

# Try to load from different possible .env locations
for env_file in ['.env.prod', '../.env.prod']:
    if Path(env_file).exists():
        load_dotenv(env_file)
        break

async def initialize_pinecone():
    """Initialize Pinecone connection"""
    api_key = os.environ.get('PINECONE_API_KEY')
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable is required")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    # Initialize Pinecone with new syntax
    pc = Pinecone(api_key=api_key)
    index_name = os.environ.get('PINECONE_INDEX_NAME', 'chatgenius')

    # Create index if it doesn't exist
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric='cosine',
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        print(f"Created new index: {index_name}")
    else:
        print(f"Using existing index: {index_name}")
    
    return PineconeVectorStore(
        index_name=index_name,
        embedding=OpenAIEmbeddings(openai_api_key=openai_api_key),
        text_key="text"
    )

async def process_text_file(file_path: Path) -> list:
    """Process a text file and split it into chunks"""
    print(f"Processing {file_path}...")
    
    # Load the text file
    loader = TextLoader(str(file_path))
    documents = loader.load()
    
    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,
        chunk_overlap=400,
        length_function=len,
        separators=["\n\n\n", "\n\n", "\n", ".", " ", ""]
    )
    
    split_docs = text_splitter.split_documents(documents)
    
    # Add metadata
    for doc in split_docs:
        doc.metadata.update({
            "source": str(file_path),
            "filename": file_path.name
        })
    
    return split_docs

async def main():
    parser = argparse.ArgumentParser(description='Load text file into Pinecone')
    parser.add_argument('file_path', type=str, help='Path to the text file')
    args = parser.parse_args()

    file_path = Path(args.file_path)
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")
    if file_path.suffix.lower() not in ['.txt', '.mb.txt']:
        raise ValueError("File must be a text file")

    # Initialize Pinecone
    vectorstore = await initialize_pinecone()
    
    try:
        # Process the text file
        documents = await process_text_file(file_path)
        print(f"Splitting text into {len(documents)} chunks...")
        
        # Add to Pinecone
        print("Adding documents to Pinecone...")
        await vectorstore.aadd_documents(documents)
        print(f"Successfully processed {file_path.name}")
        print(f"Added {len(documents)} text chunks to the knowledge base")
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 