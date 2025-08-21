# About: 
# This code evaluates the provided inputs using various evaluators.
# Supported evaluators - Similarity, Groundedness, Relevance. You can extend this script to include more.
# All evaluators are run on provided inputs, you can change this behaviour based on your requirements
# Supported authentication types to Azure OpenAI - Service Principal (Recommended) or key. See env template file.
# Tested on Python 3.11.0

# Imports
import os
import logging

from azure.identity import DefaultAzureCredential
from azure.ai.evaluation import SimilarityEvaluator, GroundednessEvaluator, RelevanceEvaluator 

from dotenv import load_dotenv

load_dotenv()

# Configure logging for DEBUG level info display
logging.basicConfig(level=logging.INFO)

# Set threshold that will pass / fail the evaluation
similarity_threshold = 3
relevance_threshold = 3
groundedness_threshold = 3

# Inputs / payload to be evaluated
inputs = {
"query" : 'Is Marie Curie born in Paris?',
"response" : 'According to wikipedia, Marie Curie was not born in Paris but in Warsaw.',
"ground_truth" : 'Marie Curie was born in Warsaw.',
"context" : 'Background: 1. Marie Curie is born on November 7, 1867. 2. Marie Curie is born in Warsaw.'
}

# Get environment variables
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

# Get if present otherwise None
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", None)

# These env. variables will be used to authenticate using Service Principal by DefaultAzureCredential
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZURE_AUTHORITY_HOST = os.getenv("AZURE_AUTHORITY_HOST")

model_config = {
            "azure_endpoint": AZURE_OPENAI_ENDPOINT,            
            "azure_deployment": AZURE_OPENAI_DEPLOYMENT_NAME,
            "api_version": AZURE_OPENAI_API_VERSION
            }

# Use key only when not using Service Principal
if AZURE_OPENAI_KEY: 
    model_config["api_key"] = AZURE_OPENAI_KEY
    logging.info("Using Azure OpenAI key for authentication.")

# Authentication using DefaultCredential (Service Principal) when not using key
if not AZURE_OPENAI_KEY:
    # Uses SP auth. with environment variables: https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential?view=azure-python)
    credential = DefaultAzureCredential()
    logging.info(f'** Please check the above log to confirm which identity is being used by DefaultAzureCredential (Service Principal client_id {AZURE_CLIENT_ID} is expected to be used) **')
    logging.info("Using DefaultAzureCredential for authentication.")


# Validate required inputs based on evaluator
def check_required_inputs(inputs_dict, required_keys = ["query", "response", "ground_truth", "context"]):
    missing_keys = [key for key in required_keys if key not in inputs]
    if missing_keys:
        logging.error(f"Missing required inputs for evaluation: {missing_keys}")
        return False
    return True

# Print inputs
logging.info(f"inputs: {inputs}")
print()
# Evaluators

# Run evaluation - Similarity
# https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/evaluation-evaluators/textual-similarity-evaluators#similarity
# Required inputs: query, response, ground_truth
if check_required_inputs(inputs, required_keys = ["query", "response", "ground_truth"]):
    similarity = SimilarityEvaluator(model_config=model_config, threshold=similarity_threshold)
    similarity_result = similarity(query=inputs["query"], response=inputs["response"], ground_truth=inputs["ground_truth"])
    # Get results - Similarity
    logging.info(f"Similarity result: {similarity_result}")
    print()
else:
    logging.error("Missing required inputs for similarity evaluation.")
    print()

# Run evaluation - Relevance
# https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/evaluation-evaluators/rag-evaluators#relevance
# Required inputs: query, response
if check_required_inputs(inputs, required_keys = ["query", "response"]):
    relevance = RelevanceEvaluator(model_config=model_config, threshold=relevance_threshold)
    relevance_result = relevance(query=inputs["query"], response=inputs["response"])
    # Get results - Relevance
    logging.info(f"Relevance result: {relevance_result}")
    print()
else:
    logging.error("Missing required inputs for relevance evaluation.")
    print()

# Run evaluation - Groundedness
# https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/evaluation-evaluators/rag-evaluators#groundedness
# Required inputs: query, context, response
if check_required_inputs(inputs, required_keys = ["query", "response", "context"]):
    groundedness = GroundednessEvaluator(model_config=model_config, threshold=groundedness_threshold)
    groundedness_result = groundedness(query=inputs["query"], response=inputs["response"], context=inputs["context"])
    # Get results - Groundedness
    print(f"Groundedness result: {groundedness_result}")
    print()
else:
    logging.error("Missing required inputs for groundedness evaluation.")
    print()