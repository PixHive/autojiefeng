import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext

# 配置日志记录
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
FLOWER_GROUP_CHAT_ID = 'FLOWER_GROUP_CHAT_ID'  # 替换为花频道的群组ID
FRIEND_GROUP_CHAT_ID = 'FRIEND_GROUP_CHAT_ID'  # 替换为群友问频道的群组ID
FLOWER_AUDIT_GROUP_CHAT_ID = 'FLOWER_AUDIT_GROUP_CHAT_ID'  # 替换为花频道审核群组ID
FRIEND_AUDIT_GROUP_CHAT_ID = 'FRIEND_AUDIT_GROUP_CHAT_ID'  # 替换为群友问频道审核群组ID

async def start(update: Update, context: CallbackContext) -> None:
    if update.message.chat.type == 'private':
        keyboard = [['开始申诉']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text('欢迎使用申诉解封机器人！请选择下方按钮开始解封流程:', reply_markup=reply_markup)

async def handle_message(update: Update, context: CallbackContext) -> None:
    if update.message.chat.type == 'private':
        if update.message.text == '开始申诉':
            keyboard = [['在花频道申诉', '群友问频道申诉']]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text('请选择申诉渠道:', reply_markup=reply_markup)
        elif update.message.text == '在花频道申诉':
            response_text = '请发送您的申诉信息。'
            keyboard = [['结束申诉']]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(response_text, reply_markup=reply_markup)
            context.user_data['awaiting_appeal'] = 'flower'
        elif update.message.text == '群友问频道申诉':
            response_text = '请发送您的申诉信息。'
            keyboard = [['结束申诉']]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(response_text, reply_markup=reply_markup)
            context.user_data['awaiting_appeal'] = 'friend'
        elif update.message.text == '结束申诉':
            await update.message.reply_text('申诉已结束。', reply_markup=ReplyKeyboardRemove())
            context.user_data['awaiting_appeal'] = None
        elif context.user_data.get('awaiting_appeal'):
            if context.user_data['awaiting_appeal'] == 'flower':
                audit_group_id = FLOWER_AUDIT_GROUP_CHAT_ID
                user_group_id = FLOWER_GROUP_CHAT_ID
            elif context.user_data['awaiting_appeal'] == 'friend':
                audit_group_id = FRIEND_AUDIT_GROUP_CHAT_ID
                user_group_id = FRIEND_GROUP_CHAT_ID

            appeal_message = f"用户 {update.message.from_user.username} 的申诉信息: {update.message.text}"
            keyboard = [
                [InlineKeyboardButton("解封", callback_data=f'unblock_{update.message.from_user.id}_{user_group_id}'), 
                InlineKeyboardButton("忽略", callback_data=f'ignore_{update.message.message_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=audit_group_id, text=appeal_message, reply_markup=reply_markup)
            await update.message.reply_text('您的申诉信息已转发。请继续发送或按“结束申诉”按钮结束。')

async def handle_callback_query(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    action, target_id, group_id = query.data.split('_')

    try:
        if action == 'unblock':
            await context.bot.unban_chat_member(chat_id=group_id, user_id=target_id)
            await query.edit_message_text(text="已解封")
            await context.bot.send_message(chat_id=target_id, text="您的账号已经解封。")
        elif action == 'ignore':
            await query.delete_message()

        await query.answer()
    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"处理请求时发生错误: {e}")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    application.run_polling()

if __name__ == '__main__':
    main()
