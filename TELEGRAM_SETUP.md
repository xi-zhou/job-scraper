# Telegram Bot Setup Guide

This guide will walk you through creating a Telegram bot and getting the credentials needed for the job crawler.

## Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather** (the official Telegram bot for creating bots)

2. Start a chat with BotFather and send the command:
   ```
   /newbot
   ```

3. BotFather will ask you to choose a name for your bot:
   - Enter a display name (e.g., "LinkedIn Job Alerts")

4. Next, choose a username for your bot:
   - Must end in "bot" (e.g., "my_linkedin_jobs_bot")
   - Must be unique

5. Once created, BotFather will give you a **Bot Token** that looks like:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

   ⚠️ **IMPORTANT**: Save this token! You'll need it for the `.env` file.

## Step 2: Get Your Chat ID

You need to get your Chat ID so the bot knows where to send messages.

### Method 1: Using a Bot (Easiest)

1. Search for **@userinfobot** in Telegram

2. Start a chat with it and it will immediately reply with your user information

3. Look for the **Id** field - this is your Chat ID (e.g., `123456789`)

### Method 2: Using the API

1. Send a message to your newly created bot (just say "hi")

2. Visit this URL in your browser (replace `YOUR_BOT_TOKEN` with your actual token):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```

3. Look for the `"chat":{"id":123456789}` field in the JSON response

4. The number is your Chat ID

## Step 3: Update Your .env File

1. Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in your credentials:
   ```
   APIFY_API_KEY=your_apify_api_key_here
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=123456789
   ```

3. Save the file

## Step 4: Test the Connection

Run the crawler once to test if everything works:

```bash
python main.py
```

If configured correctly, you should receive a test message from your bot in Telegram!

## Troubleshooting

### Bot doesn't send messages
- Make sure you've started a chat with your bot first (send any message to it)
- Verify the Bot Token is correct
- Check that the Chat ID matches your Telegram user ID

### "Unauthorized" error
- Your Bot Token is incorrect
- Copy it again from BotFather

### Messages go to wrong person
- Your Chat ID is incorrect
- Use @userinfobot to verify your Chat ID

### Still having issues?
- Make sure `.env` file exists and is in the same directory as `main.py`
- Check that there are no extra spaces in your `.env` file
- Verify Python loaded the environment variables (you can add `print(os.getenv('TELEGRAM_BOT_TOKEN'))` to debug)
