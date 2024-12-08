import os
import json
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
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

# Directory to save response files
output_directory = os.path.abspath("output_files")
os.makedirs(output_directory, exist_ok=True)

# System prompt for the chatbot
system_template = """As a highly qualified Legal Advisor specializing in Indian law, your role is to provide expert, accurate, and comprehensive responses to legal inquiries. Utilize your extensive knowledge of Indian jurisprudence, including statutes, case law, and legal principles to formulate your answers. When responding:
1. Conduct a thorough analysis of the query to identify key legal issues and relevant areas of law.
2. Provide clear, concise explanations of applicable laws, acts, and legal concepts, citing specific sections where appropriate.
3. Reference relevant case precedents and judicial pronouncements, including citations and brief summaries of their significance.
4. Offer insights into potential legal strategies or courses of action, considering both short-term and long-term implications.
5. Explain the practical applications of the law in the context of the query, including any potential challenges or considerations.
6. Highlight any ambiguities, areas of legal debate, or recent developments in the law that may impact the situation.
7. Where applicable, mention any relevant statutes of limitations or procedural requirements.
8. Conclude with a succinct summary of key points, critical information, and recommended next steps if appropriate."""

# Helper function to fetch the top document's context
def fetch_indian_kanoon_context(query):
    try:
        # Step 1: Fetch the search response
        search_url = "https://api.indiankanoon.org/search/"
        search_params = {"formInput": query, "filter": "on", "pagenum": 1}
        headers = {"Authorization": f"Token {indian_kanoon_api_key}"}

        search_response = requests.post(search_url, params=search_params, headers=headers)
        search_response.raise_for_status()
        search_data = search_response.json()

        # Save search_response.json
        search_file_path = os.path.join(output_directory, "search_response.json")
        with open(search_file_path, "w") as file:
            json.dump(search_data, file, indent=4)
        print(f"Search response saved to: {search_file_path}")

        # Get the first document's ID (tid)
        docs = search_data.get("docs", [])
        if not docs:
            return "No relevant documents found in Indian Kanoon."
        docid = docs[0].get("tid")

        # Step 2: Fetch the document context
        context_url = f"https://api.indiankanoon.org/doc/{docid}/"
        context_response = requests.post(context_url, headers=headers)
        context_response.raise_for_status()
        context_data = context_response.json()

        # Save response_context.json
        context_file_path = os.path.join(output_directory, "response_context.json")
        with open(context_file_path, "w") as file:
            json.dump(context_data, file, indent=4)
        print(f"Context response saved to: {context_file_path}")

        return context_data.get("content", "No content found in the document context.")
    except requests.exceptions.RequestException as e:
        print(f"Error with Indian Kanoon API: {e}")
        return f"Error fetching Indian Kanoon context: {e}"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Error fetching Indian Kanoon context: {e}"

@app.route("/")
def index():
    return render_template("index.html")
@app.route("/ai-help")
def ai_help():
    return render_template('feature.html')
@app.route("/chat", methods=["POST"])
def chatbot_response():
    query = request.json.get("query", "")
    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        kanoon_context = fetch_indian_kanoon_context(query)
        messages = [
            {"role": "system", "content": system_template},
            {"role": "user", "content": f"Query: {query}\n\nIndian Kanoon Context: {kanoon_context}"}
        ]
        completion = client.chat.completions.create(
            model="meta-llama/Llama-3.2-3B-Instruct",
            messages=messages,
            max_tokens=1500
        )
        response_content = completion.choices[0].message["content"]
        return jsonify({"query": query, "response": response_content})
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"error": f"Error processing query: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
