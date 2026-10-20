from flask import Flask
from threading import Thread
import telebot

# Web Server for Render Free Tier
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# Bot Configuration
API_TOKEN = '8756854734:AAHi8fbHKhfAO4iRaIjmmvYry-ADBHdOvSk'
ADMIN_ID = 7651714631
SALES_CHANNEL = '@sajidsells'

bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to Sajid Sales Bot! Kaise help karun?")

if __name__ == '__main__':
    # Start Web Server in background thread
    Thread(target=run_web_server).start()
    
    # Start Telegram Bot
    print("Bot is starting...")
    bot.infinity_polling()
  
