# Ref: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview?pivots=programming-language-python
# Ref: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/trace-application
# Ref: https://github.com/Azure-Samples/get-started-with-ai-agents/blob/main/src/api/routes.py#L296

# Azure Monitor OpenTelemetry distro samples
# Ref: https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/monitor/azure-monitor-opentelemetry/samples

from logging import INFO, Formatter, getLogger
import os

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

from dotenv import load_dotenv

load_dotenv()

OpenAIInstrumentor().instrument()

tracer = trace.get_tracer(__name__)

# APP_INSIGHTS_CONNECTION_STRING = os.getenv("APP_INSIGHTS_CONNECTION_STRING")
AI_FOUNDRY_PROJECT_ENDPOINT = os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# if not APP_INSIGHTS_CONNECTION_STRING:
#     raise ValueError("APP_INSIGHTS_CONNECTION_STRING environment variable is not set.")
if not AI_FOUNDRY_PROJECT_ENDPOINT:
    raise ValueError("AI_FOUNDRY_PROJECT_ENDPOINT environment variable is not set.")
if not AZURE_OPENAI_DEPLOYMENT_NAME:
    raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME environment variable is not set.")

# Create an AIProjectClient instance to interact with the AI Foundry project
project_client = AIProjectClient(
  endpoint=AI_FOUNDRY_PROJECT_ENDPOINT, 
  credential=DefaultAzureCredential())

# Configure OpenTelemetry to send traces to the Azure Application Insights
configure_azure_monitor(connection_string=project_client.telemetry.get_application_insights_connection_string(),
                        # logger_name='my_app_logger'
                        )

# # Logging telemetry will be collected from logging calls made with this logger and all of it's children loggers.
# logger = getLogger("my_app_logger")
# logger.setLevel(INFO)

# print("List all deployments:")
# for deployment in project_client.deployments.list():
#     print(deployment)

# Get the OpenAI client from the AIProjectClient instance
azure_openai_client = project_client.get_openai_client(api_version='2024-10-21')

# from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
# carrier = {}        
# TraceContextTextMapPropagator().inject(carrier)
# ctx = TraceContextTextMapPropagator().extract(carrier=carrier)

@tracer.start_as_current_span("approve_loan_application")
def approve_loan_application(applicant_name: str, credit_score: int) -> bool:

    # logger.info(f"info log applicant_name:{applicant_name}, credit_score:{credit_score}")

    with trace.get_current_span() as span:
    # with tracer.start_as_current_span('approve_loan_application', context=ctx):

        span.set_attribute("applicant_name", applicant_name)
        span.set_attribute("credit_score", credit_score)
        # logging.info(f'applicant_name:{applicant_name}')
        # logging.info(f'credit_score:{credit_score}')

        response = azure_openai_client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=[
            {"role": "user", "content": f"Write one line summary of loan application from {applicant_name} with credit score {credit_score}."},
        ],
        temperature=0.0,
        max_tokens=50)

        # print(f'response: {response.choices[0].message.content}')
        span.set_attribute("applicant_summary", response.choices[0].message.content)

        if credit_score >= 700:
            span.set_attribute("approval_status", "approved")
            return True
        else:
            span.set_attribute("approval_status", "denied")
            return False

if __name__ == "__main__":
    applicant = "John Doe"
    score = 720
    is_approved = approve_loan_application(applicant, score)
    print(f"Loan application for {applicant} with credit score {score} approved: {is_approved}")

    applicant_2 = "Jane Smith"
    score_2 = 650
    is_approved_2 = approve_loan_application(applicant_2, score_2)
    print(f"Loan application for {applicant_2} with credit score {score_2} approved: {is_approved_2}")