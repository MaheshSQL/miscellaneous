import logging

import azure.functions as func

import os
import openai
from langchain.llms.openai import AzureOpenAI

from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.agents import AgentExecutor
from langchain.agents.agent_types import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.chat_models.azure_openai import AzureChatOpenAI

def getAZSQLConnStr():

    return "mssql+pyodbc://"+os.environ.get("AZ_SQL_USR")+":"+os.environ.get("AZ_SQL_PWD")+"@"+os.environ.get("AZ_SQL_SRV")+".database.windows.net:1433/"+os.environ.get("AZ_SQL_DB")+"?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=no&Encrypt=yes"    

def getExecutor():

    deployment_name=os.environ.get("OPENAI_DEPLOYMENT_NAME")
    max_tokens = os.environ.get("OPENAI_MAX_TOKENS")
    temperature = os.environ.get("OPENAI_TEMPERATURE")  
    openai_api_version=os.environ.get("OPENAI_API_VERSION")  
    
    db = SQLDatabase.from_uri(getAZSQLConnStr())
    
    toolkit = SQLDatabaseToolkit(db=db, llm=AzureChatOpenAI(openai_api_version=openai_api_version,deployment_name=deployment_name,temperature=0))
    logging.info('Toolkit initialised.')

    agent_executor = create_sql_agent(    
        llm=AzureChatOpenAI(openai_api_version=openai_api_version,deployment_name=deployment_name,
                        temperature=temperature,max_tokens=max_tokens), 
                        toolkit=toolkit,
                        verbose=True,
                        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                        # prefix = 'You are an agent designed to interact with a SQL database.\nGiven an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer without using "`" in prefix.\nUnless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.\nYou can order the results by a relevant column to return the most interesting examples in the database.\nNever query for all the columns from a specific table, only ask for the relevant columns given the question.\nYou have access to tools for interacting with the database.\nOnly use the below tools. Only use the information returned by the below tools to construct your final answer.\nYou MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.\n\nDO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.\n\nIf the question does not seem related to the database, just return "I don\'t know" as the answer.\n Never include "`" character in the answer. Return both final answer and SQL query as a JSON object.', 
                        # # suffix = None, 
                        # # format_instructions = 'Use the following format:\n\nQuestion: the input question you must answer\nThought: you should always think about what to do\nAction: the action to take, should be one of [{tool_names}]\nAction Input: the input to the action\nObservation: the result of the action\n... (this Thought/Action/Action Input/Observation can repeat N times)\nThought: I now know the final answer (this final answer "sentence" and "last SQL query" in a JSON format, never include "`" character in final output)',
                        # return_intermediate_steps=True
                        )    

    agent_executor.return_intermediate_steps = True
    agent_executor.handle_parsing_errors = True

    return agent_executor

def main(req: func.HttpRequest) -> func.HttpResponse:

    try:

        logging.info('Python HTTP trigger function started processing a request.')

        req_body = req.get_json()
        logging.info(f'req_body:{req_body}')
        question = req_body.get('question')
        logging.info(f'question:{question}')    
        agent_executor = getExecutor()
        logging.info('Starting executor.')
        response = agent_executor(inputs= {"input": question})
        logging.info('Completed executor.')
        logging.info(response)
        # print(json.dumps(response["intermediate_steps"], indent=2))  
        logging.info('Python HTTP trigger function completed processing a request.')          

        return func.HttpResponse(str(response), status_code=200)
    
    except Exception as e:
        logging.error(str(e))
        return func.HttpResponse(str(e), status_code=500)