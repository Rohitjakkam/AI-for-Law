from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# File paths
ai_response_file = r"D:\AI-for-Law\output_files\ai_response.txt"
cleaned_output_file = r"D:\AI-for-Law\output_files\cleaned_structured_output.txt"

# Load content from files
with open(ai_response_file, "r", encoding="utf-8") as file:
    ai_response_text = file.read()

with open(cleaned_output_file, "r", encoding="utf-8") as file:
    cleaned_output_text = file.read()

# Initialize SentenceTransformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Compute embeddings
embeddings = model.encode([ai_response_text, cleaned_output_text])

# Calculate cosine similarity
similarity_score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

# Print the similarity score
print(f"Similarity Score: {similarity_score:.4f}")
