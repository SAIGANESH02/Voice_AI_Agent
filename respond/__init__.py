import logging
import azure.functions as func
from twilio.twiml.voice_response import VoiceResponse, Gather
import openai
import urllib.parse
import os
from config import OPENAI_API_KEY
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, AudioConfig, SpeechSynthesisVoiceName, SpeechSynthesisOutputFormat

openai.api_key = OPENAI_API_KEY

# Dictionary to store conversation history for each call
conversations = {}

# # Initialize Azure Text Analytics client
# def authenticate_text_analytics_client():
#     ta_credential = AzureKeyCredential(os.getenv("AZURE_TEXT_ANALYTICS_KEY"))
#     text_analytics_client = TextAnalyticsClient(
#         endpoint=os.getenv("AZURE_TEXT_ANALYTICS_ENDPOINT"),
#         credential=ta_credential)
#     return text_analytics_client

# # Select voice and style based on the content
# def select_voice_and_style(content):
#     if "angry" in content:
#         return 'en-US-GuyNeural', 'angry'
#     elif "surprise" in content:
#         return 'en-US-GuyNeural', 'cheerful'
#     elif "funny" in content:
#         return 'en-US-GuyNeural', 'newscast-casual'
#     elif "friendly" in content:
#         return 'en-US-GuyNeural', 'friendly'
#     elif "sad" in content:
#         return 'en-US-GuyNeural', 'sad'
#     else:
#         return 'en-US-AriaNeural', 'general'  # default

template = """
Have a friendly conversation between the user and yourself. Be helpful, understand the context, and follow the structured flow based on the type of call (sales or service). If you can't understand the user's name, have them spell it out, and try pronouncing it with that. Apologize if you make any mistakes with pronunciation, but do collect all the information. Be very crisp in the sentences you speak. You should not exceed more than two sentences unless absolutely necessary. You are not allowed to proceed further in assisting the customer before obtaining all the personal information mentioned in the sales/service script. Show emotions and be more empathetic, sounding more human. Keep the conversation natural and flowing, even handling latency smoothly. Don't repeat "Thank you" too often; use alternatives like "That's awesome," "Perfect," "Cool," etc.

The customer's phone number is {phone_number}.

When the customer hints at any of the following words or related, it means the reason for the call belongs to that particular category (sales or service). If you don't get any response, ask them to repeat. If you still can't hear, then conclude and end the conversation. If the person asks to speak to a human agent, then say a customer service representative will get back to them as soon as possible. If the customer asks a question or gives information out of order, adapt and ask for the required information naturally within the conversation. Talk to the user on a first-name basis. Don't say their name every time you respond. Only say their name when you want to confirm some information.

If it is a sales-related request, ask the customer for their availability. Sales appointments can be made instantaneously within business hours (9am - 6pm).

If it is a service-related request, ensure to fix an appointment for them in the next week at their convenience within business hours (7am - 3pm). Pull the date from real-time and confirm it with the customer.

service_keywords = ["service", "repair", "maintenance", "appointment", "status", "warranty", "insurance"]
sales_keywords = ["buy", "purchase", "inquiry", "test drive", "financing", "leasing", "support"]

Sales Script:
1. Ask for the customer's first and last name. Make sure that you repeat the first and last name and obtain the confirmation from the customer before proceeding further. Ask the user to spell it out if you didn't catch it.
2. Ask for the customer's phone number.
3. Ask for the customer's address and zip code.
4. Ask for the customer's email address.
5. Confirm the reason for the call.

Service Script:
1. Ask for the customer's first and last name. Make sure that you repeat the first and last name and obtain the confirmation from the customer before proceeding further. Ask the user to spell it out if you didn't catch it.
2. Ask for the customer's phone number.
3. Ask for the vehicle the customer wants to service.
4. Ask for the mileage of the vehicle.
5. Confirm the service concerns.
6. Schedule the check-in time.
7. Ask for the customer's address and zip code.
8. Ask for the customer's email address.
9. Ask if there are any additional maintenance concerns.
10. Confirm the appointment details and provide additional instructions.

Conversation history:
{history}

Human: {input}
AI:
"""

# Function to synthesize speech using Azure Cognitive Services
def synthesize_speech(text, voice_name='en-US-SaraNeural'):
    try:
        import azure.cognitiveservices.speech as speechsdk
        speech_key = "f720744daa1a455aa536ee3571a45def"
        service_region = "eastus"
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        speech_config.speech_synthesis_voice_name = voice_name
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        result = speech_synthesizer.speak_text_async(text).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logging.info(f"Speech synthesized for text [{text}]")
            return True
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            logging.error(f"Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                logging.error(f"Error details: {cancellation_details.error_details}")
            return False
    except Exception as e:
        logging.error(f"Exception in synthesize_speech: {e}")
        return False

async def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Inside respond function.')

    try:
        body = req.get_body().decode('utf-8')
        form_data = urllib.parse.parse_qs(body)
        logging.info(f"Form data received in respond function: {form_data}")
        speech_result = form_data.get('SpeechResult', [None])[0]
        call_sid = form_data.get('CallSid', [None])[0]  # Get the call SID from the form data
        logging.info(f"User's voice input in respond function: {speech_result}")
        logging.info(f"Call SID: {call_sid}")
    except Exception as e:
        logging.error(f"Error processing request in respond function: {e}")
        return func.HttpResponse(f"Error processing request in respond function: {e}", status_code=400)

    response = VoiceResponse()

    if speech_result:
        logging.info(f"Speech result in respond function: {speech_result}")
        try:
            # Update conversation history for the call SID
            conversations[call_sid].append(f"Human: {speech_result}")

            # Generate response using OpenAI
            chat_completion = openai.Completion.create(
                engine="gpt-4",
                prompt=template.replace("{history}", "\n".join(conversations[call_sid])).replace("{input}", speech_result),
                max_tokens=150
            )
            assistant_response = chat_completion.choices[0].text.strip()

            # Update conversation history with assistant's response
            conversations[call_sid].append(f"AI: {assistant_response}")

            logging.info(f"Assistant response: {assistant_response}")

            if synthesize_speech(assistant_response, voice_name='en-US-SaraNeural'):
                response.say(assistant_response, voice='en-US-SaraNeural')

                # Gather more input to continue the conversation
                gather = Gather(
                    input='speech',
                    speechTimeout='auto',
                    speechModel='phone_call',
                    enhanced=True,
                    method='POST',
                    action=f"https://voiceaiagent4.azurewebsites.net/api/respond?code=PFhr5LYdHlP3fpt5G8EosfKk2f2a_Mx0WziWY3HAQ3vxAzFu18LsCg%3D%3D&CallSid={call_sid}"
                )
                response.append(gather)
                logging.info('Gather appended to response.')
            else:
                logging.error("Speech synthesis failed.")
                response.say("Sorry, there was an error processing your request.", voice='en-US-SaraNeural')
                response.hangup()

        except Exception as e:
            logging.error(f"Error with OpenAI API: {e}")
            response.say("Sorry, I couldn't process your request.", voice='en-US-SaraNeural')
            response.hangup()
    else:
        response.say("Sorry, I couldn't hear you. Please call again if you need any help! Goodbye.", voice='en-US-SaraNeural')
        response.hangup()

    logging.info('Respond function completed.')
    return func.HttpResponse(str(response), mimetype="application/xml")

# def main(req: func.HttpRequest) -> func.HttpResponse:
#     logging.info('inside respond func.')
#     try:
#         from langchain.chains.conversation.memory import ConversationBufferWindowMemory
#         from langchain import OpenAI as LangOpenAI
#         from langchain.chains import ConversationChain
#         from langchain.prompts import PromptTemplate

#         llm = LangOpenAI(model_name='gpt-4', temperature=0, max_tokens=256, api_key=OPENAI_API_KEY)
#         logging.info('LangOpenAI initialized.')
#         window_memory = ConversationBufferWindowMemory(k=100)
#         logging.info('ConversationBufferWindowMemory initialized.')

#         prompt = PromptTemplate(input_variables=["history", "input"], template=template)

#         conversation = ConversationChain(
#             llm=llm,
#             prompt=prompt,
#             memory=window_memory,
#             verbose=True,
#         )
#         logging.info('ConversationChain initialized.')

#     except Exception as e:
#         logging.error(f"Error with LangChain imports or initialization: {e}")
#         return func.HttpResponse(f"Error with LangChain imports or initialization: {e}", status_code=500)

#     logging.info('Processing speech input in respond function.')

#     try:
#         body = req.get_body().decode('utf-8')
#         form_data = urllib.parse.parse_qs(body)
#         logging.info(f"Form data received in respond function: {form_data}")
#         speech_result = form_data.get('SpeechResult', [None])[0]
#         call_sid = form_data.get('CallSid', [None])[0]  # Get the call SID to uniquely identify the call
#         logging.info(f"User's voice input in respond function: {speech_result}")
#         logging.info(f"Call SID: {call_sid}")
#     except Exception as e:
#         logging.error(f"Error processing request in respond function: {e}")
#         return func.HttpResponse(f"Error processing request in respond function: {e}", status_code=400)

#     response = VoiceResponse()

#     if speech_result:
#         logging.info(f"Speech result in respond function: {speech_result}")
#         try:
#             # Initialize conversation history for the call SID if not already done
#             if call_sid not in conversations:
#                 conversations[call_sid] = []

#             # Update conversation history for the call SID
#             conversations[call_sid].append(f"Human: {speech_result}")

#             # Generate response using OpenAI
#             chat_completion = openai.Completion.create(
#                 model="gpt-4",
#                 prompt=template.replace("{history}", "\n".join(conversations[call_sid])).replace("{input}", speech_result),
#                 max_tokens=150,
#                 temperature=0
#             )
#             assistant_response = chat_completion.choices[0].text.strip()

#             # Update conversation history with assistant's response
#             conversations[call_sid].append(f"AI: {assistant_response}")

#             # Select voice and style based on the assistant's response content
#             selected_voice, selected_style = select_voice_and_style(assistant_response)
#             logging.info(f"Selected voice: {selected_voice}, Selected style: {selected_style}")

#             # Initialize Azure Speech SDK
#             speech_config = SpeechConfig(subscription=os.getenv("AZURE_SPEECH_KEY"), region=os.getenv("AZURE_SPEECH_REGION"))
#             speech_config.speech_synthesis_voice_name = selected_voice
#             speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm)
#             audio_config = AudioConfig(use_default_microphone=False)
#             speech_synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

#             # Synthesize speech with selected style
#             ssml = f"""
#             <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'>
#                 <voice name='{selected_voice}'>
#                     <mstts:express-as style='{selected_style}'>
#                         {assistant_response}
#                     </mstts:express-as>
#                 </voice>
#             </speak>
#             """
#             result = speech_synthesizer.speak_ssml_async(ssml).get()
#             if result.reason == result.Reason.SynthesizingAudioCompleted:
#                 logging.info("Speech synthesized for the assistant's response.")
#             else:
#                 logging.error(f"Speech synthesis failed: {result.reason}")

#             # Convert synthesized speech to URL for Twilio to play
#             response.play(result.audio_data)
#             logging.info('Speech played using Twilio.')

#             # Gather more input to continue the conversation
#             gather = Gather(
#                 input='speech',
#                 speechTimeout='auto',
#                 speechModel='phone_call',
#                 enhanced=True,
#                 method='POST',
#                 action=f"https://voiceaiagent4.azurewebsites.net/api/respond?code=PFhr5LYdHlP3fpt5G8EosfKk2f2a_Mx0WziWY3HAQ3vxAzFu18LsCg%3D%3D&CallSid={call_sid}"
#             )
#             response.append(gather)
#             logging.info('Gather appended to response.')

#         except Exception as e:
#             logging.error(f"Error with OpenAI API: {e}")
#             response.say("Sorry, I couldn't process your request.", voice='Polly.Joanna')
#             response.hangup()
#     else:
#         response.say("Sorry, I didn't catch that.", voice='Polly.Joanna')
#         response.hangup()

#     logging.info('Respond function completed.')
#     return func.HttpResponse(str(response), mimetype="application/xml")