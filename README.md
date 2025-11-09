# Telegram to Google Workspace Integration Server

## Project Overview

This server provides a powerful integration between Telegram and Google Workspace, augmented with AI capabilities. It actively listens for new messages in a specified Telegram channel, processes them using a Large Language Model (LLM), and then automates a series of actions within Google Workspace.

## Features

- **Telegram Channel Listener:** Connects to a Telegram channel and listens for new messages in real-time.
- **AI-Powered Processing:** Each message from Telegram is sent as a prompt to the Gemini LLM to generate a detailed response.
- **Google Sheets Integration:** The LLM's response is automatically saved into a new, dedicated Google Sheet.
- **Google Drive Integration:** The newly created Google Sheet is made publicly accessible with a shareable link.
- **Gmail Notifications:** An email is automatically sent with the shareable link to the Google Sheet.
- **Real-time Web Updates (SSE):** The original Telegram message is broadcasted via a Server-Sent Events (SSE) endpoint, allowing web clients to receive live updates.

## Prerequisites

- Python 3.8+
- `pip` for package management

## Setup Instructions

### 1. Install Python Dependencies

First, install all the required Python packages by running the following command in your terminal:

```bash
pip install telethon python-dotenv fastapi uvicorn google-generativeai google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 2. Configure Telegram API Credentials

You need to get your own API credentials from Telegram to allow the application to connect to your account.

1.  Go to [my.telegram.org](https://my.telegram.org) and log in with your phone number.
2.  Click on "API development tools" and fill in the required details for your new application.
3.  You will be provided with an `api_id` and `api_hash`. Keep these safe.

### 3. Configure Google Cloud Platform and OAuth Credentials

To allow the server to access your Google Drive, Sheets, and Gmail, you need to create a project in the Google Cloud Console and generate credentials.

1.  **Go to the Google Cloud Console:** [https://console.cloud.google.com/](https://console.cloud.google.com/)
2.  **Create a new project** (or select an existing one).
3.  **Enable the necessary APIs:**
    -   Go to "APIs & Services" > "Library".
    -   Search for and enable the following APIs one by one:
        -   **Gmail API**
        -   **Google Drive API**
        -   **Google Sheets API**
4.  **Create OAuth Credentials:**
    -   Go to "APIs & Services" > "Credentials".
    -   Click "+ CREATE CREDENTIALS" and select "OAuth client ID".
    -   If prompted, configure the "OAuth consent screen". Choose "External" and fill in the required app name, user support email, and developer contact information.
    -   For the "Application type", select **"Desktop app"**.
    -   Give it a name (e.g., "Telegram Integration Client") and click "Create".
5.  **Download the Credentials File:**
    -   A window will pop up with your client ID and secret. Click the **"DOWNLOAD JSON"** button.
    -   Rename the downloaded file to `client_secret.json`.
    -   Move this `client_secret.json` file into the root of your project directory.

### 4. Create and Configure the `.env` File

Create a file named `.env` in the root of your project directory. This file will store all your secret credentials. Copy the following content into it and replace the placeholder values with your actual credentials.

```
# Gemini API Key
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

# Gmail Credentials (for sending email)
GMAIL_ADDRESS="your_email@gmail.com"
GMAIL_PASSWORD="your_gmail_app_password"

# Telegram API Credentials
API_ID=YOUR_TELEGRAM_API_ID
API_HASH=YOUR_TELEGRAM_API_HASH
PHONE=YOUR_PHONE_NUMBER_WITH_COUNTRY_CODE
```

**Note on `GMAIL_PASSWORD`:** It is highly recommended to use an "App Password" for your Google account, rather than your main password. You can generate one here: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

### 5. Configure the Target Telegram Channel

Open the `telegram_mcp_server.py` file and replace the placeholder value for the `TARGET_CHANNEL` variable with the username or ID of the Telegram channel you want to monitor.

```python
# in telegram_mcp_server.py
TARGET_CHANNEL = 'YourChannelUsername' 
```

## Running the Server

Once you have completed all the setup steps, you can start the server by running the following command in your terminal:

```bash
python telegram_mcp_server.py
```

The first time you run the server, it will:
1.  Ask you to log in to your Telegram account in the terminal.
2.  Open a new browser window asking you to log in to your Google account and grant the necessary permissions for Drive, Sheets, and Gmail. Please approve these requests.

The server will then be running and actively listening for new messages.

## How to Use

1.  **Send a Message:** Post a new message in the configured Telegram channel.
2.  **Check the Output:** The server's terminal will log its progress as it processes the message, generates an LLM response, creates a Google Sheet, and sends the email.
3.  **Check Your Email:** You will receive an email containing a shareable link to the newly created Google Sheet.
4.  **Access the SSE Stream (Optional):** You can see the original Telegram messages in real-time by navigating to `http://127.0.0.1:8000/events` in your web browser.
