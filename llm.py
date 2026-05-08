from langchain.chat_models import init_chat_model
from os import getenv
from dotenv import load_dotenv

from pydantic import SecretStr
import os
from langchain_openai import ChatOpenAI
load_dotenv()

api_key = os.getenv("INCEPTION_API_KEY")
if not api_key:
    raise ValueError("Missing required environment variable: INCEPTION_API_KEY must be set")


mercury = ChatOpenAI(
    model="mercury-2",
    temperature=0,
    api_key=SecretStr(api_key),
    base_url="https://api.inceptionlabs.ai/v1"
)

