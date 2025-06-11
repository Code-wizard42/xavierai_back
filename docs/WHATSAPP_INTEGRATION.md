# WhatsApp Integration for Xavier AI

This guide explains how to set up WhatsApp integration for your Xavier AI chatbot using Twilio's WhatsApp API.

## Prerequisites

1. A Twilio account (you can sign up for a free trial at [twilio.com](https://www.twilio.com/try-twilio))
2. A WhatsApp-enabled phone number (for testing)
3. The Xavier AI backend and frontend running

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements-whatsapp.txt
```

2. Set up environment variables:

```bash
# Twilio credentials
export TWILIO_ACCOUNT_SID=your_account_sid
export TWILIO_AUTH_TOKEN=your_auth_token
export TWILIO_WHATSAPP_NUMBER=your_whatsapp_number
```

## Setting Up Twilio WhatsApp Sandbox

1. Log in to your Twilio account
2. Navigate to Messaging > Try it Out > Try WhatsApp
3. Follow the instructions to join your WhatsApp sandbox
4. Configure the webhook URL for incoming messages to point to your Xavier AI backend:
   - Set the webhook URL to: `https://your-domain.com/whatsapp/webhook`
   - Make sure the request method is set to `HTTP POST`

## Configuring WhatsApp Integration in Xavier AI

1. Log in to your Xavier AI dashboard
2. Select the chatbot you want to integrate with WhatsApp
3. Click on the "WhatsApp" tab in the sidebar
4. Enter your Twilio credentials:
   - Account SID
   - Auth Token
   - WhatsApp Number (with country code, e.g., +14155238886)
5. Click "Save Configuration"

## Testing the Integration

1. Send a message to your Twilio WhatsApp number
2. The message will be processed by your Xavier AI chatbot
3. The response will be sent back to your WhatsApp number

## Troubleshooting

If you encounter issues with the WhatsApp integration, check the following:

1. Verify that your Twilio credentials are correct
2. Make sure your webhook URL is accessible from the internet
3. Check the Xavier AI backend logs for any errors
4. Ensure that your Twilio WhatsApp sandbox is properly set up

## Production Use

For production use, you'll need to request access to the WhatsApp Business API through Twilio. This requires approval from WhatsApp and may take some time.

1. Go to [Twilio WhatsApp API](https://www.twilio.com/whatsapp/request-access)
2. Fill out the form to request production access
3. Once approved, update your WhatsApp number in the Xavier AI dashboard

## Support

If you need help with the WhatsApp integration, please contact support at support@xavierai.site.
