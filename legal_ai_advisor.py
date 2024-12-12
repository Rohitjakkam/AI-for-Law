import os
import json
import requests
import tempfile
import PyPDF2
import docx
import streamlit as st
import logging
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()

# API keys
hf_api_key = os.getenv("HF_API_KEY")
indian_kanoon_api_key = os.getenv("INDIAN_KANOON_API_KEY")

# Initialize Hugging Face Inference Client
client = InferenceClient(api_key=hf_api_key)

# System prompt for the chatbot
SYSTEM_PROMPT = (
    """As a highly qualified Legal Advisor specializing in Indian law, your role is to provide expert, accurate, and comprehensive 
    responses to legal inquiries...."""  # Truncated for brevity
)

# Helper function to extract text from files
def extract_text_from_file(file, filename):
    logging.info("Extracting text from file...")
    try:
        file_extension = filename.rsplit('.', 1)[-1].lower()
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
        logging.info("Text extraction successful.")
        return text
    except Exception as e:
        logging.error(f"Error extracting text: {e}")
        raise ValueError(f"Error extracting text: {e}")

# Helper function to fetch legal information from Indian Kanoon
def fetch_indian_kanoon_info(query):
    logging.info(f"Fetching Indian Kanoon info for query: {query[:100]}...")
    try:
        url = "https://api.indiankanoon.org/search/"
        params = {"formInput": query, "filter": "on", "pagenum": 1}
        headers = {"Authorization": f"Token {indian_kanoon_api_key}"}
        response = requests.post(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            relevant_info = [
                f"Title: {doc.get('title', '')}\nSnippet: {doc.get('snippet', '')}\n"
                for doc in data.get('docs', [])[:1]
            ]
            logging.info("Fetched Indian Kanoon data successfully.")
            return "\n".join(relevant_info)
        else:
            logging.warning("Failed to fetch Indian Kanoon data. Non-200 response.")
            return "Unable to fetch information from Indian Kanoon API."
    except Exception as e:
        logging.error(f"Error fetching Indian Kanoon info: {e}")
        return f"Error fetching Indian Kanoon info: {e}"

# Streamlit app
def main():
    st.title("KanoonSetu")
    st.sidebar.title("Features")
    logging.info("Application started.")

    # Feature selection
    feature = st.sidebar.radio("Select a feature:", ("Text Input", "Document Upload"))
    logging.info(f"Selected feature: {feature}")

    if feature == "Text Input":
        st.header("Chat with Legal AI Based on Relevant Cases")
        user_query = st.text_area("Enter your legal query:")
        if st.button("Get Response"):
            if not user_query.strip():
                st.error("Please enter a query.")
            else:
                try:
                    # Fetch Indian Kanoon context
                    kanoon_context = fetch_indian_kanoon_info(user_query)

                    # Updated prompt for structured response
                    text_query_prompt = f"""
                    You are tasked with answering a legal query in a structured and organized format. Use the following guidelines:

                    User Query:
                    {user_query}

                    Relevant Indian Kanoon Context:
                    {kanoon_context}

                    Please provide the response in the following format:
                    1. **Key Defense Points**: Outline key arguments to defend against any legal allegations or challenges.
                    2. **Supportive Points**: Highlight relevant laws, evidence, or precedents that strengthen the case.
                    3. **Case Overview**: Mention any relevant judge(s), court name, and case details (if applicable).
                    4. **Reason for Dispute**: Summarize the primary cause of the dispute or legal issue.
                    5. **Legal Precedents**: Provide similar case precedents, their decisions, and relevance to this case.
                    6. **Recommendations**: Suggest potential legal strategies, next steps, or actions.

                    Ensure the response is concise, factual, and actionable.
                    """

                    # Prepare messages for API call
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text_query_prompt}
                    ]

                    # Call Hugging Face API
                    completion = client.chat.completions.create(
                        model="meta-llama/Llama-3.2-3B-Instruct",
                        messages=messages,
                        max_tokens=1500
                    )

                    response_content = completion.choices[0].message["content"]
                    st.success("Response:")
                    st.markdown(response_content)  # Displaying formatted response
                except Exception as e:
                    st.error(f"Error: {e}")


    elif feature == "Document Upload":
        st.header("Analyze Legal Document")
        uploaded_file = st.file_uploader("Upload your document (PDF, DOC, DOCX, TXT):", type=["pdf", "doc", "docx", "txt"])
        if uploaded_file:
            try:
                logging.info("Uploaded file detected.")
                filename = uploaded_file.name
                document_text = extract_text_from_file(uploaded_file, filename)
                kanoon_info = fetch_indian_kanoon_info(document_text[:500])
                st.write("Fetched Indian Kanoon Context:", kanoon_info)

                # Updated analysis prompt for better response
                analysis_prompt = f"""
                Analyze the following legal document and provide a structured, detailed summary based on the following key points:

                Document Content:
                {document_text[:2000]}

                Relevant Indian Kanoon Information:
                {kanoon_info}

                Please provide the response in the following format:
                1. **Key Defense Points**: Outline key arguments that can be used to defend against any allegations or legal challenges.
                2. **Supportive Points**: Highlight evidence, laws, or precedents that strengthen the case.
                3. **Case Overview**: Mention the judge(s) involved, court name, and important dates, if available.
                4. **Reason for Dispute**: Summarize the root cause or main contention in the case.
                5. **Legal Precedents**: List similar case precedents, if applicable, and their impact.
                6. **Recommendations**: Suggest potential legal strategies or next steps.

                Keep the response concise, factual, and actionable.
                """

                # Pass prompt to Hugging Face API
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": analysis_prompt}
                ]

                max_allowed_tokens = 4096 - len(analysis_prompt.split())
                max_new_tokens = min(1500, max_allowed_tokens)
                completion = client.chat.completions.create(
                    model="meta-llama/Llama-3.2-3B-Instruct",
                    messages=messages,
                    max_tokens=max_new_tokens
                )

                analysis_content = completion.choices[0].message["content"]
                logging.info("Document analysis completed.")
                st.success("Analysis:")
                st.markdown(analysis_content)  # Displaying formatted output
            except Exception as e:
                logging.error(f"Error analyzing document: {e}")
                st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
