from telegram.ext import Application
from config import TOKEN
from handlers import start_handler, message_handler, callback_query_handler, unblack_handler

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(start_handler)
    application.add_handler(unblack_handler)
    application.add_handler(message_handler)
    application.add_handler(callback_query_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
