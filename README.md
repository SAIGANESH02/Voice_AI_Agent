# Voice AI Agent for Automotive Dealerships

A sophisticated Azure Functions-based voice AI agent that handles incoming calls for automotive dealerships, providing intelligent customer service and sales support through natural language conversations powered by OpenAI GPT-4.

## 🎯 Overview

This Voice AI Agent, named **Pam**, serves as a virtual assistant for automotive dealerships, handling both sales and service inquiries. The system integrates with Twilio for voice communication, OpenAI GPT-4 for conversational AI, and MySQL for data persistence and analytics.

## ✨ Key Features

### 🤖 Intelligent Conversational AI
- **Natural Language Processing**: Powered by OpenAI GPT-4 for human-like conversations
- **Emotional Intelligence**: Expresses emotions (excitement, empathy, surprise) naturally in responses
- **Context Awareness**: Maintains conversation context using LangChain's ConversationBufferWindowMemory
- **Multi-language Support**: Familiar with English, Spanish, French, Russian, Hindi, and Chinese
- **Crisp Communication**: Keeps responses concise (typically 1-2 sentences) for better phone conversations

### 📞 Call Handling
- **Incoming Call Management**: Handles incoming calls via Twilio with custom greetings
- **Speech Recognition**: Uses Twilio's enhanced speech recognition with phone_call model
- **Dynamic Speech Timeout**: Adjusts speech timeout based on input length for optimal user experience
- **Barge-in Support**: Allows users to interrupt the AI mid-speech
- **Multiple Retry Attempts**: Handles no-response scenarios with graceful fallbacks

### 🏢 Multi-Dealership Support
- **Dealership Mapping**: Supports 50+ dealerships with unique phone number routing
- **Department-Specific Flows**: Separate conversation flows for Sales and Service departments
- **Custom Greetings**: Personalized greetings based on dealership name
- **Transfer Routing**: Automatic call transfer to appropriate human representatives

### 💾 Data Management
- **Conversation Persistence**: Stores complete conversation transcripts in MySQL database
- **Information Extraction**: Automatically extracts customer information from conversations:
  - First and Last Name
  - Phone Number
  - Car Make, Model, and Year
  - Appointment Date
  - Service Category and Sub-category
  - Additional Notes
- **Call Analytics**: Tracks call duration, coverage percentage, completion rates, and peak call times

### 🎯 Sales Flow
1. Greets customer and explains connection to representative
2. Collects first and last name (with spelling confirmation)
3. Gathers phone number
4. Identifies what customer wants to buy
5. Transfers to sales representative

### 🔧 Service Flow
1. Collects customer name (with spelling confirmation)
2. Gathers phone number
3. Identifies vehicle details (year, make, model)
4. Collects vehicle mileage
5. Confirms service concerns
6. Schedules appointment (within business hours, 7am-3pm)
7. Asks about additional maintenance concerns
8. Confirms preferred appointment date and time
9. Sets up reminder preferences (phone/text)
10. Ends with friendly closing

### 🔄 Call Transfer Intelligence
- **Smart Transfer Detection**: Uses GPT-4 to analyze customer intent for transfer requests
- **Explicit Request Handling**: Only transfers when customer explicitly requests human representative
- **Transfer Keywords**: Recognizes phrases like "talk to a representative", "connect me to a human", "advisor", "mechanic"
- **Seamless Handoff**: Smooth transfer to appropriate department representative

### 📊 Analytics & Reporting
- **Call Duration Tracking**: Monitors total call duration
- **Coverage Percentage**: Calculates percentage of required information collected
- **Call Completion Rate**: Tracks successful call completions
- **Peak Call Times**: Identifies busiest call periods
- **Dealership Metrics**: Per-dealership analytics and reporting

### 🛡️ Error Handling
- **Graceful Degradation**: Handles errors without disrupting user experience
- **Retry Logic**: Multiple fallback attempts for failed operations
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **Database Error Recovery**: Handles database connection issues gracefully

## 🏗️ Architecture

### Azure Functions Endpoints

#### 1. `/api/incomingcall`
- **Method**: POST, GET
- **Purpose**: Handles initial incoming call setup
- **Features**:
  - Identifies dealership from caller's phone number
  - Generates personalized greeting
  - Initiates speech gathering with Twilio Gather

#### 2. `/api/respond`
- **Method**: POST
- **Purpose**: Processes user speech input and generates AI responses
- **Features**:
  - Loads conversation history from database
  - Generates contextual AI responses
  - Determines call type (Sales/Service)
  - Handles transfer requests
  - Manages hangup scenarios
  - Saves conversation updates

#### 3. `/api/callstatus`
- **Method**: POST
- **Purpose**: Tracks call status changes and finalizes call data
- **Features**:
  - Monitors call completion
  - Extracts information from full conversation
  - Calculates analytics metrics
  - Stores data in database

### Database Schema

#### `transcripts` Table
- `call_sid`: Unique call identifier
- `transcript`: Full conversation history

#### `ai_inbound_info` Table
- `dealer_id`: Dealership identifier
- `first_name`, `last_name`: Customer information
- `phone_number`: Contact information
- `car_year`, `make`, `model`: Vehicle details
- `appointment`: Scheduled appointment date
- `category`, `sub_category`: Service categorization
- `notes`: Additional information
- `call_duration`: Call length in seconds
- `coverage_percentage`: Information collection rate
- `call_completion_rate`: Success rate
- `dealership_name`: Dealership identifier
- `peak_call_times`: Busiest call periods

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- Azure Functions Core Tools
- MySQL database
- Twilio account
- OpenAI API key

### Environment Variables

Configure the following environment variables in `local.settings.json` (for local development) or Azure Function App settings:

```json
{
  "TWILIO_ACCOUNT_SID": "your_twilio_account_sid",
  "TWILIO_AUTH_TOKEN": "your_twilio_auth_token",
  "OPENAI_API_KEY": "your_openai_api_key",
  "AZURE_STORAGE_CONNECTION_STRING": "your_azure_storage_connection_string"
}
```

### Database Configuration

Update the MySQL connection configuration in `function_app.py`:

```python
config = {
    'user': 'your_db_user',
    'password': 'your_db_password',
    'host': 'your_db_host',
    'database': 'your_database_name',
    'raise_on_warnings': True
}
```

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Voice_AI_Agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   - Update `local.settings.json` with your credentials
   - Or set environment variables in Azure Function App

4. **Set up database**
   - Create MySQL database
   - Create required tables (`transcripts`, `ai_inbound_info`)

5. **Deploy to Azure Functions**
   ```bash
   func azure functionapp publish <your-function-app-name>
   ```

6. **Configure Twilio Webhooks**
   - Set incoming call webhook to: `https://your-function-app.azurewebsites.net/api/incomingcall?code=<function-key>`
   - Configure status callbacks as needed

## 📁 Project Structure

```
Voice_AI_Agent/
├── function_app.py          # Main application logic
├── config.py                # Configuration management
├── ai_helpers.py           # AI helper functions
├── requirements.txt        # Python dependencies
├── host.json              # Azure Functions host configuration
├── local.settings.json    # Local development settings
├── incomingcall/          # Incoming call function
│   ├── __init__.py
│   └── function.json
├── respond/               # Response handling function
│   ├── __init__.py
│   └── function.json
└── README.md             # This file
```

## 🔧 Configuration

### Dealership Configuration

The `phone_to_dealership` dictionary maps phone numbers to dealership information:

```python
phone_to_dealership = {
    '+14709151551': {
        'name': 'Shravan Car Service',
        'department': 'Sales',
        'transfer': '+18723344517'
    },
    # ... more dealerships
}
```

### Speech Timeout Configuration

Dynamic speech timeout based on input length:
- Short inputs (< 10 chars): 3 seconds
- Medium inputs (< 30 chars): 2 seconds
- Long inputs: Auto timeout

### Prompt Templates

The system uses specialized prompt templates for:
- **Sales conversations**: Focused on purchase inquiries and product information
- **Service conversations**: Focused on appointment scheduling and vehicle service

## 🎨 Customization

### Modifying Conversation Flows

Edit the prompt templates in `function_app.py`:
- `sales_prompt_template`: Sales conversation guidelines
- `service_prompt_template`: Service conversation guidelines

### Adding New Dealerships

Add entries to the `phone_to_dealership` dictionary with:
- Phone number (key)
- Dealership name
- Department (Sales/Service)
- Transfer number

### Adjusting AI Behavior

Modify the prompt templates to:
- Change conversation style
- Add new information collection steps
- Adjust emotional tone
- Update business rules

## 📈 Monitoring & Analytics

### Logging

The application provides comprehensive logging:
- Call initiation and completion
- Conversation history updates
- Transfer decisions
- Database operations
- Error tracking

### Metrics Tracked

- Call duration
- Information coverage percentage
- Call completion rate
- Peak call times
- Dealership-specific metrics

## 🔒 Security

- **Function-level Authentication**: All endpoints use function-level auth keys
- **Environment Variables**: Sensitive data stored in environment variables
- **Database Security**: MySQL connection with credentials
- **API Key Protection**: OpenAI and Twilio keys secured

## 🐛 Troubleshooting

### Common Issues

1. **No response from AI**
   - Check OpenAI API key configuration
   - Verify API quota and billing

2. **Database connection errors**
   - Verify MySQL credentials
   - Check network connectivity
   - Ensure database is accessible

3. **Twilio call failures**
   - Verify Twilio credentials
   - Check webhook URLs
   - Validate phone number formats

4. **Conversation history not loading**
   - Check database connection
   - Verify call_sid is being passed correctly
   - Review database table structure

## 🔮 Future Enhancements

Potential improvements:
- Real-time dashboard for call monitoring
- Advanced analytics and reporting
- Integration with CRM systems
- Multi-language voice support
- Sentiment analysis
- Call quality scoring
- Automated follow-up scheduling

**Built with ❤️ using Azure Functions, Twilio, OpenAI GPT-4, and MySQL**
