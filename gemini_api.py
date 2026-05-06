import os
import google.generativeai as genai

genai.configure(api_key=os.environ.get('GEMINI_KEY'))

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 1000,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
  system_instruction="You are a job application assistant. Use the provided user data to answer chatbot questions concisely (1-5 words). For multiple choice, only provide the index number.",
)

# FIXED: Using triple quotes for the JSON block to avoid EOL SyntaxErrors
user_data_json = """
{
  "name": "Shuhbam Rajput",
  "contact": {"phone": "8180030015", "email": "shubham.prajval@gmail.com"},
  "summary": {
    "total_experience": "2 years",
    "current_ctc": "3 LPA",
    "expected_ctc": "5 LPA",
    "notice_period": "Immediate",
    "current_location": "Pune",
    "preferred_location": "Mumbai/Pune"
  },
  "skills": {"Java": "2 years", "Spring Boot": "2 years", "Operations": "2 years", "SQL": "2 years"}
}
"""

chat_session = model.start_chat(
  history=[
    {"role": "user", "parts": [user_data_json]},
    {"role": "model", "parts": ["Understood. I have your profile details and will answer questions based on them."]},
    {"role": "user", "parts": ["Remember: answers must be 1-5 words. For options, give only the number."]},
    {"role": "model", "parts": ["Confirmed. I will provide short answers or index numbers only."]}
  ]
)

def bard_flash_response(question) -> str:
    try:
      response = chat_session.send_message(str(question))
      return response.text.strip()
    except Exception as e:
      print(f"AI Error: {e}")
      return "1" # Default to 1 to keep the script moving
