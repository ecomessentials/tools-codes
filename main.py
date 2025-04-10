import asyncio
import os
import discord
from playwright.async_api import async_playwright
import pytz
from datetime import datetime

# Discord configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_TOPIC_ID_TO_SEND_CODE = int(
    os.getenv("DISCORD_CHANNEL_TOPIC_ID_TO_SEND_CODE", 0))
DISCORD_CHANNEL_ADMIN_TOPIC_ID = int(
    os.getenv("DISCORD_CHANNEL_ADMIN_TOPIC_ID", 0))
if DISCORD_CHANNEL_TOPIC_ID_TO_SEND_CODE == 0:
    raise ValueError(
        "Please set the DISCORD_CHANNEL_TOPIC_ID_TO_SEND_CODE environment variable.")
if DISCORD_CHANNEL_ADMIN_TOPIC_ID == 0:
    raise ValueError(
        "Please set the DISCORD_CHANNEL_ADMIN_TOPIC_ID environment variable.")
if not DISCORD_BOT_TOKEN:
    raise ValueError("Please set the DISCORD_BOT_TOKEN environment variable.")

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Browser automation variables
browser = None
page = None
code = None
cookie_value = None
cookie_expires = None


async def send_admin_message(message: str):
    """
    Send a message to the admin Discord channel.
    """
    try:
        channel = await client.fetch_channel(DISCORD_CHANNEL_ADMIN_TOPIC_ID)
        if channel:
            await channel.send(message)
            return True
        else:
            print(
                f"Could not find admin channel with ID: {DISCORD_CHANNEL_ADMIN_TOPIC_ID}")
            return False
    except Exception as e:
        print(f"Error sending admin Discord message: {e}")
        return False


async def send_discord_message(message: str):
    """
    Send a message to the configured Discord channel.
    """
    try:
        channel = await client.fetch_channel(DISCORD_CHANNEL_TOPIC_ID_TO_SEND_CODE)
        if channel:
            await channel.send(message)
            return True
        else:
            print(
                f"Could not find channel with ID: {DISCORD_CHANNEL_TOPIC_ID_TO_SEND_CODE}")
            return False
    except Exception as e:
        print(f"Error sending Discord message: {e}")
        return False


@client.event
async def on_ready():
    print(f'Logged in as {client.user}!')
    print("Bot is now online and ready!")


@client.event
async def on_message(message: discord.Message):
    global cookie_value, cookie_expires
    if message.content == '!getotp' and message.channel.id == DISCORD_CHANNEL_TOPIC_ID_TO_SEND_CODE:
        print("Getting OTP")
        germany_tz = pytz.timezone('Europe/Berlin')
        current_time = datetime.now(germany_tz)
        current_hour = current_time.hour

        # Check if the current time is between 12 PM and 11  PM
        # if current_hour < 12 or current_hour >= 23:
        #     await message.channel.send("Outside of allowed time range (12 PM to 11 PM Germany time).")
        #     return
        await message.channel.send("Getting OTP...")
        result = await browser_automation()
        # Send the result to the configured channel for sending code
        channel = await client.fetch_channel(DISCORD_CHANNEL_TOPIC_ID_TO_SEND_CODE)
        if channel:
            await channel.send(result)
        else:
            await send_admin_message(f"Could not find channel with ID: {DISCORD_CHANNEL_TOPIC_ID_TO_SEND_CODE}")
    # Only process commands from admin channel
    if message.channel.id != DISCORD_CHANNEL_ADMIN_TOPIC_ID:
        return

    if message.content.startswith('!setcookie'):
        try:
            # Format: !setcookie <value> <expires>
            parts = message.content.split()
            if len(parts) != 3:
                await send_admin_message("Invalid format. Use: !setcookie <value> <expires>")
                return

            new_value = parts[1]
            new_expires = int(parts[2])

            cookie_value = new_value
            cookie_expires = new_expires

            await send_admin_message(f"Cookie values updated successfully!\nValue: {cookie_value}\nExpires: {cookie_expires}")
        except ValueError:
            await send_admin_message("Invalid expires value. Must be a number.")
        except Exception as e:
            await send_admin_message(f"Error setting cookie values: {str(e)}")

    elif message.content == '!resetcookie':
        cookie_value = None
        cookie_expires = None
        await send_admin_message("Cookie values have been reset.")


async def browser_automation():
    global browser, page, code, cookie_value, cookie_expires
    async with async_playwright() as p:
        # Get the current time in Germany timezone
        germany_tz = pytz.timezone('Europe/Berlin')
        current_time = datetime.now(germany_tz)
        current_hour = current_time.hour

        # # Check if the current time is between 12 PM and 10 PM
        # if current_hour < 12 or current_hour >= 22:
        #     return "Outside of allowed time range (12 PM to 10 PM Germany time)."

        # Check if cookie values are set
        if not cookie_value:
            return "Error Code 5151"

        if browser is None:
            browser = await p.chromium.launch()
        if page is None:
            page = await browser.new_page()
        try:
            # Set the cookie before navigating
            await page.context.add_cookies([{
                'name': 'PHPSESSID',
                'value': cookie_value,
                'domain': 'toolsuite.pro',
                'path': '/',
                'secure': True,
                'expires': 0
            }])

            await page.goto("https://toolsuite.pro/creds/autologin.php")
            print(await page.title())
            # click button with class verification-button
            await page.wait_for_load_state("networkidle")
            await page.click('.verification-button')
            # click button with onclick="showCodeModal()"
            await page.wait_for_load_state("networkidle")
            await page.click('button[onclick="showCodeModal()"]')
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            # get inner text of element with class code-display
            new_code = await page.inner_text('.code-display')
            print(new_code)
            print(isinstance(new_code, int))
            code = int(new_code)
            print("new code: ", code)
            # click on button with onclick="closeCodeModal()"
            await page.wait_for_load_state("networkidle")
            await page.click('button[onclick="closeCodeModal()"]')
            await page.wait_for_load_state("networkidle")
            await page.close()
            await browser.close()
            browser = None
            page = None
            return f"OTP Code: {code}"
        except Exception as e:
            error_msg = f"Error in web scraping process: {str(e)}"
            print(error_msg)
            # Reset cookie values on error
            cookie_value = None
            cookie_expires = None
            await page.close()
            await browser.close()
            browser = None
            page = None
            return error_msg


async def main():
    # Run the Discord bot
    if DISCORD_BOT_TOKEN:
        await client.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
