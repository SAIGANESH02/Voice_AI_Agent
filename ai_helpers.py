import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def process_initial_message(customer_name, customer_businessdetails):
    # Process the initial message using OpenAI
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Customer Name: {customer_name}, Details: {customer_businessdetails}",
        max_tokens=100
    )
    return response.choices[0].text.strip()
