from google import genai
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

async def main():
    # Load environment variables from a local .env file if present.
    load_dotenv()

    # Prefer GEMINI_API_KEY; fall back to GOOGLE_API_KEY for compatibility.
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing API key. Set GEMINI_API_KEY or GOOGLE_API_KEY in your environment."
        )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents="Explain how AI works in a few words"
    )
    print(response.text)

    # Send the email using the MCP tool
    server_params = StdioServerParameters(
        command="python",
        args=["gmail_mcp_server.py"]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "send_email_smtp",
                    arguments={
                        "subject": "AI Generated Content",
                        "body": response.text
                    }
                )
                if hasattr(result, 'content') and result.content:
                    print(result.content[0].text)
                else:
                    print(result)
    except Exception as e:
        print(f"Failed to send email via MCP: {e}")

if __name__ == "__main__":
    asyncio.run(main())
