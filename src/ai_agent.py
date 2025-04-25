# ai_agent.py

import os
os.environ["USER_AGENT"] = "container-analyzer-ai-agent"
import time
import threading
from queue import Queue
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from typing import List, Optional

from kafka import KafkaConsumer
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings  # Open-source embeddings for retrieval (updated import)
from langchain_community.vectorstores import Chroma

from langchain_openai import ChatOpenAI  
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate

import docker

# 1. List of URLs for RAG
URLS = [
    "https://docs.docker.com/engine/reference/commandline/stop/",
    "https://docs.docker.com/config/containers/logs/",
    # Add more URLs as needed
]

# 2. Kafka setup
KAFKA_TOPIC = "container_logs"
KAFKA_BOOTSTRAP_SERVERS = ["localhost:9092"]

KAFKA_GROUP = "agent-group"

# 3. Docker
CONTAINER_NAME = "kafka"  # TODO: parse from logs if needed

# 4. OpenAI API
os.environ["OPENAI_API_KEY"] = "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"
# WARNING: If you see a model access error, your API key/project does not have access to the specified model.
# Change the model in the ChatOpenAI(...) constructor to one you have access to (e.g., "gpt-3.5-turbo").

# 5. LLM call interval
LLM_INTERVAL_SECONDS = 30

# ========== RAG SETUP ==========

# Load and split web docs
print("Fetching documentation from URLs...")
loader = WebBaseLoader(URLS)
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
doc_chunks = splitter.split_documents(docs)

# Initialize embeddings and vectorstore
# Hybrid RAG setup: local open-source embeddings for retrieval, OpenAI GPT for answers
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma.from_documents(doc_chunks, embeddings)
retriever = vectorstore.as_retriever()

# ========== DOCKER CLIENT ==========

docker_client = docker.from_env()

# ========== PYDANTIC SCHEMA ==========

class LogAnalysisPrompt(BaseModel):
    logs: List[str] = Field(..., description="A list of recent log lines from the container.")
    context: str = Field(..., description="Relevant Docker documentation for context.")

class LogAnalysisResponse(BaseModel):
    action: str = Field(..., description="One of: 'stop_container', 'no_action'")
    reason: str = Field(..., description="A concise explanation for the action.")
    summary: Optional[str] = Field(None, description="Optional high-level status summary.")

# ========== LLM SETUP ==========

# NOTE: You must use a valid OpenAI API key with access to the model you specify below.
llm = ChatOpenAI(temperature=0, model="gpt-4")  # Or "gpt-4" if you have access

# Helper function to get context from retriever
# This replaces the deprecated RetrievalQA chain

def get_context_from_retriever(query: str, retriever) -> str:
    # Use the new invoke() method to avoid deprecation warning
    docs = retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in docs)

# ========== KAFKA LOG BUFFER ==========



def consume_all_kafka_logs():
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id=KAFKA_GROUP
    )
    print("Kafka consumer started.")
    logs = []
    for msg in consumer:
        log_line = msg.value.decode("utf-8")
        logs.append(log_line)
        print(f"Received log: {log_line}")
        # Optional: break if you want to stop at a certain number of logs
        if len(logs) >= 5: break
    return logs

# ========== AGENT LOGIC ==========

# Strict output parsing using LangChain's PydanticOutputParser and chain.invoke
output_parser = PydanticOutputParser(pydantic_object=LogAnalysisResponse)

# Prompt template with explicit format instructions for the LLM
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert Docker monitoring agent. Use the following Docker docs as context: {context}"),
    ("human", (
        "Given these logs from a container:\n{logs}\n"
        "Analyze them and respond ONLY in the following JSON format:\n"
        "{format_instructions}\n"
        "If any memory_usage value in the logs is greater than 1024 (1MB, in bytes), your action should be 'stop_container' and your reason should be 'High memory usage detected.' Otherwise, use 'no_action'. Always use the numeric value from the memory_usage field in the logs."
    ))
])

def analyze_logs_with_llm(logs: List[str], context: str) -> LogAnalysisResponse:
    """
    Analyze logs using a strict, structured LLM chain. If the output cannot be parsed, raise an error or fallback safely.
    """
    chain_input = {
        "logs": "\n".join(logs),
        "context": context,
        "format_instructions": output_parser.get_format_instructions()
    }
    # Compose the chain: prompt -> llm -> output parser
    chain = prompt | llm | output_parser
    try:
        result = chain.invoke(chain_input)
        return result
    except Exception as e:
        print("Strict parsing failed:", e)
        # Optionally, log the error and return a safe default
        return LogAnalysisResponse(action="no_action", reason="Parsing error or unclear response.", summary=None)

def stop_container(container_name: str):
    try:
        container = docker_client.containers.get(container_name)
        container.stop()
        print(f"Container {container_name} stopped.")
    except Exception as e:
        print(f"Error stopping container: {e}")

def main():
    # Sequential: consume all available logs, then process
    logs = consume_all_kafka_logs()
    if logs:
        print(f"Total logs consumed: {len(logs)}")
        context = get_context_from_retriever(
            "What are the key things to check in container logs to decide if a container should be stopped?",
            retriever
        )
        analysis = analyze_logs_with_llm(logs, context)
        print("LLM Analysis:", analysis)
        if analysis.action == "stop_container":
            stop_container(CONTAINER_NAME)
        else:
            print(analysis.reason)
    else:
        print("No logs found in the topic.")

if __name__ == "__main__":
    main()