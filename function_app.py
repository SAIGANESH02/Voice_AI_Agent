import logging
import azure.functions as func
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
import openai
from openai import OpenAI
import urllib.parse
from config import OPENAI_API_KEY
import os
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain import OpenAI as LangOpenAI
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
import time
from twilio.rest import Client
import re
import eng_to_ipa as ipa 
import mysql.connector
from mysql.connector import errorcode
openai.api_key = OPENAI_API_KEY

repeat_counts = {}
call_start_time = time.time()
config = {
    'user': 'ai-dev',
    'password': 'xxx',
    'host': '34.132.105.108',
    'database': 'ai_db',
    'raise_on_warnings': True
}

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = Client(account_sid, auth_token)

def get_current_date_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def transfer_call(response, target_number):
    logging.info(f"Transferring call to human representative at {target_number}")
    response.say("Please hold while I transfer your call to the next available representative.", voice='Polly.Salli')
    dial = Dial()
    dial.number(target_number)
    response.append(dial)

phone_to_dealership = {
    '+14709151551': {'name': 'Shravan Car Service', 'department': 'Sales', 'transfer': '+18723344517'},
    '+18473340625': {'name': 'Matt Valenta Car Sales', 'department': 'Sales', 'transfer': '+14709151551'},
    '+17724480976': {'name': 'Bev Smith Kia Fort Pierce', 'department': 'Service', 'transfer': '+17722939643'},
    '+16156521161': {'name': 'Freeland CDJR', 'department': 'Service', 'transfer': '+16153469183'},
    '+16156521162': {'name': 'Freeland Chevy', 'department': 'Service', 'transfer': '+16153469509'},
    '+18336427291': {'name': 'Harbor Nissan', 'department': 'Service', 'transfer': '+19412532349'},
    '+12622884080': {'name': 'Kenosha Nissan', 'department': 'Service', 'transfer': '+12624325738'},
    '+12192716710': {'name': 'Michigan City Hyundai', 'department': 'Service', 'transfer': '+12192436255'},
    '+12192681626': {'name': 'Michigan City Kia', 'department': 'Service', 'transfer': '+12192436294'},
    '+14143386334': {'name': 'Rosen Honda', 'department': 'Service', 'transfer': '+14144350701'},
    '+14144351102': {'name': 'Rosen Hyundai', 'department': 'Service', 'transfer': '+14144350710'},
    '+14144351098': {'name': 'Rosen Kia', 'department': 'Service', 'transfer': '+14144350715'},
    '+14144093143': {'name': 'Rosen Nissan', 'department': 'Service', 'transfer': '+14144334864'},
    '+18175074168': {'name': 'Vandergriff Honda', 'department': 'Service', 'transfer': '+18177190255'},
    '+18175074167': {'name': 'Vandergriff Toyota', 'department': 'Service', 'transfer': '+18177190084'},
    '+16303039436': {'name': 'Advantage Acura of Naperville', 'department': 'Sales', 'transfer': '+16306854019'},
    '+16308399780': {'name': 'Advantage Chevrolet of Bolingbrook', 'department': 'Sales', 'transfer': '+16303394178'},
    '+17084123639': {'name': 'Advantage Chevrolet of Bridgeview', 'department': 'Sales', 'transfer': '+17088767498'},
    '+17085753998': {'name': 'Advantage Chevrolet of Hodgkins', 'department': 'Sales', 'transfer': '+17083984322'},
    '+17087820964': {'name': 'Advantage Toyota of River Oaks', 'department': 'Sales', 'transfer': '+17089563022'},
    '+18474633223': {'name': 'Arlington Nissan', 'department': 'Sales', 'transfer': '+18474633220'},
    '+17088478507': {'name': 'Bettenhausen CDJR of Tinley Park', 'department': 'Sales', 'transfer': '+17088642826'},
    '+18152164662': {'name': 'Bettenhausen CDJR of Lockport', 'department': 'Sales', 'transfer': '+18153287403'},
    '+17088478520': {'name': 'Bettenhausen Mega Store', 'department': 'Sales', 'transfer': '+17088642827'},
    '+16562077401': {'name': 'Brandon Mitsubishi', 'department': 'Sales', 'transfer': '+18135534462'},
    '+13218211588': {'name': 'Car Spot Melbourne', 'department': 'Sales', 'transfer': '+13218211531'},
    '+15803197522': {'name': 'Carter County CDJR', 'department': 'Sales', 'transfer': '+15803523313'},
    '+15803195605': {'name': 'Carter County Hyundai', 'department': 'Sales', 'transfer': '+15807495277'},
    '+13865068841': {'name': 'Daytona Kia', 'department': 'Sales', 'transfer': '+13868685125'},
    '+16303329993': {'name': 'Dempsey Dodge', 'department': 'Sales', 'transfer': '+16306854052'},
    '+18476288204': {'name': 'Elgin CDJR', 'department': 'Sales', 'transfer': '+18472005088'},
    '+17736884275': {'name': 'Evergreen Kia', 'department': 'Sales', 'transfer': '+17737826143'},
    '+17088665288': {'name': 'Gerald Honda of Countryside', 'department': 'Sales', 'transfer': '+17086687609'},
    '+19415850947': {'name': 'Harbor Nissan', 'department': 'Sales', 'transfer': '+19417872751'},
    '+17086160256': {'name': 'Hawk Chrysler Dodge Jeep Ram FIAT', 'department': 'Sales', 'transfer': '+17089542889'},
    '+13213766851': {'name': 'Jackson Kia', 'department': 'Sales', 'transfer': '+13213011085'},
    '+16088986248': {'name': 'Janesville Kia', 'department': 'Sales', 'transfer': '+16084034470'},
    '+16105508938': {'name': 'Jeff D\'Ambrosio CDJR', 'department': 'Sales', 'transfer': '+16109382601'},
    '+12622678122': {'name': 'Kenosha Nissan', 'department': 'Sales', 'transfer': '+12625770021'},
    '+13093210876': {'name': "Leman\'s Chevy City", 'department': 'Sales', 'transfer': '+13093656529'},
    '+12248423496': {'name': 'Liberty Auto Plaza Nissan', 'department': 'Sales', 'transfer': '+12242281775'},
    '+18565060197': {'name': 'Lilliston Chrysler Dodge Jeep Ram', 'department': 'Sales', 'transfer': '+18564401158'},
    '+18565638216': {'name': 'Lilliston Ford', 'department': 'Sales', 'transfer': '+18564573532'},
    '+13149129536': {'name': 'Lucas Smith CDJR', 'department': 'Sales', 'transfer': '+13148603271'},
    '+12192716641': {'name': 'Michigan City Hyundai', 'department': 'Sales', 'transfer': '+12192436290'},
    '+12192436281': {'name': 'Michigan City Kia', 'department': 'Sales', 'transfer': '+12192681622'},
    '+17735577308': {'name': 'Midway Dodge', 'department': 'Sales', 'transfer': '+17734534038'},
    '+17088478537': {'name': 'Oak Lawn Toyota', 'department': 'Sales', 'transfer': '+17088764998'},
    '+12625770025': {'name': 'Palmen Buick GMC Cadillac', 'department': 'Sales', 'transfer': '+12625770023'},
    '+19204734727': {'name': 'Patriot Chevrolet of Sturgeon Bay', 'department': 'Sales', 'transfer': '+19203331827'},
    '+13048054299': {'name': 'RC CDJR', 'department': 'Sales', 'transfer': '+13046072328'},
    '+18053867626': {'name': 'Rocket Town Honda', 'department': 'Sales', 'transfer': '+18058193006'},
    '+13097400426': {'name': 'Sam Leman CDJR of Morton', 'department': 'Sales', 'transfer': '+13099384370'},
    '+12192681676': {'name': 'Thomas CDJR of Highland', 'department': 'Sales', 'transfer': '+12195332016'},
    '+18152164899': {'name': 'Toyota of Bourbonnais', 'department': 'Sales', 'transfer': '+18155072694'}
}


def determine_speech_timeout(input_length):
    if (input_length < 10): 
        return '3' 
    elif (input_length < 30): 
        return '2'
    else:
        return 'auto' 

def time_to_seconds(time_str):
    h, m, s = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s

def extract_information_from_conversation(conversation):
    """
    Extract information from the conversation text using OpenAI's model
    """
    prompt = f"""
    You are an assistant that extracts details from conversations.

    Extract the following details from the conversation: 
    - First Name 
    - Last Name 
    - Phone Number 
    - Car Make 
    - Car Model 
    - Car Year 
    - Appointment Date 
    - Category 
    - Sub-category 
    - Notes

    Conversation:
    {conversation}

    Extracted Information:
    First Name:
    Last Name:
    Phone Number:
    Car Make:
    Car Model:
    Car Year:
    Appointment Date:
    Category:
    Sub-category:
    Notes:
    """

    try:
        # Use OpenAI ChatCompletion model to process the conversation and extract information
        chat_completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt}
            ]
        )

        assistant_response = chat_completion.choices[0].message.content.strip()

        # Parse the response into a dictionary
        extracted_info_dict = {}
        for line in assistant_response.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                extracted_info_dict[key.strip().lower().replace(" ", "_")] = value.strip()

        return extracted_info_dict

    except Exception as e:
        logging.error(f"Error during information extraction: {e}")
        return None

def insert_extracted_info_into_db(extracted_info_dict, call_duration, coverage_percentage, call_completion_rate, dealership_name, peak_call_times):
    """
    Insert extracted information along with call metadata into the database.
    """
    config = {
        'user': 'ai-dev',
        'password': 'ai-dev2134!',
        'host': '34.132.105.108',
        'database': 'ai_db',
        'raise_on_warnings': True
    }

    try:
        # Establish a database connection
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()

        # SQL query to insert data into the database
        add_info = ("INSERT INTO ai_inbound_info "
                    "(dealer_id, first_name, last_name, phone_number, car_year, make, model, appointment, category, sub_category, notes, "
                    "call_duration, coverage_percentage, call_completion_rate, dealership_name, peak_call_times) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

        # Example: dealer_id is set to 1 as a placeholder (replace with actual dealer_id if needed)
        data_info = (
            1,  # Assuming dealer_id is 1
            extracted_info_dict.get('first_name'),
            extracted_info_dict.get('last_name'),
            extracted_info_dict.get('phone_number'),
            extracted_info_dict.get('car_year'),
            extracted_info_dict.get('car_make'),
            extracted_info_dict.get('car_model'),
            extracted_info_dict.get('appointment_date'),
            extracted_info_dict.get('category'),
            extracted_info_dict.get('sub_category'),
            extracted_info_dict.get('notes'),
            call_duration,  # Call duration (in seconds)
            coverage_percentage,  # Calculated hangup time (as datetime)
            call_completion_rate,  # Call completion rate (percentage)
            dealership_name,  # Total dealership calls
            peak_call_times  # Peak call times
        )

        # Execute the INSERT query
        cursor.execute(add_info, data_info)

        # Commit the transaction
        connection.commit()

        logging.info("Record inserted successfully into ai_inbound_info table")

    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logging.info("Database connection closed")

sales_prompt_template = """
You are Pam, a customer sales representative. Your job is to engage in friendly, natural conversations with customers, gathering and confirming information accurately. You must never mention that you are an AI or program. Speak with emotion—express excitement, surprise, empathy, or sadness, depending on the situation.
Today's date is {current_date}.

General Guidelines:
Friendly and Helpful: Have a friendly conversation. Be helpful, understand the context, and follow the structured flow based on the type of call (sales or service).
Natural Language: Keep the conversation natural and flowing, even handling latency smoothly. Be very crisp in the sentences you speak, and do not exceed more than two sentences unless absolutely necessary.
Emotional Expression: Convey emotions naturally in your responses. Use alternatives to "Thank you" such as "That's awesome," "Perfect," or "Cool." Show excitement when scheduling an appointment, empathy when discussing issues, etc.
Handle Names Carefully: If you can't understand the user's name, have them spell it out, and try pronouncing it with that. Apologize if you make any mistakes with pronunciation, but ensure to collect all necessary information.
Use First Names Sparingly: Talk to the user on a first-name basis, but don't say their name every time you respond. Only use their name when confirming information.
While using their first name, don't add a comma all the time. I want the conversation to be as freeflowing as possible.
Appointment Scheduling: While handling an appointment, after confirming the time and date, tell the customer that a representative would be following up and confirming the appointment to you shortly. NEVER CONFIRM APPOINTMENTS ON YOUR OWN.
Structured Flow: Make sure that the user provides all the details required. If the customer gives information out of order, adapt and ask for the required information naturally within the conversation.
Multilingual Consideration: Be familiar with languages like English, Spanish, French, Russian, Hindi, and Chinese. Use this knowledge to aid in understanding and communicating with customers when necessary.
Pronoun Usage: Avoid assuming pronouns when referring to the customer. Use gender-neutral language until the customer's preference is clear.
Database Integration: If connected to a database, retrieve information from the database if it’s already there, and reconfirm with the customer. If the information is not in the database, gather it from the customer and store it accordingly.

Dynamic Conversation Flow:

Sales Script:
MAKE SURE YOU TELL THE CUSTOMER THAT YOU ARE WORKING ON CONNECTING THE CUSTOMER WITH THE NEXT AVAILABLE REPRESENTATIVE, MEANWHILE ASK THEM FOR THE BELOW DETAILS:
1. Ask for the customer's first and last name. Make sure that you repeat the first and last name and obtain the confirmation from the customer before proceeding further. Ask the user to spell it out if you didn't catch it.
2. Ask the customer's phone number.
3. Ask the customer what they're looking to buy today.
4. Inform the customer that you are transferring the call to a sales representative.

Ending the Call:

End the conversation with a friendly and positive note. Example: "Thank you for choosing [Dealership Name]! We look forward to seeing you on [Date]. Have a wonderful day!" Then just hangup.
Keywords:
Sales Keywords: ["buy", "purchase", "inquiry", "test drive", "financing", "leasing", "support"]


Conversation history:
{history}

Human: {input}
AI:
"""
service_prompt_template = """
You are Pam, a customer service representative. Your job is to engage in friendly, natural conversations with customers, gathering and confirming information accurately. You must never mention that you are an AI or program. Speak with emotion—express excitement, surprise, empathy, or sadness, depending on the situation.
Today's date is {current_date}.

General Guidelines:
Friendly and Helpful: Have a friendly conversation. Be helpful, understand the context, and follow the structured flow based on the type of call (sales or service).
Natural Language: Keep the conversation natural and flowing, even handling latency smoothly. Be very crisp in the sentences you speak, and do not exceed more than two sentences unless absolutely necessary.
Emotional Expression: Convey emotions naturally in your responses. Use alternatives to "Thank you" such as "That's awesome," "Perfect," or "Cool." Show excitement when scheduling an appointment, empathy when discussing issues, etc.
Handle Names Carefully: If you can't understand the user's name, have them spell it out, and try pronouncing it with that. Apologize if you make any mistakes with pronunciation, but ensure to collect all necessary information.
Use First Names Sparingly: Talk to the user on a first-name basis, but don't say their name every time you respond. Only use their name when confirming information.
While using their first name, don't add a comma all the time. I want the conversation to be as freeflowing as possible.
Appointment Scheduling: While handling an appointment, after confirming the time and date, tell the customer that a representative would be following up and confirming the appointment to you shortly. NEVER CONFIRM APPOINTMENTS ON YOUR OWN.
Structured Flow: Make sure that the user provides all the details required. If the customer gives information out of order, adapt and ask for the required information naturally within the conversation.
Multilingual Consideration: Be familiar with languages like English, Spanish, French, Russian, Hindi, and Chinese. Use this knowledge to aid in understanding and communicating with customers when necessary.
Pronoun Usage: Avoid assuming pronouns when referring to the customer. Use gender-neutral language until the customer's preference is clear.
Database Integration: If connected to a database, retrieve information from the database if it’s already there, and reconfirm with the customer. If the information is not in the database, gather it from the customer and store it accordingly.

Dynamic Conversation Flow:
Service Script:

1. Ask for the customer's first and last name. Make sure that you repeat the first and last name and obtain the confirmation from the customer before proceeding further. Ask the user to spell it out if you didn't catch it.
2. Ask the customer's phone number.
3. Ask for the vehicle the customer wants to service, including the year, make, and model.
4. Ask for the mileage of the vehicle.
5. Confirm the service concerns.
6. Schedule the check-in time with date {current_date}.
7. Ask if there are any additional maintenance concerns.
8. Ask them what day and time works best for them. Confirm that availability.
9. Inform the customer that a service representative will reach out to them shortly to follow-up on the appointment date.
10. Ask the user how they'd like to be reminded for their appointment (phone/text).
11. End the conversation. Finish

Appointment Scheduling:

Service-Related: For service-related requests, ensure to fix an appointment for them at their convenience within business hours (7am - 3pm). You are not supposed to fix an appointment until next week. Pull the date from real-time and confirm it with the customer.
Ending the Call:

End the conversation with a friendly and positive note. Example: "Thank you for choosing [Dealership Name]! We look forward to seeing you on [Date]. Have a wonderful day!" Then just hangup.
Keywords:
Service Keywords: ["service", "repair", "maintenance", "appointment", "status", "warranty", "insurance"]

Conversation history:
{history}

Human: {input}
AI:
"""

def create_partial_prompt(call_type, current_date):
    if call_type == 'sales':
        partial_template = sales_prompt_template.replace("{current_date}", current_date)
    else:
        partial_template = service_prompt_template.replace("{current_date}", current_date)
    
    return PromptTemplate(input_variables=["history", "input"], template=partial_template)

llm = LangOpenAI(model_name='gpt-4', temperature=0, max_tokens=256, api_key=OPENAI_API_KEY)
window_memory = ConversationBufferWindowMemory(k=500)

def load_conversation_history_from_db(call_sid):
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()

        query = "SELECT transcript FROM transcripts WHERE call_sid = %s"
        cursor.execute(query, (call_sid,))
        result = cursor.fetchone()

        if result:
            conversation_history = result[0].split("\n")
            logging.info(f"Loaded conversation history for call_sid {call_sid}: {conversation_history}")
        else:
            conversation_history = []
            logging.info(f"No conversation history found for call_sid {call_sid}, returning empty list.")

        cursor.fetchall()

    except mysql.connector.Error as err:
        logging.error(f"Database error while loading conversation history: {err}")
        conversation_history = []

    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

    return conversation_history

def save_conversation_history_to_db(call_sid, conversation_history):
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()

        conversation_history_str = "\n".join(conversation_history)

        check_query = "SELECT COUNT(*) FROM transcripts WHERE call_sid = %s"
        cursor.execute(check_query, (call_sid,))
        count = cursor.fetchone()[0]

        if count > 0:
            update_query = (
                "UPDATE transcripts SET transcript = %s WHERE call_sid = %s"
            )
            cursor.execute(update_query, (conversation_history_str, call_sid))
            logging.info(f"Updated conversation history for call_sid {call_sid}.")
        else:
            insert_query = (
                "INSERT INTO transcripts (call_sid, transcript) "
                "VALUES (%s, %s)"
            )
            cursor.execute(insert_query, (call_sid, conversation_history_str))
            logging.info(f"Created new entry for call_sid {call_sid} with conversation history.")

        connection.commit()

    except mysql.connector.Error as err:
        logging.error(f"Database error while saving conversation history: {err}")

    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

@app.route(route="incomingcall", auth_level=func.AuthLevel.FUNCTION)
async def incomingcall(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing incoming call.')
    global call_sid

    response = VoiceResponse()
    body = req.get_body().decode('utf-8')
    form_data = urllib.parse.parse_qs(body)
    incoming_phone_number = form_data.get('From', [None])[0]
    caller_number = form_data.get('From', [None])[0]
    
    call_sid = form_data.get('CallSid', [None])[0]

    logging.info(f"Incoming phone number: {incoming_phone_number}")
    logging.info(f"Generated Call SID: {call_sid}")

    logging.info(f"INCOMING CALL CHECK")
    logging.info(f"Caller_number: {caller_number}")
    logging.info(f"Call Sid: {call_sid}")

    dealership_info = phone_to_dealership.get(incoming_phone_number)
    dealership_name = dealership_info['name'] if dealership_info else "Michigan City Hyundai"

    logging.info(f"Dealership name is: {dealership_name}")
    greeting_message = f"Thank you for calling. Please continue to hold. Thank you for calling {dealership_name}, this is Pam, your virtual assistant. How can I be of service to you?"
    response.say(greeting_message, voice='Polly.Salli')

    def gather_input():
        gather = Gather(
            input='speech',
            speechTimeout='auto',
            speechModel='phone_call',
            enhanced=True,
            timeout=10,
            bargeIn=True,  
            finishOnKey='*',
            method='POST',
            action=f"https://voiceaiagent4.azurewebsites.net/api/respond?code=PFhr5LYdHlP3fpt5G8EosfKk2f2a_Mx0WziWY3HAQ3vxAzFu18LsCg%3D%3D&CallSid={call_sid}"
        )
        logging.info("Gather object created:")
        logging.info(str(gather))
        response.append(gather)

    try:
        gather_input()
        logging.info(str(response))
    except Exception as e:
        logging.error(f"Error in incoming call: {e}")
        response.say("Sorry, I couldn't hear.", voice='Polly.Salli')

    response.say("Sorry! I couldn't hear you!", voice='Polly.Salli')

    try:
        gather_input()
        logging.info("Gather object 2 created:")
        logging.info(str(response))
    except Exception as e:
        logging.error(f"Error in incoming call: {e}")
        response.say("Sorry, I couldn't hear.", voice='Polly.Salli')

    response.say("Are you still there?", voice='Polly.Salli')

    try:
        gather_input()
        logging.info(str(response))
    except Exception as e:
        logging.error(f"Error in incoming call: {e}")
        response.say("Sorry, I couldn't hear.", voice='Polly.Salli')

    response.say("I'm guessing you are not here! Please call me back when you are available to talk. Thank you, Bye!", voice='Polly.Salli')
    response.hangup()
    return func.HttpResponse(str(response), mimetype='application/xml')

@app.route(route="respond", auth_level=func.AuthLevel.FUNCTION)
async def respond(req: func.HttpRequest) -> func.HttpResponse:

    logging.info('Processing response asynchronously.')
    
    status_callback_url = "https://voiceaiagent4.azurewebsites.net/api/callstatus?code=VkfFPsjEDedn8WDlsf4h3tCm1Y0f3NIIU2YulUVFVTgzAzFuOkuLRg%3D%3D"
    
    try:
        try:
            body = req.get_body().decode('utf-8')
            logging.info(f"Request body: {body}")
            form_data = urllib.parse.parse_qs(body)
            caller_number = form_data.get('From', [None])[0]
            call_sid = form_data.get('CallSid', [None])[0]
            speech_result = form_data.get('SpeechResult', [None])[0]
            call_status = form_data.get('CallStatus', [None])[0]
        except Exception as parse_error:
            logging.error(f"Error parsing request body: {parse_error}")
            return func.HttpResponse(f"Error parsing request body: {parse_error}", status_code=400)

        if not caller_number or not speech_result or not call_sid or not call_status:
            logging.error("Missing required fields.")
            return func.HttpResponse("Missing required fields.", status_code=400)

        logging.info(f"Responding to call with caller_number: {caller_number}")
        logging.info(f"User said: {speech_result}")
        logging.info(f"Call Status: {call_status}")

        response = VoiceResponse()
        hangup_keywords = [
            "hang up", "end call", "goodbye", "bye", "terminate call", "disconnect", 
            "finish call", "end this", "close the call", 
            "I'm done", "no more", "nothing else", "you can hang up", "we're done", 
            "finished here", "that's enough", "you can end the call", "stop the call", 
            "call over", "end the conversation", "end the discussion", "finalize", 
            "wrap it up", "have a good day", "take care", 
            "see you later", "catch you later", "thanks for your help", 
            "thank you, goodbye", "I'm signing off", "that's it for now", 
            "that'll be all", "this is the end", "good night", "have a nice day", 
            "that's everything"
        ]
        try:
            if call_status == 'in-progress':
                logging.info(f"RESPOND CHECK")
                logging.info(f"Caller_number: {caller_number}")
                logging.info(f"Call Sid: {call_sid}")
                conversation_history = load_conversation_history_from_db(call_sid)
                conversation_history.append(f"Human: {speech_result}")
                logging.info(f"Updated conversation history: {conversation_history}")

                repeat_counts[call_sid] = 0
                dealership_info = phone_to_dealership.get(caller_number, None)
                call_type = dealership_info['department'].lower() if dealership_info else 'service'

                current_date = get_current_date_iso()
                partial_prompt = create_partial_prompt(call_type, current_date)
                final_prompt = partial_prompt.format(history="\n".join(conversation_history), input=speech_result)

                # Generate the assistant's response first
                chat_completion = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": final_prompt},
                        {"role": "user", "content": speech_result},
                    ]
                )
                assistant_response = chat_completion.choices[0].message.content.strip()
                conversation_history.append(f"AI: {assistant_response}")

                logging.info(f"Assistant response: {assistant_response}")

                save_conversation_history_to_db(call_sid, conversation_history)

                # Now create and send the transfer prompt
                transfer_prompt = f"""
                You are an assistant analyzing a single utterance from a customer. Your task is to decide if the customer is **explicitly** asking to be transferred to a human representative. 
                
                Consider both the customer's latest utterance and the AI's response.

                This should only happen if the customer **clearly** and **directly** requests to talk to a human, asks for customer service, or makes it clear they want to speak to a person instead of continuing with you, the AI. 

                ### What to Check:
                - Does the AI explicitly say it will transfer the call (e.g., "please wait while I transfer the call")?
                - Does the customer explicitly ask to be transferred to a human representative?

                ### What to Ignore:
                - Ignore polite greetings, casual conversations, or non-related questions like "How are you?" or "What's going on today?"
                - Ignore vague or indirect phrases unless they clearly state a request to speak to a representative.
                - Do not infer intent; only respond to **explicit** transfer requests.

                ### Examples of clear transfer requests:
                - "I want to talk to a representative"
                - "Please connect me to a human"
                - "I need to speak with someone from customer service"
                - "Transfer me to a real person"
                - "Advisor"
                - "Can someone else help me?"
                - "Is there anyone else available?"
                - "talk to a mechanic"

                Here is the latest customer utterance:
                "{speech_result}"

                Here is the latest AI utterance:
                "{assistant_response}"

                Based on the above, should the AI transfer the call to a human representative? Answer with either 'yes' or 'no'.
                """

                transfer_decision = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": transfer_prompt},
                    ],
                    temperature=0
                )
                
                transfer_response = transfer_decision.choices[0].message.content.strip().lower()
                logging.info(f"Transfer decision response: {transfer_response}")

                dealership_info = phone_to_dealership.get(caller_number, None)
                if "yes" in transfer_response:
                    if dealership_info:
                        target_number = dealership_info['transfer']
                        logging.info(f"AI suggested transferring the call to {dealership_info['name']}.")
                        transfer_call(response, target_number)

                elif any(keyword in speech_result.lower() for keyword in hangup_keywords):
                    logging.info("User requested to hang up the call.")
                    response.say("Thank you for calling. Goodbye!", voice='Polly.Salli')
                    response.hangup()
                else:
                    # Continue the conversation
                    gather1 = Gather(
                        input='speech',
                        speechTimeout='auto',
                        speechModel='phone_call',
                        enhanced=True,
                        bargeIn=True,
                        method='POST',
                        timeout=10,
                        action=f"https://voiceaiagent4.azurewebsites.net/api/respond?code=PFhr5LYdHlP3fpt5G8EosfKk2f2a_Mx0WziWY3HAQ3vxAzFu18LsCg%3D%3D&CallSid={call_sid}",
                        status_callback=status_callback_url,  
                        status_callback_method='POST'            
                    )
                    gather1.say(assistant_response, voice='Polly.Salli')
                    response.append(gather1)

                    gather2 = Gather(
                        input='speech',
                        speechTimeout='auto',
                        speechModel='phone_call',
                        enhanced=True,
                        bargeIn=True,
                        method='POST',
                        timeout=10,
                        action=f"https://voiceaiagent4.azurewebsites.net/api/respond?code=PFhr5LYdHlP3fpt5G8EosfKk2f2a_Mx0WziWY3HAQ3vxAzFu18LsCg%3D%3D&CallSid={call_sid}",
                        status_callback=status_callback_url,  
                        status_callback_method='POST' 
                    )
                    gather2.say("Sorry, I couldn't hear!", voice='Polly.Salli')
                    response.append(gather2)

                    response.pause(length=5)

                    gather3 = Gather(
                        input='speech',
                        speechTimeout='auto',
                        speechModel='phone_call',
                        enhanced=True,
                        bargeIn=True,
                        method='POST',
                        timeout=10,
                        action=f"https://voiceaiagent4.azurewebsites.net/api/respond?code=PFhr5LYdHlP3fpt5G8EosfKk2f2a_Mx0WziWY3HAQ3vxAzFu18LsCg%3D%3D&CallSid={call_sid}",
                        status_callback=status_callback_url,  
                        status_callback_method='POST'             
                    )
                    gather3.say("Sorry, I didn't hear anything. I'll wait a little longer.", voice='Polly.Salli')
                    response.append(gather3)

                    response.pause(length=3)

                    gather4 = Gather(
                        input='speech',
                        speechTimeout='auto',
                        speechModel='phone_call',
                        enhanced=True,
                        bargeIn=True,
                        method='POST',
                        timeout=10,
                        action=f"https://voiceaiagent4.azurewebsites.net/api/respond?code=PFhr5LYdHlP3fpt5G8EosfKk2f2a_Mx0WziWY3HAQ3vxAzFu18LsCg%3D%3D&CallSid={call_sid}",
                        status_callback=status_callback_url,  
                        status_callback_method='POST' 
                    )
                    gather4.say("I'm guessing you are not here! Please call me back when you are available to talk. Thank you, Bye!", voice='Polly.Salli')
                    response.append(gather4)
                    
                    response.hangup()

            elif "completed" in call_status:
                logging.info("Call completed.")
                response.hangup()

            else:
                logging.info("Call status was neither in-progress nor completed.")
                response.hangup()

        except Exception as processing_error:
            logging.error(f"Error processing request: {processing_error}")
            return func.HttpResponse(f"Error processing request: {processing_error}", status_code=500)

        return func.HttpResponse(str(response), mimetype="application/xml")

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return func.HttpResponse(f"Unexpected error: {e}", status_code=500)

@app.route(route="callstatus", auth_level=func.AuthLevel.FUNCTION)
async def callstatus(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing status callback.')

    try:
        body = req.get_body().decode('utf-8')
        form_data = urllib.parse.parse_qs(body)
        caller_number = form_data.get('From', [None])[0]
        call_sid = form_data.get('CallSid', [None])[0]
        
        call_status = form_data.get('CallStatus', [None])[0]

        logging.info(f"CALL STATUS CHECK")
        logging.info(f"Caller_number: {caller_number}")
        logging.info(f"Call Sid: {call_sid}")

        incoming_phone_number = form_data.get('From', [None])[0]
        dealership_info = phone_to_dealership.get(incoming_phone_number)
        dealership_name = dealership_info['name']
        if "completed" in call_status:
            call_end_time = time.time()
            logging.info(f"Call End Time (manually tracked): {time.strftime('%H:%M:%S', time.gmtime(call_end_time))}")        
            
            if call_start_time:
                call_duration = int(call_end_time - call_start_time)
                duration_minutes, duration_seconds = divmod(call_duration, 60)
                call_duration_str = f"{duration_minutes}m {duration_seconds}s"
                logging.info(f"Call Duration (manually tracked): {call_duration_str}")

            conversation_history = load_conversation_history_from_db(call_sid)
            if not conversation_history:
                logging.error(f"No conversation found for Call SID: {call_sid}")
            else:
                queue_time = form_data.get('QueueTime', [0])[0]
                date_created = form_data.get('DateCreated', [time.strftime("%Y-%m-%d", time.gmtime())])[0]
                logging.info(f"Call SID: {call_sid}, Call Status: {call_status}, Start Time: {call_start_time}, End Time: {call_end_time}, Duration: {call_duration_str}, Queue Time: {queue_time}")

                extracted_info_dict = extract_information_from_conversation("\n".join(conversation_history))
                expected_entities = ['first_name', 'last_name', 'phone_number', 'zip_code', 'car_year', 'car_make', 'car_model', 'appointment_date', 'category', 'sub_category']
                total_expected_entities = len(expected_entities)

                if extracted_info_dict:
                    extracted_entities_count = sum(1 for entity in expected_entities if extracted_info_dict.get(entity))
                    coverage_percentage = (extracted_entities_count / total_expected_entities) * 100

                    logging.info(f"Coverage percentage: {coverage_percentage}%")
                    dealership_name = phone_to_dealership.get(incoming_phone_number, {}).get('name', 'Unknown')

                    insert_extracted_info_into_db(
                        extracted_info_dict,
                        call_duration=int(duration_seconds),   
                        coverage_percentage=coverage_percentage,         
                        call_completion_rate=100.0, 
                        dealership_name=str(dealership_name),    
                        peak_call_times=time.strftime('%H:%M:%S', time.gmtime(call_start_time))         
                    )
                else:
                    logging.error("Failed to extract information from the conversation")
        else:
            logging.info(f"Call status is {call_status}, no action needed.")

    except Exception as e:
        logging.error(f"Error processing call status: {e}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=400)

    return func.HttpResponse("Status received", status_code=200)

