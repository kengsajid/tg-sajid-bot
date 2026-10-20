import os
import logging
from threading import Thread
from flask import Flask

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# --- CONFIGURATION ---
BOT_TOKEN = "8756854734:AAHi8fbHKhfAO4iRaIjmmvYry-ADBHdOvSk"
ADMIN_ID = 7651714631
SALES_CHANNEL = "@sajidsells"

# In-Memory Storage (Cloud Memory)
user_balances = {}
server_1_stock = []
server_2_stock = []
pending_topups = {}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- FLASK WEB SERVER (For Render Keep-Alive) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "TG SAJID API BOT is Running 24/7 on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- START / MAIN MENU ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    if user_id not in user_balances:
        user_balances[user_id] = 0.0

    keyboard = [
        [InlineKeyboardButton("📦 BUY ACCOUNTS", callback_data="buy_menu")],
        [InlineKeyboardButton("💳 TOP UP", callback_data="topup"), InlineKeyboardButton("👤 MY PROFILE", callback_data="profile")],
        [InlineKeyboardButton("💬 SUPPORT", callback_data="support"), InlineKeyboardButton("📢 SALES CHANNEL", url=f"https://t.me/{SALES_CHANNEL.replace('@', '')}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = f"👋 **Welcome to TG SAJID API BOT, {user.first_name}!**\n\nFast & Reliable Telegram Account Marketplace.\n\n💰 **Your Balance:** ₹{user_balances[user_id]:.2f}"
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

# --- CALLBACK HANDLER ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "main_menu":
        await start(update, context)

    elif data == "profile":
        bal = user_balances.get(user_id, 0.0)
        msg = f"👤 **USER PROFILE**\n\n🆔 **User ID:** `{user_id}`\n💰 **Balance:** ₹{bal:.2f}"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "support":
        msg = "💬 **SUPPORT & HELP**\n\nTG Support: @osajid\nWhatsApp: +6283132327923"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "buy_menu":
        s1_count = len(server_1_stock)
        s2_count = len(server_2_stock)
        
        keyboard = [
            [InlineKeyboardButton(f"Server 1 (Stock: {s1_count}) - ₹100", callback_data="buy_s1")],
            [InlineKeyboardButton(f"Server 2 (Stock: {s2_count}) - ₹120", callback_data="buy_s2")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        await query.message.edit_text("🛒 **SELECT SERVER TO BUY ACCOUNTS:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data in ["buy_s1", "buy_s2"]:
        is_s1 = (data == "buy_s1")
        price = 100.0 if is_s1 else 120.0
        stock_list = server_1_stock if is_s1 else server_2_stock
        server_name = "Server 1" if is_s1 else "Server 2"

        bal = user_balances.get(user_id, 0.0)
        if bal < price:
            keyboard = [[InlineKeyboardButton("💳 Add Balance", callback_data="topup")], [InlineKeyboardButton("🔙 Back", callback_data="buy_menu")]]
            await query.message.edit_text(f"❌ **Insufficient Balance!**\n\nRequired: ₹{price}\nYour Balance: ₹{bal:.2f}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        if not stock_list:
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="buy_menu")]]
            await query.message.edit_text(f"❌ **{server_name} is currently OUT OF STOCK!**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        # Deliver Account
        account_data = stock_list.pop(0)
        user_balances[user_id] -= price

        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        await query.message.edit_text(f"✅ **PURCHASE SUCCESSFUL!**\n\n🖥 **Server:** {server_name}\n💰 **Price:** ₹{price}\n\n📦 **Account Details:**\n`{account_data}`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        # Broadcast to Sales Channel
        try:
            broadcast_msg = f"⚡ **NEW SALE — SUCCESS!** ⚡\n\n🛒 **Item:** {server_name} Account\n💵 **Price:** ₹{price}\n👤 **Buyer ID:** `{user_id}`\n\n🤖 @{context.bot.username}"
            await context.bot.send_message(chat_id=SALES_CHANNEL, text=broadcast_msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Failed to send sales broadcast: {e}")

    elif data == "topup":
        context.user_data['awaiting_topup'] = True
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")]]
        await query.message.edit_text("💳 **UPI TOP-UP**\n\nPlease enter the amount you want to add (e.g. `100`):", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ADMIN ACTIONS
    elif data.startswith("approve_") or data.startswith("reject_"):
        if user_id != ADMIN_ID:
            return
        
        action, req_id = data.split("_", 1)
        if req_id not in pending_topups:
            await query.message.edit_text("⚠️ Request already processed.")
            return

        topup_info = pending_topups.pop(req_id)
        target_user = topup_info['user_id']
        amount = topup_info['amount']

        if action == "approve":
            user_balances[target_user] = user_balances.get(target_user, 0.0) + amount
            await context.bot.send_message(chat_id=target_user, text=f"✅ **Top-Up Approved!**\n₹{amount:.2f} has been added to your balance.", parse_mode="Markdown")
            await query.message.edit_text(f"✅ Approved ₹{amount} for user `{target_user}`.")
        else:
            await context.bot.send_message(chat_id=target_user, text=f"❌ **Top-Up Request Rejected.**", parse_mode="Markdown")
            await query.message.edit_text(f"❌ Rejected top-up for user `{target_user}`.")

# --- ADMIN PANEL ---
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Account (Server 1)", callback_data="add_s1")],
        [InlineKeyboardButton("➕ Add Account (Server 2)", callback_data="add_s2")],
        [InlineKeyboardButton("📊 Check Stocks", callback_data="check_stock")]
    ]
    await update.message.reply_text("👑 **ADMIN CONTROL PANEL**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        return
    
    data = query.data
    if data == "add_s1":
        context.user_data['adding_stock'] = "s1"
        await query.message.edit_text("📥 Send account details for **SERVER 1**:")
    elif data == "add_s2":
        context.user_data['adding_stock'] = "s2"
        await query.message.edit_text("📥 Send account details for **SERVER 2**:")
    elif data == "check_stock":
        await query.message.edit_text(f"📊 **CURRENT STOCK:**\n\nServer 1: {len(server_1_stock)} accounts\nServer 2: {len(server_2_stock)} accounts")

# --- TEXT / MEDIA HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text or ""

    # Admin Adding Stock
    if user_id == ADMIN_ID and context.user_data.get('adding_stock'):
        target_server = context.user_data.pop('adding_stock')
        if target_server == "s1":
            server_1_stock.append(text)
            await update.message.reply_text("✅ Account successfully added to **SERVER 1**!")
        else:
            server_2_stock.append(text)
            await update.message.reply_text("✅ Account successfully added to **SERVER 2**!")
        return

    # User Topup Amount
    if context.user_data.get('awaiting_topup'):
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError
            context.user_data['topup_amount'] = amount
            context.user_data.pop('awaiting_topup')
            context.user_data['awaiting_screenshot'] = True
            await update.message.reply_text(f"💰 Amount: ₹{amount}\n\nPlease send payment screenshot or UTR number to proceed.")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid positive number.")
        return

    # User Screenshot / UTR Submission
    if context.user_data.get('awaiting_screenshot'):
        amount = context.user_data.pop('topup_amount', 0)
        context.user_data.pop('awaiting_screenshot')
        
        req_id = f"{user_id}_{update.message.message_id}"
        pending_topups[req_id] = {'user_id': user_id, 'amount': amount}

        keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{req_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_{req_id}")]
        ]
        
        # Notify Admin
        admin_text = f"🔔 **NEW TOP-UP REQUEST**\n\n👤 **User ID:** `{user_id}`\n💵 **Amount:** ₹{amount}"
        if update.message.photo:
            photo_file = update.message.photo[-1].file_id
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file, caption=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            admin_text += f"\n📝 **UTR / Info:** {text}"
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        await update.message.reply_text("⏳ Payment proof submitted! Admin approval ka wait karein.")

def main():
    # Background Flask Web Server Thread
    server_thread = Thread(target=run_flask)
    server_thread.daemon = True
    server_thread.start()

    # Telegram Bot Runner
    tg_app = ApplicationBuilder().token(BOT_TOKEN).build()

    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("admin", admin))
    tg_app.add_handler(CallbackQueryHandler(admin_button_handler, pattern="^(add_s1|add_s2|check_stock)$"))
    tg_app.add_handler(CallbackQueryHandler(button_handler))
    tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    tg_app.run_polling()

if __name__ == '__main__':
    main()
        
