#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to handle '(my_)chat_member' updates.
Greets new users & keeps track of which chats the bot is in.
Usage:
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import os
import logging
from typing import Optional, Tuple

from telegram import __version__ as TG_VER, ChatPermissions

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import Chat, ChatMember, ChatMemberUpdated, Update
from telegram.constants import ParseMode
from telegram.ext import Application, ChatMemberHandler, CommandHandler, ContextTypes, MessageHandler, filters
import time
import random
import re
from fuzzywuzzy import fuzz
import json

# Enable logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

dict_re = {
    'а': '[@|а|а́|a]',
    'б': '[б|6|b]',
    'в': '[в|b|v]',
    'г': '[г|r|g]',
    'д': '[д|d]',
    'е': '[е|e|ё|ë]',
    'ж': '[ж|z|*]',
    'з': '[з|3|z]',
    'и': '[и|u|i]',
    'й': '[й|u|i]',
    'к': '[к|k]',
    'л': '[л|l]',
    'м': '[м|m]',
    'н': '[н|h|n]',
    'о': '[о|o|0]',
    'п': '[п|n|p]',
    'р': '[р|r|p]',
    'с': '[с|c|s|5|$]',
    'т': '[т|m|t]',
    'у': '[у́|у|y|u]',
    'ф': '[ф|f]',
    'х': '[х|x|h]',
    'ц': '[ц|c|u]',
    'ч': '[ч|c|h]',
    'ш': '[ш|щ]',
    'ь': '[ь|b]',
    'ы': '[ы|i]',
    #  'ъ' :   '[ъ|ь]',
    'э': '[э|e]',
    'ю': '[ю|y|u]',
    'я': '[я|r]',
    # ' ': '[.|,|!|?|&|)|(|\\|\/|*|-|_|"|\'|;|®]'
}
# Регулярки для замены похожих букв и символов на русские


CWF = open('CurseWords.txt', 'r', encoding='utf-8')
CurseWords = list(filter(None, CWF.read().split('\n')))
CWF.close()

PWF = open('PingWords.txt', 'r', encoding='utf-8')
PingWords = list(filter(None, PWF.read().split('\n')))
PWF.close()

# reading the settings from config file
with open('config.json', 'r', encoding='utf-8') as cf:
    js = cf.read()
    cf.close()
config = json.loads(js)
telegram_token = config.get('telegram_token')
forward_pm = config.get('forward_pm')
random_fun_keyword = config.get('random_fun_keyword')
helper_keyword = config.get('helper_keyword')
admins = config.get('admins')
admin_command_start = config.get('admin_command_start')

hf1 = open('hello1.txt', 'r', encoding='utf-8')
hello_msg1 = hf1.read()
hf1.close()

hf1_1 = open('hello1_1.txt', 'r', encoding='utf-8')
hello_msg1_1 = hf1_1.read()
hf1_1.close()

gf = open('goodbye.txt', 'r', encoding='utf-8')
goodbye_msgs = list(filter(None, gf.read().split('\n')))
gf.close()

sf = open('start.txt', 'r', encoding='utf-8')
start_msg = sf.read()
sf.close()

prf = open('Ping_rand.txt', 'r', encoding='utf-8')
random_msgs = list(filter(None, prf.read().split('\n')))
prf.close()

rpf = open('Rand_Pervoe.txt', 'r', encoding='utf-8')
rand_helper = list(filter(None, rpf.read().split('\n')))
rpf.close()

helper_list = []
for root, dirs, files in os.walk('helper'):
    for filename in files:
        with open('helper/' + filename, 'r', encoding="utf-8") as helperf:
            js_h = helperf.read()
            helperf.close()
        try:
            helper_ent = json.loads(js_h, strict=False)
            helper_list.append(helper_ent)
        except json.decoder.JSONDecodeError:
            print(json.decoder.JSONDecodeError)
            print(js_h)


def config_writer():
    json_object = json.dumps(config, ensure_ascii=False, indent=4)
    with open("config.json", "w", encoding='utf-8') as outfile:
        outfile.write(json_object)
        outfile.close()


def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member


def replace_letters(word=None):
    word = word.lower()
    for key, value in dict_re.items():
        word = re.sub(value, key, word)
    return word


def filter_word(msg):
    msg = msg.split()
    for w in msg:
        w = ''.join([w[i] for i in range(len(w) - 1) if w[i + 1] != w[i]] + [
            w[-1]]).lower()  # Здесь убираю символы которые повторяються "Приииииивет" -> "Привет"
        w = replace_letters(w)

        '''admin trigger words'''
        for word in PingWords:
            b = fuzz.token_sort_ratio(word, w)  # Проверяю сходство слов из списка
            if b >= 100:
                return f"{w} | {b}% Слово-триггер: {word}"
            else:
                pass

        for word in CurseWords:
            b = fuzz.token_sort_ratio(word, w)  # Проверяю сходство слов из списка
            if b >= 87:
                return f"{w} | {b}% Слово-триггер: {word}"
            else:
                pass
    return False


async def detect_chat_adm(msg):
    userid = msg.from_user.id
    member = await msg.chat.get_member(userid)
    anon = None
    if msg.sender_chat is not None:
        anon = msg.sender_chat.id
    if member.status != 'administrator' and member.status != 'creator' and anon != msg.chat.id:
        return False
    else:
        return True


async def antispam(msg, context):
    """Delete spam channel messages"""

    message_entities = None

    if msg.entities is not None and len(msg.entities) > 0:
        message_entities = msg.entities
    elif msg.caption_entities is not None:
        message_entities = msg.caption_entities

    if msg.reply_to_message is not None:
        if msg.reply_to_message.is_automatic_forward is not None:
            if msg.reply_to_message.is_automatic_forward is True:
                for message_entity in message_entities:
                    if message_entity.type == 'url' or message_entity.type == 'text_link':
                        if await detect_chat_adm(msg) is False:
                            for key in admins:
                                await context.bot.send_message(chat_id=admins[key],
                                                               text=f'URL or text_link, id: {msg.from_user.id}',
                                                               parse_mode=ParseMode.HTML)
                                await msg.forward(admins[key])
                            await context.bot.deleteMessage(msg.chat.id, msg.message_id)
                            return
        elif re.search(config['warn_keyword'], msg.text):
            """Warning chat members by admin"""

            if await detect_chat_adm(msg) is True:
                msg_reply = msg.reply_to_message
                for key in admins:
                    await context.bot.send_message(chat_id=admins[key],
                                                   text=f'{msg.text} {msg_reply.from_user.first_name}, '
                                                        f'{msg_reply.from_user.username}, id: {msg_reply.from_user.id}',
                                                   parse_mode=ParseMode.HTML)


async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tracks the chats the bot is in."""
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    # Let's check who is responsible for the change
    cause_name = update.effective_user.full_name

    # Handle chat types differently:
    chat = update.effective_chat
    if chat.type == Chat.PRIVATE:
        if not was_member and is_member:
            logger.info("%s started the bot", cause_name)
            context.bot_data.setdefault("user_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s blocked the bot", cause_name)
            context.bot_data.setdefault("user_ids", set()).discard(chat.id)
    elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            logger.info("%s added the bot to the group %s", cause_name, chat.title)
            context.bot_data.setdefault("group_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the group %s", cause_name, chat.title)
            context.bot_data.setdefault("group_ids", set()).discard(chat.id)
    else:
        if not was_member and is_member:
            logger.info("%s added the bot to the channel %s", cause_name, chat.title)
            context.bot_data.setdefault("channel_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the channel %s", cause_name, chat.title)
            context.bot_data.setdefault("channel_ids", set()).discard(chat.id)


async def show_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows which chats the bot is in"""
    user_ids = ", ".join(str(uid) for uid in context.bot_data.setdefault("user_ids", set()))
    group_ids = ", ".join(str(gid) for gid in context.bot_data.setdefault("group_ids", set()))
    channel_ids = ", ".join(str(cid) for cid in context.bot_data.setdefault("channel_ids", set()))
    text = (
        f"@{context.bot.username} is currently in a conversation with the user IDs {user_ids}."
        f" Moreover it is a member of the groups with IDs {group_ids} "
        f"and administrator in the channels with IDs {channel_ids}."
    )
    await update.effective_message.reply_text(text)


async def greet_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greets new users in chats and announces when someone leaves"""
    result = extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result
    cause_name = update.chat_member.from_user.mention_html()
    member_name = update.chat_member.new_chat_member.user.mention_html()

    chat = await context.bot.getChat(update.effective_chat.id)
    if not was_member and is_member:
        if chat.permissions.can_send_messages:
            if config['admin_commands']['hello']['state'] is True:
                if config['admin_commands']['spoilers']['state'] is True:
                    await update.effective_chat.send_message(
                        hello_msg1_1.format(member_name=member_name),
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await update.effective_chat.send_message(
                        hello_msg1.format(member_name=member_name),
                        parse_mode=ParseMode.HTML,
                    )
    elif was_member and not is_member:
        if config['admin_commands']['goodbye']['state'] is True:
            await update.effective_chat.send_message(
                f"{random.choice(goodbye_msgs)}",
                parse_mode=ParseMode.HTML,
            )


async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward the user message."""
    await update.message.forward(forward_pm)


async def forward_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward from channel to private chat."""
    await update.channel_post.forward(config['private_chat'])


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    # user = update.effective_user
    await update.message.reply_html(
        start_msg,
        # reply_markup=ForceReply(selective=True),
    )


async def delete_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete chat join messages"""
    if config['admin_commands']['join']['state'] is True:
        await update.message.delete()


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.reply_to_message is not None:
        msg = update.message
        member_id = update.message.reply_to_message.from_user.id
        if await detect_chat_adm(msg) is True:
            chat_permissions = ChatPermissions(can_send_messages=False)
            await context.bot.restrict_chat_member(msg.chat.id, member_id, chat_permissions, time.time() + 86400)


async def moderation_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if config['admin_commands']['q&a']['state'] is True:
        if update.message.sender_chat is not None:
            anon = update.message.sender_chat.id
            if anon == update.message.chat.id:
                await update.message.copy(config['support_chat'])

    """Checks channel comments for spam urls."""
    await antispam(update.message, context)

    """Checks chat messages for unacceptable content."""
    print(update)
    print(' ')
    result_word = filter_word(update.message.text)
    if result_word is not False:
        chat = await context.bot.get_chat(update.message.chat.id)
        for key in admins:
            if not chat.has_protected_content:
                await update.message.forward(admins[key])
            else:
                user = f"{update.message.from_user.first_name}, {update.message.from_user.username}, {update.message.from_user.id}"
                text = update.message.text
                link = update.message.link
                await context.bot.send_message(chat_id=admins[key], text=f"<b>{user}</b> \n{text} \n{link}", parse_mode=ParseMode.HTML)
            await context.bot.send_message(chat_id=admins[key], text=result_word, parse_mode=ParseMode.HTML)


async def moderation_caption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks channel comments for spam urls."""
    await antispam(update.message, context)

    """Checks chat messages for unacceptable content."""
    result_word = filter_word(update.message.caption)
    if result_word is not False:
        chat = await context.bot.get_chat(update.message.chat.id)
        for key in admins:
            if not chat.has_protected_content:
                await update.message.forward(admins[key])
            else:
                user = f"{update.message.from_user.first_name}, {update.message.from_user.username}, {update.message.from_user.id}"
                text = update.message.caption
                link = update.message.link
                await context.bot.send_message(chat_id=admins[key], text=f"<b>{user}</b> \n{text} \n{link}",
                                               parse_mode=ParseMode.HTML)
            await context.bot.send_message(chat_id=admins[key], text=result_word, parse_mode=ParseMode.HTML)


async def moderation_edited_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks channel comments for spam urls."""
    await antispam(update.edited_message, context)

    """Checks chat messages for unacceptable content."""
    result_word = filter_word(update.edited_message.text)

    if result_word is not False:
        print('----edited message----')
        print(update)
        print('----------------------')
        # await update.edited_message.forward(config['debug_chat'])
        # await context.bot.send_message(chat_id=config['debug_chat'], text=str(update.edited_message))
        chat = await context.bot.get_chat(update.edited_message.chat.id)
        for key in admins:
            if not chat.has_protected_content:
                await update.edited_message.forward(admins[key])
            else:
                user = f"{update.edited_message.from_user.first_name}, {update.edited_message.from_user.username}, {update.edited_message.from_user.id}"
                text = update.edited_message.text
                link = update.edited_message.link
                await context.bot.send_message(chat_id=admins[key], text=f"<b>{user}</b> \n{text} \n{link}",
                                               parse_mode=ParseMode.HTML)
            await context.bot.send_message(chat_id=admins[key], text=f"{result_word}, сообщение отредактировано",
                                           parse_mode=ParseMode.HTML)


async def moderation_edited_caption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks channel comments for spam urls."""
    await antispam(update.edited_message, context)

    """Checks chat messages for unacceptable content."""
    result_word = filter_word(update.edited_message.caption)
    if result_word is not False:
        chat = await context.bot.get_chat(update.edited_message.chat.id)
        for key in admins:
            if not chat.has_protected_content:
                await update.edited_message.forward(admins[key])
            else:
                user = f"{update.edited_message.from_user.first_name}, {update.edited_message.from_user.username}, {update.edited_message.from_user.id}"
                text = update.edited_message.caption
                link = update.edited_message.link
                await context.bot.send_message(chat_id=admins[key], text=f"<b>{user}</b> \n{text} \n{link}",
                                               parse_mode=ParseMode.HTML)
            await context.bot.send_message(chat_id=admins[key], text=f"{result_word}, сообщение отредактировано",
                                           parse_mode=ParseMode.HTML)


async def random_fun(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is not None:
        await update.message.reply_html(
            f'{random.choice(random_msgs)}')


async def adm_chat_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot control settings"""
    msg = update.message
    if await detect_chat_adm(msg) is True:
        admin_message = msg.text
        for command in config['admin_commands']:
            if admin_message == f"{admin_command_start}{command}_off" and config['admin_commands'][command]['state'] is False:
                await update.effective_chat.send_message(
                    config['admin_commands'][command]['answer_off'],
                    parse_mode=ParseMode.HTML,
                )
                config['admin_commands'][command]['state'] = True
            elif admin_message == f"{admin_command_start}{command}_on" and config['admin_commands'][command]['state'] is True:
                await update.effective_chat.send_message(
                    config['admin_commands'][command]['answer_on'],
                    parse_mode=ParseMode.HTML,
                )
                config['admin_commands'][command]['state'] = False
        config_writer()
    else:
        await update.message.reply_html(config['non_admin_answer'])


async def helper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if update.message is not None:
            for helper_entity in helper_list:
                keyword = replace_letters(update.message.text)
                if helper_entity['command'] == keyword:
                    if helper_entity['delay'] == 'Yes':
                        await update.message.reply_html(
                            f'{random.choice(rand_helper)}')
                        time.sleep(10)
                    await update.message.reply_html(
                        helper_entity['content'],
                        # reply_markup=ForceReply(selective=True),
                    )
                    return
            await moderation_msg(update, context)
    except AttributeError:
        print(AttributeError.args)
        print(update)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(telegram_token).build()

    # Keep track of which chats the bot is in
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    # application.add_handler(CommandHandler("show_chats", show_chats))

    # Handle members joining/leaving chats.
    application.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start, filters.ChatType.PRIVATE))

    # Forward the pm messages on Telegram
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE, forward))

    # VIP chat special
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, forward_vip))

    # Admin commands
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.Regex(f"^{admin_command_start}"),
                                           adm_chat_commands))

    # Mute users
    application.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.Regex(f"^mute"), mute_user))

    # Random fun messages
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.Regex(random_fun_keyword), random_fun))

    # Chat content request
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.Regex(helper_keyword), helper))

    # Delete chat join messages
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.StatusUpdate.NEW_CHAT_MEMBERS, delete_join))

    # Moderating chats
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.TEXT,
                                           moderation_msg))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.UpdateType.EDITED_MESSAGE & filters.TEXT,
                                           moderation_edited_msg))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.CAPTION,
                                           moderation_caption))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.UpdateType.EDITED_MESSAGE & filters.CAPTION,
                                           moderation_edited_caption))

    # Run the bot until the user presses Ctrl-C
    # We pass 'allowed_updates' handle *all* updates including `chat_member` updates
    # To reset this, simply pass `allowed_updates=[]`
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
