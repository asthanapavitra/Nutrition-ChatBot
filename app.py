# Required Libraries
from flask import Flask, request, jsonify
from twilio.rest import Client
import openai
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Twilio Credentials
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_whatsapp_number = os.getenv('TWILIO_Whatsapp')
client = Client(account_sid, auth_token)

# OpenAI API Key
openai.api_key = os.getenv('OPENAI_API_KEY')

# BetterDoctor API Key
betterdoctor_api_key = os.getenv('BETTERDOCTOR_API_KEY')

# Function to fetch nutritionists using BetterDoctor API
def get_nutritionists():
    url = f"https://api.betterdoctor.com/2016-03-01/doctors?specialty_uid=dietitian&location=37.773,-122.413,100&skip=0&limit=10&user_key={betterdoctor_api_key}"
    response = requests.get(url)
    data = response.json()

    # Parse and return a list of nutritionists
    nutritionists = []
    for doctor in data.get('data', []):
        name = doctor['profile']['first_name'] + " " + doctor['profile']['last_name']
        phone = doctor['practices'][0]['phones'][0]['number']
        nutritionists.append({"name": name, "phone": phone})

    return nutritionists

# Function to analyze user input (height, weight, etc.)
def analyze_user_input(user_data):
    height = user_data.get("height")
    weight = user_data.get("weight")
    bmi = weight / ((height / 100) ** 2)
    if bmi >= 30:
        return "It looks like your BMI is in the obese range. We recommend professional help."
    else:
        return "Your BMI is within a healthy range. Here's a diet chart for you."

# Function to book an appointment (mockup)
def book_appointment(nutritionist_name, user_phone):
    message = f"Appointment with {nutritionist_name} has been booked. We'll confirm it via call."
    return message

# Route to interact with the Chatbot
@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_data = request.json

    # Get user input for height, weight, symptoms
    height = user_data.get("height")
    weight = user_data.get("weight")
    symptoms = user_data.get("symptoms")
    user_phone = user_data.get("phone")

    # Step 1: Use OpenAI GPT to generate a diet chart or response
    openai_prompt = f"The user has a height of {height} cm, weight of {weight} kg, and symptoms: {symptoms}. Please suggest a diet."
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=openai_prompt,
        max_tokens=150
    )
    ai_response = response['choices'][0]['text'].strip()

    # Step 2: Analyze user health based on BMI and symptoms
    health_advice = analyze_user_input(user_data)

    # Step 3: Suggest professional help if needed
    if "recommend professional help" in health_advice:
        # Fetch nutritionists using BetterDoctor API
        nutritionists = get_nutritionists()
        nutritionist = nutritionists[0]  # Choose the first nutritionist
        whatsapp_message = f"{health_advice} Do you want to book an appointment with {nutritionist['name']}?"

        # Send WhatsApp message using Twilio
        message = client.messages.create(
            body=whatsapp_message,
            from_=twilio_whatsapp_number,
            to=f'whatsapp:{user_phone}'
        )
        return jsonify({"message": whatsapp_message, "ai_response": ai_response, "whatsapp_status": "sent"})
    
    # Step 4: If no professional help needed, return AI response and diet chart
    return jsonify({"ai_response": ai_response, "health_advice": health_advice})

# Route to confirm and book appointment
@app.route('/confirm_appointment', methods=['POST'])
def confirm_appointment():
    user_data = request.json
    user_phone = user_data.get("phone")
    nutritionist_name = user_data.get("nutritionist_name")

    # Book the appointment
    booking_confirmation = book_appointment(nutritionist_name, user_phone)

    # Send WhatsApp message confirmation
    message = client.messages.create(
        body=booking_confirmation,
        from_=twilio_whatsapp_number,
        to=f'whatsapp:{user_phone}'
    )

    return jsonify({"confirmation": booking_confirmation, "whatsapp_status": "sent"})

if __name__ == '__main__':
    app.run(debug=True)
