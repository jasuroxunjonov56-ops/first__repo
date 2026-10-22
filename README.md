# UniXizmat

FastAPI website + aiogram Telegram bot for student orders and worker registration.

## Render environment variables

Set these in Render → your service → Environment. Do not commit card details, bot tokens, or admin passwords into GitHub.

- `BOT_TOKEN` — Telegram bot token.
- `BOT_USERNAME` — bot username without `@`, used for website registration deep links.
- `ADMIN_ID` — Telegram numeric admin ID.
- `ENTRY_FEE` — one-time worker activation fee; default `4000`.
- `PAYMENT_CARD_NUMBER` — payment card shown only inside the Telegram bot.
- `PAYMENT_CARD_HOLDER` — optional cardholder name shown only inside the Telegram bot.
- `ADMIN_USERNAME` — website admin login.
- `ADMIN_PASSWORD` — strong website admin password.
- `COMMISSION_PERCENT` — platform commission percent; default `10`.

## Flow

- Visitors can submit orders directly on the website. Website orders also appear in the Telegram bot order list.
- Worker signup creates a username/password account and opens a Telegram deep link to connect the same account to the user's Telegram ID.
- The one-time fee and card details are shown only in the Telegram bot. A receipt is sent to the admin for manual verification.
- After the admin approves payment, the worker account is activated and the website can automatically sign the user in.
- Workers can take orders from either the website or Telegram bot.

## Deployment

Deploy the repository as a Python web service using the existing Render start command for this project (for example, `uvicorn web:app --host 0.0.0.0 --port $PORT`). Ensure the environment variables above are configured before testing registration/payment.
