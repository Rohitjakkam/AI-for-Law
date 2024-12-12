from googletrans import Translator  # Add a translator for language translation
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
    responses to legal inquiries. You are also a multilingual chatbot capable of understanding and responding in multiple Indian languages, 
    including Hindi.If there is any kind of issue with respone should not at all be in other lanuguage. Ensure that your responses are contextually accurate and tailored to the user's 
    preferred language. When addressing legal matters, use terminology and examples specific to Indian laws, and strive to explain complex 
    legal concepts in a user-friendly manner. If a user's question is unclear or incomplete, politely ask for clarification..."""  # Truncated for brevity
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

# Initialize the translator
translator = Translator()

def main():
    st.title("KanoonSetu (Hindi Edition)")
    st.sidebar.title("Features")
    logging.info("Application started (Hindi Edition).")

    # Feature selection
    feature = st.sidebar.radio("Select a feature:", ("Text Input", "Document Upload"))
    logging.info(f"Selected feature: {feature}")

    if feature == "Text Input":
        st.header("कानूनी एआई के साथ चैट करें")
        user_query_hindi = st.text_area("अपना कानूनी प्रश्न दर्ज करें (हिंदी में):")
        if st.button("उत्तर प्राप्त करें"):
            if not user_query_hindi.strip():
                st.error("कृपया एक प्रश्न दर्ज करें।")
            else:
                try:
                    # Translate user query from Hindi to English
                    user_query_english = translator.translate(user_query_hindi, src="hi", dest="en").text

                    # Fetch Indian Kanoon context using translated query
                    kanoon_context_english = fetch_indian_kanoon_info(user_query_english)

                    # Translate Kanoon context back to Hindi
                    kanoon_context_hindi = translator.translate(kanoon_context_english, src="en", dest="hi").text

                    # Translate prompt to Hindi
                    text_query_prompt_hindi = f"""
                    आप एक कानूनी प्रश्न का उत्तर एक संरचित और व्यवस्थित प्रारूप में देने के लिए जिम्मेदार हैं। निम्नलिखित दिशानिर्देशों का उपयोग करें:

                    उपयोगकर्ता का प्रश्न:
                    {user_query_hindi}

                    संबंधित भारतीय कानून संदर्भ:
                    {kanoon_context_hindi}

                    कृपया उत्तर निम्नलिखित प्रारूप में प्रदान करें:
                    1. **मुख्य बचाव बिंदु**: किसी भी कानूनी आरोपों या चुनौतियों का सामना करने के लिए मुख्य तर्क।
                    2. **सहायक बिंदु**: प्रासंगिक कानून, साक्ष्य, या नजीरें जो मामले को मजबूत करती हैं।
                    3. **मामले का अवलोकन**: किसी प्रासंगिक न्यायाधीश, अदालत का नाम, और मामले का विवरण (यदि लागू हो)।
                    4. **विवाद का कारण**: विवाद या कानूनी मुद्दे का प्राथमिक कारण।
                    5. **कानूनी नजीरें**: इसी तरह के मामले, उनके निर्णय, और इस मामले से उनकी प्रासंगिकता।
                    6. **सिफारिशें**: संभावित कानूनी रणनीतियाँ, अगले कदम, या कार्य।

                    सुनिश्चित करें कि उत्तर संक्षिप्त, तथ्यात्मक और क्रियान्वयन योग्य हो।
                    """

                    # Prepare messages for API call
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text_query_prompt_hindi}
                    ]

                    # Call Hugging Face API
                    completion = client.chat.completions.create(
                        model="meta-llama/Llama-3.2-3B-Instruct",
                        messages=messages,
                        max_tokens=1500
                    )

                    response_content_hindi = completion.choices[0].message["content"]
                    st.success("उत्तर:")
                    st.markdown(response_content_hindi)  # Display response in Hindi
                except Exception as e:
                    st.error(f"त्रुटि: {e}")

    elif feature == "Document Upload":
        st.header("कानूनी दस्तावेज़ का विश्लेषण करें")
        uploaded_file = st.file_uploader("अपना दस्तावेज़ अपलोड करें (PDF, DOC, DOCX, TXT):", type=["pdf", "doc", "docx", "txt"])
        if uploaded_file:
            try:
                logging.info("Uploaded file detected.")
                filename = uploaded_file.name
                document_text = extract_text_from_file(uploaded_file, filename)

                # Translate document text to English for Indian Kanoon API
                document_text_english = translator.translate(document_text[:500], src="hi", dest="en").text
                kanoon_info_english = fetch_indian_kanoon_info(document_text_english)

                # Translate Kanoon context to Hindi
                kanoon_info_hindi = translator.translate(kanoon_info_english, src="en", dest="hi").text

                st.write("भारतीय कानून संदर्भ:", kanoon_info_hindi)

                # Prepare analysis prompt in Hindi
                analysis_prompt_hindi = f"""
                निम्नलिखित कानूनी दस्तावेज़ का विश्लेषण करें और निम्नलिखित प्रमुख बिंदुओं के आधार पर एक संरचित, विस्तृत सारांश प्रदान करें:

                दस्तावेज़ सामग्री:
                {document_text[:2000]}

                संबंधित भारतीय कानून जानकारी:
                {kanoon_info_hindi}

                कृपया उत्तर निम्नलिखित प्रारूप में प्रदान करें:
                1. **मुख्य बचाव बिंदु**: किसी भी आरोपों या कानूनी चुनौतियों का सामना करने के लिए मुख्य तर्क।
                2. **सहायक बिंदु**: साक्ष्य, कानून, या नजीरें जो मामले को मजबूत करती हैं।
                3. **मामले का अवलोकन**: इसमें न्यायाधीश, अदालत का नाम, और महत्वपूर्ण तिथियां शामिल हों।
                4. **विवाद का कारण**: विवाद या मुख्य मुद्दे की जड़।
                5. **कानूनी नजीरें**: इसी तरह के मामलों की सूची और उनके प्रभाव।
                6. **सिफारिशें**: संभावित कानूनी रणनीतियाँ या अगले कदम।

                सुनिश्चित करें कि उत्तर संक्षिप्त, तथ्यात्मक और क्रियान्वयन योग्य हो।
                """

                # Call Hugging Face API
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": analysis_prompt_hindi}
                ]

                max_allowed_tokens = 4096 - len(analysis_prompt_hindi.split())
                max_new_tokens = min(1500, max_allowed_tokens)
                completion = client.chat.completions.create(
                    model="meta-llama/Llama-3.2-3B-Instruct",
                    messages=messages,
                    max_tokens=max_new_tokens
                )

                analysis_content_hindi = completion.choices[0].message["content"]
                logging.info("Document analysis completed in Hindi.")
                st.success("विश्लेषण:")
                st.markdown(analysis_content_hindi)  # Display response in Hindi
            except Exception as e:
                logging.error(f"Error analyzing document: {e}")
                st.error(f"त्रुटि: {e}")


if __name__ == "__main__":
    main()
