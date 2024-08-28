import ollama
import bs4
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

def send_msg_to_llm(logs):

    prompt = f"""
    Analyze the following logs and provide a summary with identified issues and recommendations. Structure your response in JSON format with the following keys:
    - issues: A list of detected issues.
    - recommendations: Suggestions to resolve the issues.
    - summary: A brief summary of the overall log condition.
    
    Logs: {logs}
    """
    stream = ollama.chat(
        model='llama3.1',
        messages=[{'role': 'user', 'content': '{}'.format(prompt)}],
        stream=False,
    )
    return stream['message']['content']
    # for chunk in stream:
    #     print(chunk['message']['content'], end='', flush=True)


# loader = WebBaseLoader(
#     web_paths=("https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/",),
#     bs_kwargs=dict(
#         parse_only=bs4.SoupStrainer(
#             class_=("post-content", "post-title", "post-header")
#         )
#     ),
# )
# docs = loader.load()
# text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
# splits = text_splitter.split_documents(docs)
#
# # Create Ollama embeddings and vector store
# embeddings = OllamaEmbeddings(model="llama3.1")
# vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
#
# # Create the retriever
# retriever = vectorstore.as_retriever()
#
# def format_docs(docs):
#     return "\n\n".join(doc.page_content for doc in docs)
#
#
# def ollama_llm(question, context):
#     formatted_prompt = f"Question: {question}\n\nContext: {context}"
#     response = ollama.chat(model='llama3.1', messages=[{'role': 'user', 'content': formatted_prompt}])
#     return response['message']['content']
#
# def rag_chain(question):
#     retrieved_docs = retriever.invoke(question)
#     formatted_context = format_docs(retrieved_docs)
#     return ollama_llm(question, formatted_context)

