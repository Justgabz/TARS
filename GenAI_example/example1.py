from prep import MODEL,genai

gen_model = genai.GenerativeModel(model_name=MODEL)

response = gen_model.generate_content('What is the capital of us?')
print(response.text)