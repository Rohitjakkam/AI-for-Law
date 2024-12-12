import json
import re
from bs4 import BeautifulSoup

def clean_and_structure_text(input_text):
    # Parse the text to remove HTML tags
    soup = BeautifulSoup(input_text, "html.parser")
    plain_text = soup.get_text()

    # Remove extra whitespaces and normalize
    plain_text = re.sub(r'\s+', ' ', plain_text).strip()

    # Structure the content by splitting into sections
    sections = re.split(r'\b(ISSUE NO\.\(\d+\)|\d+\.)', plain_text)
    structured_text = []
    current_section = []

    for segment in sections:
        if re.match(r'(ISSUE NO\.\(\d+\)|\d+\.)', segment):
            if current_section:
                structured_text.append(' '.join(current_section).strip())
                current_section = []
        current_section.append(segment)
    if current_section:
        structured_text.append(' '.join(current_section).strip())

    return '\n\n'.join(structured_text)

# Update this path to the actual location of the file on your local system
file_path = r"D:\AI-for-Law\output_files\readable_output.txt"

# Updated output path (ensure the directory exists)
output_file_path = r"D:\AI-for-Law\output_files\cleaned_structured_output.txt"

try:
    # Load the text from the file
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    # Apply cleaning and structuring
    structured_text = clean_and_structure_text(content)

    # Save the cleaned and structured output
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write(structured_text)

    print(f"Processed text has been saved to: {output_file_path}")

except FileNotFoundError:
    print(f"Error: File not found at {file_path}. Please check the file path and try again.")

