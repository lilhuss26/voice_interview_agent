from dotenv import load_dotenv
from pydantic import SecretStr
import os
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

load_dotenv()

mercury = ChatOpenAI(
    model="mercury-2",
    temperature=0,
    api_key=SecretStr(os.getenv("INCEPTION_API_KEY")),
    base_url="https://api.inceptionlabs.ai/v1"
)

haiku = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0,
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

