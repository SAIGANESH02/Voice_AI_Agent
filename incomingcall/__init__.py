# import logging
# import azure.functions as func
# from twilio.twiml.voice_response import VoiceResponse, Gather

# ai_voice = 'en-US-AriaNeural'
# conversations = {}

# def main(req: func.HttpRequest) -> func.HttpResponse:
#     logging.info('Processing incoming call.')

#     response = VoiceResponse()
#     body = req.get_body().decode('utf-8')
#     form_data = urllib.parse.parse_qs(body)
#     incoming_phone_number = form_data.get('From', [None])[0]
#     call_sid = form_data.get('CallSid', [None])[0]  # Get the call SID to uniquely identify the call
#     logging.info(f"Incoming phone number: {incoming_phone_number}")
#     logging.info(f"Call SID: {call_sid}")

#     # Initialize conversation history for the call SID
#     if call_sid not in conversations:
#         conversations[call_sid] = []

#     response.say("Hello! It's a great day at Rossen Nissan, how can I help you?", voice=ai_voice)
#     gather = Gather(
#         input='speech',
#         speechTimeout='auto',
#         speechModel='phone_call',
#         enhanced=True,
#         method='POST',
#         action=f"https://voiceaiagent4.azurewebsites.net/api/respond?code=PFhr5LYdHlP3fpt5G8EosfKk2f2a_Mx0WziWY3HAQ3vxAzFu18LsCg%3D%3D&CallSid={call_sid}"
#     )
#     logging.info("Gather object created:")
#     logging.info(str(gather))
#     response.append(gather)
#     logging.info(str(response))

#     return func.HttpResponse(str(response), mimetype='application/xml')

import logging
import azure.functions as func
from twilio.twiml.voice_response import VoiceResponse, Gather
import urllib.parse

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
    logging.info('Processing incoming call.')

    response = VoiceResponse()
    phone_to_dealership = {
        '+12244638902': 'chethana claire Nissan',
        '+14709151551': 'shravan shrooov Nissan',
        '+16176754444':  'Sai Ganesh Nissan',
        '+12243308489': 'Dom Nissan',
    }

    try:
        body = req.get_body().decode('utf-8')
        form_data = urllib.parse.parse_qs(body)
        incoming_phone_number = form_data.get('From', [None])[0]
        call_sid = form_data.get('CallSid', [None])[0]  # Get the call SID to uniquely identify the call
        logging.info(f"Incoming phone number: {incoming_phone_number}")
        logging.info(f"Call SID: {call_sid}")

        dealership_name = phone_to_dealership.get(incoming_phone_number)
        logging.info(f"Dealership name is: {dealership_name}")
        greeting_message = f"It's a great day at {dealership_name} Rossen Nissan, my name is Johnny Storm. How can I be of service to you?"

        if synthesize_speech(greeting_message, voice_name='en-US-SaraNeural'):
            response.say(greeting_message, voice='en-US-SaraNeural')

            gather = Gather(
                input='speech',
                speechTimeout='auto',
                speechModel='phone_call',
                enhanced=True,
                method='POST',
                action=f"https://voiceaiagent4.azurewebsites.net/api/respond?code=PFhr5LYdHlP3fpt5G8EosfKk2f2a_Mx0WziWY3HAQ3vxAzFu18LsCg%3D%3D&CallSid={call_sid}"
            )
            logging.info("Gather object created:")
            logging.info(str(gather))
            response.append(gather)
            logging.info(str(response))
        else:
            logging.error("Speech synthesis failed.")
            response.say("Sorry, there was an error processing your call.", voice='en-US-SaraNeural')

    except Exception as e:
        logging.error(f"Error in incoming call: {e}")
        response.say("Sorry, I couldn't hear.", voice='en-US-SaraNeural')

    return func.HttpResponse(str(response), mimetype='application/xml')
