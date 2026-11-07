import os
import sqlite3
import logging
from decimal import Decimal, InvalidOperation

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "bot.db")
COMMISSION_RATE = Decimal("0.10")

if not TOKEN:
    raise RuntimeError("Set BOT_TOKEN in Railway Variables.")
if not ADMIN_ID:
    raise RuntimeError("Set ADMIN_ID (your numeric Telegram user ID) in Railway Variables.")

logging.basicConfig(level=logging.INFO)
bot = Bot(TOKEN)
dp = Dispatcher()


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance TEXT NOT NULL DEFAULT '0.00',
            referred_by INTEGER,
            referrals INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_user_id INTEGER NOT NULL,
            eligible_amount TEXT NOT NULL,
            commission TEXT NOT NULL,
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")


def ensure_user(user_id, username, referrer=None):
    with db() as c:
        row = c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row:
            c.execute("UPDATE users SET username=? WHERE user_id=?", (username or "", user_id))
            return
        if referrer == user_id:
            referrer = None
        if referrer:
            exists = c.execute("SELECT user_id FROM users WHERE user_id=?", (referrer,)).fetchone()
            if not exists:
                referrer = None
        c.execute("INSERT INTO users(user_id, username, referred_by) VALUES(?,?,?)",
                  (user_id, username or "", referrer))
        if referrer:
            c.execute("UPDATE users SET referrals=referrals+1 WHERE user_id=?", (referrer,))


def get_user(user_id):
    with db() as c:
        return c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def menu():
    # Telegram Bot API 9.4+: danger=red, primary=blue, success=green.
    # Older Telegram clients may show their default button appearance.
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📞 Numbers", style="danger"),
                KeyboardButton(text="📊 Status", style="primary"),
            ],
            [
                KeyboardButton(text="🏆 Traffic", style="primary"),
                KeyboardButton(text="💰 Balance", style="primary"),
            ],
            [
                KeyboardButton(text="💗 Refer & Earn", style="success"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


@dp.message(CommandStart())
async def start(message: Message):
    referrer = None
    if message.text and len(message.text.split()) > 1:
        payload = message.text.split(maxsplit=1)[1]
        if payload.startswith("ref_"):
            try:
                referrer = int(payload[4:])
            except ValueError:
                referrer = None
    ensure_user(message.from_user.id, message.from_user.username, referrer)
    await message.answer(
        f"👋 Welcome, {message.from_user.first_name or 'friend'}!\n\n"
        "Welcome to our service bot. Choose an option below.",
        reply_markup=menu()
    )


@dp.message(F.text.in_({"📞 Numbers", "Numbers"}))
async def numbers(message: Message):
    await message.answer("📞 No Numbers Available")


@dp.message(F.text.in_({"📊 Status", "Status"}))
async def status(message: Message):
    await message.answer("📊 No Status Available")


@dp.message(F.text.in_({"🏆 Traffic", "Traffic"}))
async def traffic(message: Message):
    await message.answer("🏆 No Traffic Available")


@dp.message(F.text.in_({"💰 Balance", "Balance", "balance"}))
async def balance(message: Message):
    ensure_user(message.from_user.id, message.from_user.username)
    u = get_user(message.from_user.id)
    await message.answer(
        "💰 Wallet & Balance\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💵 Available: ${Decimal(u['balance']):.2f}\n"
        f"👥 Total Referred: {u['referrals']}\n"
        "━━━━━━━━━━━━━━━━━━"
    )


@dp.message(F.text.in_({"💗 Refer & Earn", "Refer & Earn", "refer"}))
async def refer(message: Message):
    ensure_user(message.from_user.id, message.from_user.username)
    u = get_user(message.from_user.id)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{message.from_user.id}"
    await message.answer(
        "💗 Refer & Earn\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Invite friends and earn 10% commission on eligible, admin-approved activity.\n\n"
        f"👤 Total Referred: {u['referrals']}\n"
        "💸 Commission: 10%\n\n"
        f"🔗 Your Referral Link:\n{link}\n\n"
        "Commission is credited only when the admin records eligible revenue."
    )


@dp.message(Command("admin"))
async def admin_help(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "🛠 Admin commands:\n"
        "/user USER_ID — view user\n"
        "/credit USER_ID AMOUNT — add wallet balance\n"
        "/commission REFERRER_ID REFERRED_USER_ID AMOUNT — "
        "record eligible revenue and credit 10% commission"
    )


@dp.message(Command("user"))
async def admin_user(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.answer("Usage: /user USER_ID")
    u = get_user(int(parts[1]))
    if not u:
        return await message.answer("User not found.")
    await message.answer(
        f"User: {u['user_id']}\nUsername: @{u['username']}\n"
        f"Balance: ${Decimal(u['balance']):.2f}\nReferrals: {u['referrals']}"
    )


@dp.message(Command("credit"))
async def admin_credit(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split()
    if len(parts) != 3 or not parts[1].isdigit():
        return await message.answer("Usage: /credit USER_ID AMOUNT")
    try:
        amount = Decimal(parts[2])
        if amount <= 0 or amount > Decimal("1000000"):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        return await message.answer("Enter a valid positive amount.")
    uid = int(parts[1])
    with db() as c:
        row = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        if not row:
            return await message.answer("User not found.")
        new_balance = Decimal(row["balance"]) + amount
        c.execute("UPDATE users SET balance=? WHERE user_id=?", (str(new_balance), uid))
    await message.answer(f"Added ${amount:.2f} to user {uid}.")


@dp.message(Command("commission"))
async def admin_commission(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split(maxsplit=3)
    if len(parts) < 4 or not parts[1].isdigit() or not parts[2].isdigit():
        return await message.answer(
            "Usage: /commission REFERRER_ID REFERRED_USER_ID ELIGIBLE_AMOUNT"
        )
    try:
        referrer_id, referred_id = int(parts[1]), int(parts[2])
        eligible = Decimal(parts[3])
        if eligible <= 0 or eligible > Decimal("1000000"):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        return await message.answer("Enter valid IDs and a positive amount.")
    with db() as c:
        ref = c.execute("SELECT user_id FROM users WHERE user_id=?", (referrer_id,)).fetchone()
        referred = c.execute(
            "SELECT referred_by FROM users WHERE user_id=?", (referred_id,)
        ).fetchone()
        if not ref or not referred or referred["referred_by"] != referrer_id:
            return await message.answer("Referral relationship not found.")
        commission = (eligible * COMMISSION_RATE).quantize(Decimal("0.01"))
        bal = c.execute("SELECT balance FROM users WHERE user_id=?", (referrer_id,)).fetchone()
        new_balance = Decimal(bal["balance"]) + commission
        c.execute("UPDATE users SET balance=? WHERE user_id=?", (str(new_balance), referrer_id))
        c.execute(
            """INSERT INTO commissions
               (referrer_id,referred_user_id,eligible_amount,commission,note)
               VALUES(?,?,?,?,?)""",
            (referrer_id, referred_id, str(eligible), str(commission), "Admin approved")
        )
    await message.answer(
        f"Recorded eligible amount ${eligible:.2f}; "
        f"credited 10% = ${commission:.2f}."
    )


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
