import logging
import os

# Loads .env file for API keys
from dotenv import load_dotenv

# OpenAI SDK
from openai import OpenAI

# Flask imports
from flask import Flask, request, jsonify

# Docling Imports
from docling.document_converter import DocumentConverter
from docling.datamodel.document import DoclingDocument

# Imports response formats for AI agents
from response_formats import LegalDocumentCheck, LegalSummaryData

_log = logging.getLogger(__name__)

# Set up logging to the console (optional, but useful to display logs on the terminal)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Show logs from INFO level and above
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
_log.addHandler(console_handler)

# Allows us to configure what OpenAI model we are using
MODEL = "gpt-4o-mini"

# Configuration for document parsing
MAX_PAGES = 20

# Initialize Flask app
app = Flask(__name__)


def parse_document(document_path: str) -> DoclingDocument:
    # Creates a docling document converter
    converter = DocumentConverter()

    # NOTE: We currently don't chunk the document because legal files should always be small enough.
    return converter.convert(document_path, max_num_pages=MAX_PAGES).document


def analyze_document(document: str) -> LegalSummaryData:
    # Sets up a client to call OpenAI API
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Prompts being sent the LLM backend
    messages = [
        {
            "role": "system",
            "content": "You are a helpful legal document interpreter.",
        },
        {
            "role": "developer",
            "content": "A user will attach a document containing a legal contract. Analyze its content.",
        },
        {
            "role": "user",
            "content": document,
        },
    ]

    # 1. Safety Check: Is the document provided a legal document?
    response_1 = client.beta.chat.completions.parse(
        model=MODEL, messages=messages, response_format=LegalDocumentCheck
    )

    legal_doc_check = response_1.choices[0].message.parsed

    # Checks if the document provided is a legal document
    #   valid_document - boolean: check if the model thinks its a legal document
    #   confidence_level - float: level of confidence between 0.0 - 1.0
    if (
        not legal_doc_check.valid_document
        or legal_doc_check.confidence_level < 0.8
    ):
        raise ValueError("Failed to identify as a legal document")

    # Appends this information to the current message prompt
    messages.append(
        {
            "role": "developer",
            "content": "Extract most important details from the user's document.",
        }
    )

    # 2. Request JSON object of important legal details
    response_2 = client.beta.chat.completions.parse(
        model=MODEL, messages=messages, response_format=LegalSummaryData
    )

    # This may needed to be tweaked to account for data the LLM can't find
    summary_data = response_2.choices[0].message.parsed

    return summary_data


@app.route('/analyze-legal-document', methods=['POST'])
def process_legal_document():
    try:
        # Sets up the log level
        _log.setLevel(level=logging.INFO)

        # Loads the .env variables
        load_dotenv()

        # Get the uploaded file from the request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Save the uploaded file temporarily
        temp_path = f"temp_{file.filename}"
        file.save(temp_path)

        # Process the document
        _log.info(f"Converting document at {temp_path}")
        document = parse_document(temp_path)
        markdown_text = document.export_to_markdown()

        # Clean up temporary file
        os.remove(temp_path)

        # Gives document to AI agent to analyze
        _log.info("AI agent is analyzing document...")
        summary_data = analyze_document(markdown_text)

        return jsonify({
            'success': True,
            'document_name': file.filename,
            'summary': summary_data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)