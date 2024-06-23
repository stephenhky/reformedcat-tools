
import os
import json
import logging

import boto3
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings.gpt4all import GPT4AllEmbeddings
from langchain_aws.llms.bedrock import Bedrock
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from dotenv import load_dotenv


load_dotenv()


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=900,
    chunk_overlap=20,
    length_function=len
)


def get_bedrock_runtime(region_name, *args, **kwargs):
    return boto3.client(service_name='bedrock-runtime', region_name=region_name, *args, **kwargs)


def get_langchain_bedrock_llm(model_id, client, *args, **kwargs):
    return Bedrock(model_id=model_id, client=client, *args, **kwargs)


def lambda_handler(events, context):
    # get query
    logging.info(events)
    print(events)
    if isinstance(events['body'], dict):
        logging.info("dictionary")
        print("dictionary")
        query = events['body']
    else:
        logging.info("string")
        print("string")
        query = json.loads(events['body'])

    # get query question
    question = query['question']

    # retrieve config
    vectorstoredir = os.getenv('FAISS_CORPUS_DIR')
    embed_model_name = query.get('embed_model_name', 'all-MiniLM-L6-v2.gguf2.f16.gguf')
    llm_name = query.get('llm_name', 'mistral.mixtral-8x7b-instruct-v0:1')

    # getting an instance of LLM
    bedrock_runtime = get_bedrock_runtime('us-east-1')
    llm = get_langchain_bedrock_llm(llm_name, bedrock_runtime)

    # loading the embedding model
    embedding_model = GPT4AllEmbeddings(model_name=embed_model_name)

    # loading vector database
    db = FAISS.load_local(vectorstoredir, embedding_model, allow_dangerous_deserialization=True)
    retriever = db.as_retriever()

    # getting the chain
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type='stuff', retriever=retriever, return_source_documents=True)

    # get the results
    results = qa({'query': question})

    # return
    return {'statusCode': 200, 'body': results}
