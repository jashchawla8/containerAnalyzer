# ai_agent_splitter_character_retriever_chroma.py
# Uses CharacterTextSplitter and Chroma retriever
import os
import time
from typing import List, Optional
from kafka import KafkaConsumer
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
import docker

URLS = [
    "https://docs.docker.com/config/containers/logs/",
]
KAFKA_TOPIC = "container_logs"
KAFKA_BOOTSTRAP_SERVERS = ["localhost:9092"]
KAFKA_GROUP = "agent-group"
CONTAINER_NAME = "kafka"
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
LLM_INTERVAL_SECONDS = 30

print("Fetching documentation from URLs...")
loader = WebBaseLoader(URLS)
docs = loader.load()
splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
doc_chunks = splitter.split_documents(docs)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma.from_documents(doc_chunks, embeddings)
retriever = vectorstore.as_retriever()

docker_client = docker.from_env()

class LogAnalysisPrompt(BaseModel):
    logs: List[str] = Field(..., description="A list of recent log lines from the container.")
    context: str = Field(..., description="Relevant Docker documentation for context.")
class LogAnalysisResponse(BaseModel):
    action: str = Field(..., description="One of: 'stop_container', 'no_action'")
    reason: str = Field(..., description="A concise explanation for the action.")
    summary: Optional[str] = Field(None, description="Optional high-level status summary.")

output_parser = PydanticOutputParser(pydantic_object=LogAnalysisResponse)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert Docker monitoring agent. Use the following Docker docs as context: {context}"),
    ("human", (
        "Given these logs from a container:\n{logs}\n"
        "Analyze them and respond ONLY in the following JSON format:\n"
        "{format_instructions}\n"
        "If any memory_usage value in the logs is greater than 1024 (1MB, in bytes), your action should be 'stop_container' and your reason should be 'High memory usage detected.' Otherwise, use 'no_action'. Always use the numeric value from the memory_usage field in the logs."
    ))
])
llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
def get_context_from_retriever(query: str, retriever) -> str:
    docs = retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in docs)
def stop_container(container_name: str):
    try:
        container = docker_client.containers.get(container_name)
        container.stop()
        print(f"Container {container_name} stopped.")
    except Exception as e:
        print(f"Error stopping container: {e}")
def analyze_logs_with_llm(logs: List[str], context: str) -> LogAnalysisResponse:
    chain_input = {
        "logs": "\n".join(logs),
        "context": context,
        "format_instructions": output_parser.get_format_instructions()
    }
    chain = prompt | llm | output_parser
    try:
        result = chain.invoke(chain_input)
        return result
    except Exception as e:
        print("Strict parsing failed:", e)
        return LogAnalysisResponse(action="no_action", reason="Parsing error or unclear response.", summary=None)
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
        if len(logs) >= 5: break
    return logs
def main():
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
