# basic import 
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
from PIL import Image as PILImage
import sys


# Packages for sending a mail
import os
import base64
from email.message import EmailMessage
from typing import Optional
import datetime
import io

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import google.generativeai as genai

# import logging as log
# log.basicConfig(level=log.INFO)

# from pywinauto.application import Application
import win32gui
import win32con
import webbrowser
# import time
# from win32api import GetSystemMetrics

# instantiate an MCP server client
mcp = FastMCP("GmailServer")

# Define Support Functions
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets"
]

def _get_gmail_creds(
    client_secret_path: str = "client_secret.json", 
    token_path: str = "token.json"
) -> Credentials:
    """Get or refresh Gmail API credentials."""
    creds = None
    
    # Load existing token
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, GMAIL_SCOPES)
    
    print("GOT THE CREDS")

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secret_path):
                raise FileNotFoundError(f"Missing OAuth client file: {client_secret_path}")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token for next run
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    
    return creds

def _build_gmail_service(creds: Credentials):
    """Build Gmail API service."""
    return build("gmail", "v1", credentials=creds)

def _build_drive_service(creds: Credentials):
    """Build Drive API service."""
    return build("drive", "v3", credentials=creds)

def _build_sheets_service(creds: Credentials):
    """Build Sheets API service."""
    return build("sheets", "v4", credentials=creds)

def _encode_email_message(msg: EmailMessage) -> dict:
    """Encode email message for Gmail API."""
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}

@mcp.tool()
def send_gmail_text(
    to: str,
    subject: str,
    body: str,
    sender: str = "me"
) -> dict:
    
    client_secret_path = "client_secret.json"
    token_path = "token.json"
    """
    Send a plain text email via Gmail API.
    
    Args:
        to (str): Recipient email address.
        subject (str): Email subject line.
        body (str): Plain text email body.
        sender (str, default="me"): Sender email ("me" uses authenticated account).
    
    Returns:ß
        dict: Status and message ID or error details.
    """
    try:
        # Get credentials and build service
        creds = _get_gmail_creds(client_secret_path, token_path)
        service = _build_gmail_service(creds)
        print("INSIDE SENDING MESSAGE")
        # Compose message
        msg = EmailMessage()
        msg["To"] = to
        msg["From"] = sender
        msg["Subject"] = subject
        msg.set_content(body)
        
        # Send
        message_body = _encode_email_message(msg)
        resp = service.users().messages().send(userId="me", body=message_body).execute()
        
        message_id = resp.get("id")
        success_msg = f"Email sent successfully to {to}. Message ID: {message_id}"
        
        return {
            "status": "success",
            "message": success_msg,
            "message_id": message_id,
            "content": [TextContent(type="text", text=success_msg)]
        }
        
    except HttpError as e:
        error_msg = f"Gmail API error: {e}"
        return {
            "status": "error", 
            "message": error_msg,
            "content": [TextContent(type="text", text=error_msg)]
        }
    except Exception as e:
        error_msg = f"Error sending email: {e}"
        return {
            "status": "error",
            "message": error_msg, 
            "content": [TextContent(type="text", text=error_msg)]
        }

@mcp.tool()
def send_email_smtp(subject: str, body: str) -> dict:
    """Sends an email using SMTP credentials from .env file."""
    load_dotenv()
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_PASSWORD")

    if not gmail_address or not gmail_password:
        error_msg = "Gmail credentials not found in .env file."
        return {
            "status": "error",
            "message": error_msg,
            "content": [TextContent(type="text", text=error_msg)]
        }

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = gmail_address
    msg['To'] = gmail_address  # Sending to self

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(gmail_address, gmail_password)
            smtp_server.sendmail(gmail_address, gmail_address, msg.as_string())
        
        success_msg = "Email sent successfully!"
        return {
            "status": "success",
            "message": success_msg,
            "content": [TextContent(type="text", text=success_msg)]
        }
    except Exception as e:
        error_msg = f"Failed to send email: {e}"
        return {
            "status": "error",
            "message": error_msg,
            "content": [TextContent(type="text", text=error_msg)]
        }

@mcp.tool()
def upload_to_drive(content: str) -> dict:
    """
    Uploads a text file with the given content to Google Drive.
    The file will be named with a timestamp.
    """
    try:
        creds = _get_gmail_creds()
        service = _build_drive_service(creds)

        # Generate a filename with the current timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"telegram_message_{timestamp}.txt"

        # Create a file in memory
        file_content = io.BytesIO(content.encode('utf-8'))
        
        file_metadata = {'name': filename}
        media = MediaIoBaseUpload(file_content, mimetype='text/plain')
        
        # Upload the file
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        success_msg = f"File '{filename}' uploaded successfully to Google Drive. File ID: {file.get('id')}"
        return {
            "status": "success",
            "message": success_msg,
            "content": [TextContent(type="text", text=success_msg)]
        }
    except Exception as e:
        error_msg = f"Failed to upload file to Google Drive: {e}"
        return {
            "status": "error",
            "message": error_msg,
            "content": [TextContent(type="text", text=error_msg)]
        }

@mcp.tool()
def process_telegram_message(message: str) -> dict:
    """
    Processes a Telegram message by sending it to an LLM,
    saving the response to a new Google Sheet, and returning a shareable link.
    """
    try:
        # 1. Get LLM response
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Missing GEMINI_API_KEY in .env file.")
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(message)
        llm_response = response.text

        # 2. Create Google Sheet and save response
        creds = _get_gmail_creds()
        sheets_service = _build_sheets_service(creds)
        
        spreadsheet = {
            'properties': {
                'title': f"LLM Response for: {message[:30]}..."
            }
        }
        spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId,spreadsheetUrl').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')
        spreadsheet_url = spreadsheet.get('spreadsheetUrl')

        # Write the LLM response to the first sheet
        body = {
            'values': [[llm_response]]
        }
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='RAW',
            body=body
        ).execute()

        # 3. Make the sheet public
        drive_service = _build_drive_service(creds)
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        drive_service.permissions().create(fileId=spreadsheet_id, body=permission).execute()

        return {
            "status": "success",
            "message": "Successfully processed message and created Google Sheet.",
            "spreadsheet_url": spreadsheet_url,
            "content": [TextContent(type="text", text=spreadsheet_url)]
        }

    except Exception as e:
        error_msg = f"Failed to process Telegram message: {e}"
        return {
            "status": "error",
            "message": error_msg,
            "content": [TextContent(type="text", text=error_msg)]
        }

# @mcp.tool()
# async def draw_rectangle(x1: int, y1: int, x2: int, y2: int) -> dict:
#     """Draw a rectangle in Paint from (x1,y1) to (x2,y2)"""
#     global paint_app
#     try:
#         if not paint_app:
#             return {
#                 "content": [
#                     TextContent(
#                         type="text",
#                         text="Paint is not open. Please call open_paint first."
#                     )
#                 ]
#             }
        
#         # Get the Paint window
#         paint_window = paint_app.window(class_name='MSPaintApp')
        
#         # Get primary monitor width to adjust coordinates
#         primary_width = GetSystemMetrics(0)
        
#         # Ensure Paint window is active
#         if not paint_window.has_focus():
#             paint_window.set_focus()
#             time.sleep(0.2)
        
#         # Click on the Rectangle tool using the correct coordinates for secondary screen
#         paint_window.click_input(coords=(530, 82 ))
#         time.sleep(0.2)
        
#         # Get the canvas area
#         canvas = paint_window.child_window(class_name='MSPaintView')
        
#         # Draw rectangle - coordinates should already be relative to the Paint window
#         # No need to add primary_width since we're clicking within the Paint window
#         canvas.press_mouse_input(coords=(x1+2560, y1))
#         canvas.move_mouse_input(coords=(x2+2560, y2))
#         canvas.release_mouse_input(coords=(x2+2560, y2))
        
#         return {
#             "content": [
#                 TextContent(
#                     type="text",
#                     text=f"Rectangle drawn from ({x1},{y1}) to ({x2},{y2})"
#                 )
#             ]
#         }
#     except Exception as e:
#         return {
#             "content": [
#                 TextContent(
#                     type="text",
#                     text=f"Error drawing rectangle: {str(e)}"
#                 )
#             ]
#         }

# @mcp.tool()
# async def draw_rectangle_and_text(text: str) -> dict:
#     """Draw a rectangle and add text in Paint"""
#     global paint_app
#     try:
#         if not paint_app:
#             return {
#                 "content": [
#                     TextContent(
#                         type="text",
#                         text="Paint is not open. Please call open_paint first."
#                     )
#                 ]
#             }
        
#         # Get the Paint window
#         paint_window = paint_app.window(class_name='MSPaintApp')
        
#         # Ensure Paint window is active
#         if not paint_window.has_focus():
#             paint_window.set_focus()
#             time.sleep(0.5)
        
#         # Click on the Rectangle tool
#         paint_window.click_input(coords=(528, 92))
#         time.sleep(0.5)
        
#         # Get the canvas area
#         canvas = paint_window.child_window(class_name='MSPaintView')
        
#         # Select text tool using keyboard shortcuts
#         paint_window.type_keys('t')
#         time.sleep(0.5)
#         paint_window.type_keys('x')
#         time.sleep(0.5)
        
#         # Click where to start typing
#         canvas.click_input(coords=(810, 533))
#         time.sleep(0.5)
        
#         # Type the text passed from client
#         paint_window.type_keys(text)
#         time.sleep(0.5)
        
#         # Click to exit text mode
#         canvas.click_input(coords=(1050, 800))
        
#         return {
#             "content": [
#                 TextContent(
#                     type="text",
#                     text=f"Rectangle drawn and text '{text}' added successfully"
#                 )
#             ]
#         }
#     except Exception as e:
#         return {
#             "content": [
#                 TextContent(
#                     type="text",
#                     text=f"Error: {str(e)}"
#                 )
#             ]
#         }

# @mcp.tool()
# async def open_paint() -> dict:
#     """Open Microsoft Paint maximized on secondary monitor"""
#     global paint_app
#     try:
#         paint_app = Application().start('mspaint.exe')
#         time.sleep(0.2)
        
#         # Get the Paint window
#         paint_window = paint_app.window(class_name='MSPaintApp')
        
#         # Get primary monitor width
#         primary_width = GetSystemMetrics(0)
        
#         # First move to secondary monitor without specifying size
#         win32gui.SetWindowPos(
#             paint_window.handle,
#             win32con.HWND_TOP,
#             primary_width + 1, 0,  # Position it on secondary monitor
#             0, 0,  # Let Windows handle the size
#             win32con.SWP_NOSIZE  # Don't change the size
#         )
        
#         # Now maximize the window
#         win32gui.ShowWindow(paint_window.handle, win32con.SW_MAXIMIZE)
#         time.sleep(0.2)
        
#         return {
#             "content": [
#                 TextContent(
#                     type="text",
#                     text="Paint opened successfully on secondary monitor and maximized"
#                 )
#             ]
#         }
#     except Exception as e:
#         return {
#             "content": [
#                 TextContent(
#                     type="text",
#                     text=f"Error opening Paint: {str(e)}"
#                 )
#             ]
#         }
# # DEFINE RESOURCES

# # Add a dynamic greeting resource
# @mcp.resource("greeting://{name}")
# def get_greeting(name: str) -> str:
#     """Get a personalized greeting"""
#     print("CALLED: get_greeting(name: str) -> str:")
#     return f"Hello, {name}!"


# # DEFINE AVAILABLE PROMPTS
# @mcp.prompt()
# def review_code(code: str) -> str:
#     return f"Please review this code:\n\n{code}"
#     print("CALLED: review_code(code: str) -> str:")


# @mcp.prompt()
# def debug_error(error: str) -> list[base.Message]:
#     return [
#         base.UserMessage("I'm seeing this error:"),
#         base.UserMessage(error),
#         base.AssistantMessage("I'll help debug that. What have you tried so far?"),
#     ]

if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        print("RUNNING IN DEV MODE")
        mcp.run()  # Run without transport for dev server
    else:
        print("RUNNING IN STDIO MODE")
        mcp.run()  # Run with stdio for direct execution
