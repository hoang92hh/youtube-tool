# Reference Style Tool V1

Desktop Python tool:
Reference text + New topic -> OpenAI API -> Analysis -> Create -> Scene -> Structured JSON -> Excel.

## Requirements
- Python 3.11+
- OpenAI Python SDK
- tkinter (normally included with Windows Python)
- openpyxl

## Setup
1. Create an OpenAI API key.
2. Copy `.env.example` to `.env`.
3. Put the API key in `.env`.
4. Install dependencies:
   `pip install -r requirements.txt`
5. Run:
   `python main.py`

The application never sends an API key to the model. The key is used only by the OpenAI SDK.

## Important
This V1 is a local prototype. Do not distribute the `.env` file.
# youtube-tool
