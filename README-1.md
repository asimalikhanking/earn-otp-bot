# Telegram Referral Bot (colored buttons)

Menu:
- Numbers: red (`danger`) -> No Numbers Available
- Status: blue (`primary`) -> No Status Available
- Traffic: blue (`primary`) -> No Traffic Available
- Balance: blue (`primary`) -> wallet balance
- Refer & Earn: green (`success`) -> referral link and 10% commission

No Stock button. No Create Session button.

Colored button backgrounds require Telegram Bot API 9.4+ and a compatible Telegram client
(released February 9, 2026 or later). Older clients may display default button colors.

## Deploy on Railway
1. Create a bot with @BotFather and copy its token.
2. Set Railway Variables:
   - BOT_TOKEN = your BotFather token
   - ADMIN_ID = your numeric Telegram user ID
3. Deploy this folder. Start command: `python bot.py`
4. For persistent user balances, attach a Railway Volume and set DB_PATH to a file path
   inside that volume, e.g. `/data/bot.db`.

## Admin commands
- /admin
- /user USER_ID
- /credit USER_ID AMOUNT
- /commission REFERRER_ID REFERRED_USER_ID ELIGIBLE_AMOUNT

Referral commissions are 10% of eligible amounts manually approved and recorded by admin.
This starter has no number sales or session feature, so it does not create automatic sales.
Keep BOT_TOKEN secret.
