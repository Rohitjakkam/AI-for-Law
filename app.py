from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
from werkzeug.utils import secure_filename
import PyPDF2
import docx
import tempfile
from huggingface_hub import InferenceClient

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()

# API keys
hf_api_key = os.getenv("HF_API_KEY")
indian_kanoon_api_key = os.getenv("INDIAN_KANOON_API_KEY")

# Initialize Hugging Face Inference Client
client = InferenceClient(api_key=hf_api_key)

# System prompt for the chatbot
system_template = """You are a highly experienced Legal Advisor specializing in Indian law. Your role is to assist lawyers, judges, and law students by providing detailed, accurate, and actionable insights into legal queries. When responding:

1. **Identify Core Legal Issues**: Analyze the query to pinpoint the fundamental legal matters.
2. **Legal Analysis**: Elaborate on the laws, sections, acts, or principles applicable, citing the exact legal provisions and their relevance to the query.
3. **Case Precedents**: Reference up-to-date case laws, their citations, and summarize their significance in resolving similar issues.
4. **Time-Saving Strategies**: Offer clear and concise insights that help the user save time in legal research.
5. **Practical Guidance**: Highlight practical steps, procedural requirements, or key considerations relevant to the situation.
6. **Ambiguities or Challenges**: Address any areas of uncertainty in the law or recent developments impacting the issue.
7. **Next Steps**: Conclude with clear, actionable recommendations to advance the legal research or case preparation.

Your responses should prioritize precision, comprehensiveness, and brevity to maximize efficiency for legal professionals and students. Use plain, professional language to ensure understanding across varied expertise levels.
"""

# Allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to extract text from files
def extract_text_from_file(file, filename):
    try:
        file_extension = filename.rsplit('.', 1)[1].lower()
        if file_extension == 'pdf':
            pdf_reader = PyPDF2.PdfReader(file)
            text = "".join([page.extract_text() for page in pdf_reader.pages])
        elif file_extension in ['doc', 'docx']:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
                temp_file.write(file.read())
                temp_file.close()
                doc = docx.Document(temp_file.name)
                text = "\n".join([para.text for para in doc.paragraphs])
            os.unlink(temp_file.name)
        elif file_extension == 'txt':
            text = file.read().decode('utf-8')
        else:
            raise ValueError("Unsupported file format")
        return text
    except Exception as e:
        raise ValueError(f"Error while extracting text: {e}")

# Helper function to fetch legal information from Indian Kanoon
def fetch_indian_kanoon_info(query):
    try:
        url = "https://api.indiankanoon.org/search/"
        params = {"formInput": query, "filter": "on", "pagenum": 1}
        headers = {"Authorization": f"Token {indian_kanoon_api_key}"}
        response = requests.post(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            detailed_info = []
            for doc in data.get('docs', [])[:3]:
                tid = doc.get('tid')
                title = doc.get('title', '')
                snippet = doc.get('snippet', '')
                # Add metadata and fragments if available
                docmeta_url = f"https://api.indiankanoon.org/docmeta/{tid}/"
                meta_response = requests.post(docmeta_url, headers=headers)
                metadata = meta_response.json() if meta_response.status_code == 200 else {}
                detailed_info.append({
                    "Title": title,
                    "Snippet": snippet,
                    "Metadata": metadata
                })
            return detailed_info
        else:
            return f"Error: {response.status_code} {response.text}"
    except Exception as e:
        return f"Error fetching Indian Kanoon info: {e}"

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/ai-help")
def ai_help():
    return render_template('feature.html')

@app.route("/chat", methods=["POST"])
def chatbot_response():
    query = request.json.get("query", "")
    if not query:
        return jsonify({"error": "Query is required"}), 400
    try:
        kanoon_info = fetch_indian_kanoon_info(query)
        messages = [
            {"role": "system", "content": system_template},
            {"role": "user", "content": f"Query: {query}\n\nAnalyze the following query and provide actionable insights:\n{kanoon_info}"}
        ]

        completion = client.chat.completions.create(
            model="meta-llama/Llama-3.2-3B-Instruct",
            messages=messages,
            max_tokens=1500
        )
        response_content = completion["choices"][0]["message"]["content"]
        return jsonify({"query": query, "response": response_content})
    except Exception as e:
        return jsonify({"error": f"Error processing query: {e}"}), 500

@app.route("/analyze", methods=["POST"])
def analyze_document():
    file = request.files.get("file")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid or missing file"}), 400
    filename = secure_filename(file.filename)
    try:
        document_text = extract_text_from_file(file, filename)
        kanoon_info = fetch_indian_kanoon_info(document_text[:500])
        analysis_prompt = f"""Analyze the following legal document to provide a structured summary:

        Document Content:
        {document_text}

        Relevant Indian Kanoon Information:
        {kanoon_info}
        """

        messages = [
            {"role": "system", "content": system_template},
            {"role": "user", "content": analysis_prompt}
        ]
        completion = client.chat.completions.create(
            model="meta-llama/Llama-3.2-3B-Instruct",
            messages=messages,
            max_tokens=1500
        )
        analysis_content = completion["choices"][0]["message"]["content"]
        return jsonify({"analysis": analysis_content})
    except Exception as e:
        return jsonify({"error": f"Error analyzing document: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
