import os
from openai import OpenAI

_client = None


def get_client():
    global _client
    if _client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("Chưa cấu hình OPENAI_API_KEY trong file .env")
        _client = OpenAI(api_key=key)
    return _client


def get_model():
    return os.getenv("OPENAI_MODEL", "gpt-5.6")


def response_text(instructions, input_text):
    client = get_client()
    response = client.responses.create(
        model=get_model(),
        instructions=instructions,
        input=input_text,
    )
    return response.output_text
