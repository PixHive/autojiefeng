import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from telegram.error import BadRequest
from config import FLOWER_AUDIT_GROUP_CHAT_ID, FRIEND_AUDIT_GROUP_CHAT_ID, FLOWER_GROUP_CHAT_ID, FRIEND_GROUP_CHAT_ID, blacklist, appeals, ADMIN_USER_ID

logger = logging.getLogger(__name__)

async def notify_admin(context: CallbackContext, error: Exception) -> None:
    try:
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=f"处理请求时发生错误：{error}")
    except Exception as e:
        logger.error(f"无法通知管理员错误信息：{e}")

async def start(update: Update, context: CallbackContext) -> None:
    if update.message.chat.type == 'private':
        keyboard = [['在花频道申诉', '在群友问频道申诉']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text('请选择在下方选择你要解封的频道或者群组。', reply_markup=reply_markup)
        logger.info("用户 %s 开始申诉流程", update.message.from_user.username)

async def handle_message(update: Update, context: CallbackContext) -> None:
    if update.message.chat.type == 'private':
        user_id = update.message.from_user.id
        username = update.message.from_user.username or update.message.from_user.full_name
        if user_id in blacklist:
            logger.info("用户 %s 已被封禁，无法发送申诉信息", username)
            return  # 用户被封禁时不通知用户

        if update.message.text == '在花频道申诉':
            response_text = '请发送您的申诉信息。'
            keyboard = [['结束申诉']]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(response_text, reply_markup=reply_markup)
            context.user_data['awaiting_appeal'] = 'flower'
            logger.info("用户 %s 选择在花频道申诉", username)
        elif update.message.text == '在群友问频道申诉':
            response_text = '请发送您的申诉信息。'
            keyboard = [['结束申诉']]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(response_text, reply_markup=reply_markup)
            context.user_data['awaiting_appeal'] = 'friend'
            logger.info("用户 %s 选择在群友问频道申诉", username)
        elif update.message.text == '结束申诉':
            await update.message.reply_text('申诉已结束。', reply_markup=ReplyKeyboardRemove())
            context.user_data['awaiting_appeal'] = None
            logger.info("用户 %s 结束了申诉", username)
        elif context.user_data.get('awaiting_appeal'):
            if context.user_data['awaiting_appeal'] == 'flower':
                audit_group_id = FLOWER_AUDIT_GROUP_CHAT_ID
                user_group_id = FLOWER_GROUP_CHAT_ID
            elif context.user_data['awaiting_appeal'] == 'friend':
                audit_group_id = FRIEND_AUDIT_GROUP_CHAT_ID
                user_group_id = FRIEND_GROUP_CHAT_ID

            appeal_message = f"用户 {username} (ID: {user_id}) 的申诉信息：\n{update.message.text}"
            keyboard = [
                [InlineKeyboardButton("解封", callback_data=f'unblock_{user_id}_{user_group_id}'), 
                InlineKeyboardButton("封禁", callback_data=f'blacklist_{user_id}_{user_group_id}'),
                InlineKeyboardButton("忽略", callback_data=f'ignore_{update.message.message_id}_{update.message.message_id}_{user_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                message = await context.bot.send_message(chat_id=audit_group_id, text=appeal_message, reply_markup=reply_markup)
                appeals[message.message_id] = user_id
                await update.message.reply_text('您的申诉信息已转发。请继续发送或按“结束申诉”按钮结束。')
                logger.info("用户 %s 的申诉信息已成功转发到审核群", username)
            except Exception as e:
                logger.error("无法转发用户 %s 的申诉信息：%s", username, e)
                await notify_admin(context, e)
                await update.message.reply_text('转发申诉信息时出现问题，请稍后再试。')
    elif update.message.chat.type in ['group', 'supergroup']:
        if update.message.text.startswith('/unblack'):
            try:
                user_id = int(update.message.text.split(' ')[1])
                if user_id in blacklist:
                    blacklist.remove(user_id)
                    await update.message.reply_text(f"用户 {user_id} 已被移出黑名单。")
                    logger.info("用户 %s 已被移出黑名单", user_id)
                else:
                    await update.message.reply_text(f"用户 {user_id} 不在黑名单中。")
                    logger.info("用户 %s 不在黑名单中", user_id)
            except (IndexError, ValueError) as e:
                await update.message.reply_text("使用方法: /unblack 用户telegramid")
                logger.warning("无效的 /unblack 命令格式")
                await notify_admin(context, e)
        elif update.message.reply_to_message and update.message.reply_to_message.message_id in appeals:
            user_id = appeals[update.message.reply_to_message.message_id]
            try:
                await context.bot.send_message(chat_id=user_id, text=f"审核回复：{update.message.text}")
                logger.info("审核回复已发送给用户 %s", user_id)
            except Exception as e:
                logger.error("无法发送审核回复给用户 %s：%s", user_id, e)
                await notify_admin(context, e)

async def handle_callback_query(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    action, target_id, group_id, message_id = query.data.split('_')

    try:
        if action == 'unblock':
            await context.bot.unban_chat_member(chat_id=group_id, user_id=target_id)
            await query.edit_message_text(text="已解封")
            await context.bot.send_message(chat_id=target_id, text="您的账号已经解封。")
            logger.info("用户 %s 已解封", target_id)
        elif action == 'ignore':
            await query.delete_message()
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=int(message_id))
            except BadRequest as e:
                if str(e).startswith("Message to delete not found"):
                    logger.warning("消息已删除，无法再次删除：%s", e)
                else:
                    logger.error("删除消息时发生错误：%s", e)
                    await notify_admin(context, e)
            await context.bot.send_message(chat_id=target_id, text="您的申诉已被忽略。")
            logger.info("用户 %s 的申诉已被忽略", target_id)
        elif action == 'blacklist':
            blacklist.add(int(target_id))
            await query.edit_message_text(text="已封禁")
            await context.bot.send_message(chat_id=target_id, text="您的账号已被封禁。")
            logger.info("用户 %s 已被封禁", target_id)

        await query.answer()
    except Exception as e:
        logger.error(f"处理回调查询时发生错误：{e}")
        await notify_admin(context, e)
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"处理请求时发生错误：{e}")

start_handler = CommandHandler("start", start)
unblack_handler = CommandHandler("unblack", handle_message)
message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
callback_query_handler = CallbackQueryHandler(handle_callback_query)
