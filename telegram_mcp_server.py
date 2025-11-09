import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# New imports for the SSE web server
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

# Load environment variables from the .env file
load_dotenv()

# Get Telegram credentials from environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")

# --- IMPORTANT ---
# Replace with your target Telegram channel username or ID
TARGET_CHANNEL = 'AlpeshTestChannel' 

# Create the Telegram client
client = TelegramClient('telegram_session', API_ID, API_HASH)

# Create a queue to share messages between Telethon and FastAPI
message_queue = asyncio.Queue()

# Create the FastAPI app for the SSE server
app = FastAPI()

async def process_and_email_message(message_text):
    """
    Processes a Telegram message, gets a Google Sheet link, and emails it.
    """
    server_params = StdioServerParameters(
        command="python",
        args=["gmail_mcp_server.py"]
    )
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 1. Process the message to get the Google Sheet URL
                print("Calling Gmail MCP server to process message...")
                result = await session.call_tool(
                    "process_telegram_message",
                    arguments={"message": message_text}
                )
                
                spreadsheet_url = ""
                if hasattr(result, 'content') and result.content:
                    spreadsheet_url = result.content[0].text
                    print(f"Google Sheet created: {spreadsheet_url}")
                else:
                    print(f"Error creating Google Sheet: {result}")
                    return

                # 2. Send the email with the link
                email_subject = f"Response for your query: {message_text[:30]}..."
                email_body = f"Here is the link to the Google Sheet with the answer:\n{spreadsheet_url}"
                
                print("Calling Gmail MCP server to send email...")
                await session.call_tool(
                    "send_email_smtp",
                    arguments={
                        "subject": email_subject,
                        "body": email_body
                    }
                )
                print("Email sent successfully.")

    except Exception as e:
        print(f"Failed to process and email message via MCP: {e}")

@client.on(events.NewMessage(chats=TARGET_CHANNEL))
async def handler(event):
    """
    Event handler for new messages in the target channel.
    """
    message = event.raw_text
    print(f"New message received from {TARGET_CHANNEL}: {message}")
    
    # Put the message in the queue for SSE clients
    await message_queue.put(message)
    
    # Process the message and get a Google Sheet link
    await process_and_email_message(message)

@app.get("/")
async def root():
    """
    Root endpoint with a welcome message and instructions.
    """
    return {
        "message": "Telegram SSE server is running.",
        "sse_endpoint": "/events"
    }

@app.get("/events")
async def sse_endpoint(request: Request):
    """
    SSE endpoint to stream new messages to connected clients.
    """
    async def event_generator():
        while True:
            if await request.is_disconnected():
                print("Client disconnected.")
                break
            
            # Wait for a new message from the queue
            message = await message_queue.get()
            
            # Format as an SSE message and yield it
            yield f"data: {message}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

async def run_telethon_client():
    """
    Connects and runs the Telethon client.
    """
    await client.start(PHONE)
    print("Telegram client started. Listening for new messages...")
    await client.run_until_disconnected()

async def main():
    """
    Main function to run the FastAPI server and the Telethon client concurrently.
    """
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    
    telethon_task = asyncio.create_task(run_telethon_client())
    
    print("Starting FastAPI server on http://127.0.0.1:8000")
    await asyncio.gather(telethon_task, server.serve())

if __name__ == "__main__":
    print("Starting Telegram MCP Server with SSE...")
    try:
        asyncio.run(main())
    except (ValueError, TypeError) as e:
        print(f"Error: Could not connect to Telegram. Please ensure your API_ID, API_HASH, and PHONE are correctly set in the .env file.")
        print(f"Details: {e}")
    except ImportError:
        print("Error: Missing required packages. Please install them by running:")
        print("pip install telethon python-dotenv fastapi uvicorn google-generativeai")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
