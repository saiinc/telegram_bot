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
import datetime
import os
import logging
from typing import Optional, Tuple

import pytz
from telegram import __version__ as TG_VER, ChatPermissions, Message

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


import gspread  # импортируем библиотеку для работы с гугл таблицами


# Enable logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
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

def bot_config_read():
    with open('config.json', 'r', encoding='utf-8') as cf:
        js = cf.read()
        cf.close()
    return json.loads(js)


def bot_config_writer(config_dict):
    json_object = json.dumps(config_dict.__dict__, ensure_ascii=False, indent=4)
    with open("config.json", "w", encoding='utf-8') as outfile:
        outfile.write(json_object)
        outfile.close()


class UserConfig:
    def __init__(self, telegram_token, helper_keyword, random_fun_keyword, random_game_keyword, warn_keyword,
                 forward_pm, admin_command_start, non_admin_answer, admin_command_update, private_chat, debug_chat,
                 google_table_users, private_spammers):
        self.telegram_token = telegram_token
        self.helper_keyword = helper_keyword
        self.random_fun_keyword = random_fun_keyword
        self.random_game_keyword = random_game_keyword
        self.warn_keyword = warn_keyword
        self.forward_pm = forward_pm
        self.admin_command_start = admin_command_start
        self.non_admin_answer = non_admin_answer
        self.admin_command_update = admin_command_update
        self.private_chat = private_chat
        self.debug_chat = debug_chat
        self.google_table_users = google_table_users
        self.private_spammers = private_spammers


def bot_config_load():
    config_content = bot_config_read()
    my_bot_config = UserConfig(
                    config_content["telegram_token"],
                    config_content["helper_keyword"],
                    config_content["random_fun_keyword"],
                    config_content["random_game_keyword"],
                    config_content["warn_keyword"],
                    config_content["forward_pm"],
                    config_content["admin_command_start"],
                    config_content["non_admin_answer"],
                    config_content["admin_command_update"],
                    config_content["private_chat"],
                    config_content["debug_chat"],
                    config_content["google_table_users"],
                    config_content["private_spammers"])
    return my_bot_config


bot_config = bot_config_load()
gs = gspread.service_account(filename='agile-splicer-401313-81027a7c3f21.json')  # подключаем файл с ключами и пр.
sh = gs.open_by_key(bot_config.google_table_users)  # подключаем таблицу по ID
worksheet = sh.sheet1  # получаем первый лист

chat_list = os.listdir("chats")


def my_helper_read(chat):
    file_helper_list = []
    for root, dirs, files in os.walk(f"chats/{chat}/helper"):
        for filename in files:
            with open(f"chats/{chat}/helper/" + filename, 'r', encoding="utf-8") as helperf:
                js_h = helperf.read()
                helperf.close()
            try:
                helper_ent = json.loads(js_h, strict=False)
                file_helper_list.append(helper_ent)
            except json.decoder.JSONDecodeError:
                logger.error(json.decoder.JSONDecodeError)
                print(js_h)
    return file_helper_list


def my_msg_content_read(chat):
    file_msg_content = {}
    for root, dirs, files in os.walk(f"chats/{chat}/msg_content"):
        for filename in files:
            with open(f"chats/{chat}/msg_content/" + filename, 'r', encoding="utf-8") as msgf:
                msgc = msgf.read()
                msgf.close()
            file_msg_content[filename[:filename.rfind('.')].lower()] = msgc
    return file_msg_content


def my_str_content_read(chat):
    file_str_content = {}
    for root, dirs, files in os.walk(f"chats/{chat}/str_content"):
        for filename in files:
            with open(f"chats/{chat}/str_content/" + filename, 'r', encoding="utf-8") as strf:
                strc = list(filter(None, strf.read().split('\n')))
                strf.close()
            file_str_content[filename[:filename.rfind('.')].lower()] = strc
    return file_str_content


def my_rp_actions_read(chat):
    with open(f"chats/{chat}/rp_actions.json", 'r', encoding='utf-8') as rpf:
        js = rpf.read()
        rpf.close()
    return json.loads(js)


def chat_config_read(chat):
    with open(f"chats/{chat}/config.json", 'r', encoding='utf-8') as cf:
        js = cf.read()
        cf.close()
    return json.loads(js)


def chat_config_writer(config_dict, chat):
    json_object = json.dumps(config_dict, ensure_ascii=False, indent=4)
    with open(f"chats/{chat}/config.json", "w", encoding='utf-8') as outfile:
        outfile.write(json_object)
        outfile.close()


def chat_content_load(chat):
    msg_content = my_msg_content_read(chat)
    str_content = my_str_content_read(chat)
    chat_config = chat_config_read(chat)
    my_chat = ChatMy(int(chat),
                     msg_content['hello1'],
                     msg_content['hello1_1'],
                     str_content['goodbye'],
                     str_content['curse_words'],
                     str_content['ping_words'],
                     str_content['delete_words'],
                     str_content['ping_rand'],
                     str_content['rand_pervoe'],
                     my_helper_read(chat),
                     my_rp_actions_read(chat),
                     chat_config['admin_commands'],
                     chat_config['support_chat'])
    return my_chat


class ChatMy:
    def __init__(self, chat, hello, hello_spoil, goodbye, curse_words, ping_words, delete_words, ping_rand, rand_pervoe,
                 chat_helper, rp_actions, admin_commands, support_chat):
        self.chat = chat
        self.hello = hello
        self.hello_spoil = hello_spoil

        self.goodbye = goodbye
        self.curse_words = curse_words
        self.ping_words = ping_words
        self.delete_words = delete_words
        self.ping_rand = ping_rand
        self.rand_pervoe = rand_pervoe

        self.helper = chat_helper
        self.rp_actions = rp_actions

        self.admin_commands = admin_commands
        self.support_chat = support_chat


chats = {}
support_chats = {}


for user_chat_id in chat_list:
    chats[int(user_chat_id)] = chat_content_load(user_chat_id)
    support_chats[chats[int(user_chat_id)].support_chat] = int(user_chat_id)

for dict_key in chats:
    user_chat_id = chats[dict_key]
    print(dict_key, user_chat_id.support_chat, user_chat_id.rp_actions)

ignore = []


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


def delete_word(msg, chat):
    if chats.get(chat) is not None:
        pass
    else:
        chat = support_chats[chat]
    msg = msg.split()
    for w in msg:
        w = ''.join([w[i] for i in range(len(w) - 1) if w[i + 1] != w[i]] + [
            w[-1]]).lower()  # Здесь убираю символы которые повторяються "Приииииивет" -> "Привет"
        w = replace_letters(w)

        for word in chats[chat].delete_words:
            b = fuzz.token_sort_ratio(word, w)  # Проверяю сходство слов из списка
            if b >= 100:
                return f"{w} | {b}% Слово-триггер: {word}"
            else:
                pass
    return False


def filter_word(msg, chat):
    if chats.get(chat) is not None:
        pass
    else:
        chat = support_chats[chat]
    msg = msg.split()
    for w in msg:
        w = ''.join([w[i] for i in range(len(w) - 1) if w[i + 1] != w[i]] + [
            w[-1]]).lower()  # Здесь убираю символы которые повторяються "Приииииивет" -> "Привет"
        w = replace_letters(w)

        '''admin trigger words'''
        if chats[chat].admin_commands["ping_words"]["state"] is True:
            for word in chats[chat].ping_words:
                b = fuzz.token_sort_ratio(word, w)  # Проверяю сходство слов из списка
                if b >= 100:
                    return f"{w} | {b}% Слово-триггер: {word}"
                else:
                    pass

        for word in chats[chat].curse_words:
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
    """Delete messages from user as channel's sender"""
    if msg.sender_chat is not None:
        if msg.sender_chat.id != msg.chat.id:
            if msg.reply_to_message is None:
                await context.bot.deleteMessage(msg.chat.id, msg.message_id)
                return
            '''if msg.reply_to_message is not None:
                if msg.reply_to_message.is_automatic_forward is None:
                    if msg.message_thread_id is None:
                        await msg.reply_html("to delete")'''

    """Delete spam channel messages"""
    message_entities = None

    if msg.entities is not None and len(msg.entities) > 0:
        message_entities = msg.entities
    elif msg.caption_entities is not None:
        message_entities = msg.caption_entities

    if msg.reply_to_message is not None:
        if await detect_chat_adm(msg) is False:
            if msg.reply_to_message.is_automatic_forward is not None:  # Detect spam link
                if msg.reply_to_message.is_automatic_forward is True:
                    for message_entity in message_entities:
                        if message_entity.type == 'url' or message_entity.type == 'text_link':

                            await context.bot.send_message(chat_id=chats[msg.chat.id].support_chat,
                                                           text=f'URL or text_link, id: {msg.from_user.id}',
                                                           parse_mode=ParseMode.HTML)
                            await msg.forward(chats[msg.chat.id].support_chat)
                            await context.bot.deleteMessage(msg.chat.id, msg.message_id)


async def moderation_alert_sender(update, result_word, context, edited=False):
    from_user = update.effective_message.from_user
    caption = update.effective_message.caption
    text = update.effective_message.text
    link = update.effective_message.link

    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = support_chats[update.effective_chat.id]
    user = f"{from_user.first_name}, {from_user.username}, {from_user.id}"
    await context.bot.send_message(chat_id=chats[chat].support_chat,
                                   text=f"<b>{user}</b> \n{text if text is not None else caption} \n{link}",
                                   parse_mode=ParseMode.HTML)
    if edited is False:
        await context.bot.send_message(chat_id=chats[chat].support_chat, text=result_word,
                                       parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(chat_id=chats[chat].support_chat,
                                       text=f"{result_word}, сообщение отредактировано",
                                       parse_mode=ParseMode.HTML)


async def moderatorial_user_sender(update, context):
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = support_chats[update.effective_chat.id]
    msg = update.message
    msg_reply = update.message.reply_to_message
    await context.bot.send_message(chat_id=chats[chat].support_chat,
                                   text=f'{str(msg_reply.text or "") + str(msg_reply.caption or "")} |{msg.text}| '
                                        f'{msg_reply.from_user.first_name}, '
                                        f'{msg_reply.from_user.username}, id: {msg_reply.from_user.id}',
                                   parse_mode=ParseMode.HTML)
    '''---Добавление пользователя в гугл-таблицу---'''
    worksheet.append_row([str(datetime.datetime.now(pytz.timezone("Europe/Moscow"))),  # Дата
                          msg_reply.from_user.id,  # Юзер Айди
                          msg_reply.from_user.username,  # Юзернейм
                          msg_reply.from_user.first_name,  # Ник
                          msg.text,  # Мут/пред/бан
                          str(msg_reply.text or "") + str(msg_reply.caption or "")])  # Сообщение
    '''----------------------------------------------'''


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
    if chat.permissions is None:
        return

    if chats.get(chat.id) is not None:
        chat_id = chat.id
    else:
        chat_id = support_chats[chat.id]

    if not was_member and is_member:
        if chat.permissions.can_send_messages:
            if chats[chat_id].admin_commands['notify_join']['state'] is True:
                user = f"{update.chat_member.new_chat_member.user.first_name}, " \
                       f"{update.chat_member.new_chat_member.user.username}, " \
                       f"{update.chat_member.new_chat_member.user.id}"
                text = "now joined."
                await context.bot.send_message(chat_id=chats[chat_id].support_chat, text=f"‼<b>{user}</b> \n{text}‼",
                                               parse_mode=ParseMode.HTML)
            if chats[chat_id].admin_commands['hello']['state'] is True:
                if chats[chat_id].admin_commands['spoilers']['state'] is False:
                    await update.effective_chat.send_message(
                        chats[chat_id].hello.format(member_name=member_name),
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await update.effective_chat.send_message(
                        chats[chat_id].hello_spoil.format(member_name=member_name),
                        parse_mode=ParseMode.HTML,
                    )
    elif was_member and not is_member:
        if chats[chat_id].admin_commands['goodbye']['state'] is True:
            await update.effective_chat.send_message(
                f"{random.choice(chats[chat_id].goodbye)}",
                parse_mode=ParseMode.HTML,
            )


async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward the private user message."""
    user = update.effective_user
    message = update.effective_message.text.split()
    if user.id == int(bot_config.forward_pm) and message[0] == "Ignore":
        spammer = int(message[1])
        if user.id != spammer and spammer not in bot_config.private_spammers:
            bot_config.private_spammers.append(spammer)
            bot_config_writer(bot_config)
    if user.id not in bot_config.private_spammers:
        await context.bot.send_message(bot_config.forward_pm, user)
        await update.message.forward(bot_config.forward_pm)


async def forward_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward from channel to private chat."""
    if update.channel_post.pinned_message is None:
        await update.channel_post.forward(bot_config.private_chat)


async def new_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Announce new web post"""
    text = update.message.text.split()
    pin_msg = await context.bot.send_message(chat_id=bot_config.private_chat,
                                             text=f"На Бусти новый пост! Уровень подписки {text[-1]} и выше! {text[1]}"
                                             )
    await context.bot.pin_chat_message(pin_msg.chat.id, pin_msg.message_id)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    # user = update.effective_user
    await update.message.reply_html(
        "Привет!",
        # reply_markup=ForceReply(selective=True),
    )


async def delete_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete chat join messages"""
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = support_chats[update.effective_chat.id]
    if chats[chat].admin_commands['delete_join']['state'] is True:
        await update.message.delete()


async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await detect_chat_adm(update.message):
        await moderatorial_user_sender(update, context)


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await detect_chat_adm(update.message) is True:
        msg = update.message
        mute_time = 24
        if len(update.message.text.split()) > 1:
            mute_time = int(update.message.text.split()[-1])
        member_id = update.message.reply_to_message.from_user.id
        chat_permissions = ChatPermissions(can_send_messages=False)
        await context.bot.restrict_chat_member(msg.chat.id, member_id, chat_permissions,
                                               time.time() + mute_time * 3600)
        await moderatorial_user_sender(update, context)


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await detect_chat_adm(update.message) is True:
        msg = update.message
        member_id = update.message.reply_to_message.from_user.id
        await context.bot.banChatMember(chat_id=msg.chat_id, user_id=member_id)
        await moderatorial_user_sender(update, context)


async def moderation_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Copy all massages from anon admin"""
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = support_chats[update.effective_chat.id]
    if chats[chat].admin_commands['q&a']['state'] is True:
        if update.message.sender_chat is not None:
            anon = update.message.sender_chat.id
            if anon == update.message.chat.id:
                await update.message.copy(chats[chat].support_chat)

    """Role-play commands"""
    if update.message is not None and update.message.reply_to_message is not None:
        user_command = [word for word in update.message.text.split()]
        for action in chats[chat].rp_actions:
            if user_command[0].lower() == action:
                await context.bot.send_message(chat_id=update.message.chat.id,
                                               text=f"{chats[chat].rp_actions[action]} "
                                                    f"{update.message.reply_to_message.from_user.mention_html()} "
                                                    f"{' '.join(user_command[1:])}",
                                               parse_mode=ParseMode.HTML)

    """Checks channel comments for spam urls."""
    await antispam(update.effective_message, context)

    """Checks chat messages for unacceptable content."""
    result_word = filter_word(update.effective_message.text, update.effective_chat.id)
    if result_word is not False:
        if update.edited_message is None:
            await moderation_alert_sender(update, result_word, context, edited=False)
        else:
            await moderation_alert_sender(update, result_word, context, edited=True)
    else:
        result_word = delete_word(update.effective_message.text, update.effective_chat.id)
        if result_word is not False:
            await moderation_alert_sender(update, result_word, context, edited=False)
            await context.bot.deleteMessage(update.effective_chat.id, update.effective_message.id)


async def moderation_caption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks channel comments for spam urls."""
    await antispam(update.effective_message, context)

    """Checks chat messages for unacceptable content."""
    result_word = filter_word(update.effective_message.caption, update.effective_chat.id)
    if result_word is not False:
        if update.edited_message is None:
            await moderation_alert_sender(update, result_word, context, edited=False)
        else:
            await moderation_alert_sender(update, result_word, context, edited=True)
    else:
        result_word = delete_word(update.effective_message.caption, update.effective_chat.id)
        if result_word is not False:
            await moderation_alert_sender(update, result_word, context, edited=False)
            await context.bot.deleteMessage(update.effective_chat.id, update.effective_message.id)


async def random_fun(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot replies a random string from text file"""
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = support_chats[update.effective_chat.id]
    await update.message.reply_html(random.choice(chats[chat].ping_rand))


async def random_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot replies a random number"""
    global ignore
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = support_chats[update.effective_chat.id]
    if update.message is not None:
        if await detect_chat_adm(update.message):
            s = update.message.text
            nums = re.findall(r'\d+', s)
            nums = [int(i) for i in nums]
            diap = list(range(nums[1], nums[2] + 1))
            if update.effective_chat.id == chats[chat].support_chat:
                ignore = nums[3:]  # In admin chat, you can edit numbers to ignore
            print(ignore)
            for del_num in ignore:
                if del_num in diap:
                    diap.remove(del_num)
                else:
                    await update.message.reply_html(
                        f"Числа-исключения вне диапазона.")
                    return
            rand_nums = []
            if nums[0] > len(diap):
                if update.effective_chat.id == chats[chat].support_chat:
                    await update.message.reply_html(
                        f"Количество чисел больше диапазона.")
            else:
                for i in range(nums[0]):
                    rand_num = random.choice(range(len(diap)))
                    rand_nums.append(diap[rand_num])
                    del diap[rand_num]
                await update.message.reply_html(
                    f"Случайные числа: {rand_nums}.")


async def adm_chat_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot control settings"""
    global bot_config
    msg = update.message
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = support_chats[update.effective_chat.id]
    if await detect_chat_adm(msg) is True:
        admin_message = msg.text
        if admin_message == f"{bot_config.admin_command_start}{bot_config.admin_command_update}":
            bot_config = bot_config_load()
            chats[chat] = chat_content_load(chat)
            current_jobs = context.job_queue.get_jobs_by_name(str(chat))
            if chats[chat].admin_commands['night_mute']['state'] is True and not current_jobs:
                mute_jobs(context.job_queue, chat)
                await update.message.reply_html('Jobs created')
                return
            elif chats[chat].admin_commands['night_mute']['state'] is False and current_jobs:
                for job in current_jobs:
                    job.enabled = False
                    job.schedule_removal()
                    await update.message.reply_html('Job destroyed')
                    return
            print(current_jobs)
            await update.message.reply_html(
                'Ok')
            return
        for command in chats[chat].admin_commands:
            if admin_message == bot_config.admin_command_start:
                command_list = ""
                for commands in chats[chat].admin_commands:
                    command_list = command_list + f"{commands}: {str(chats[chat].admin_commands[commands]['state'])} \n"
                await update.message.reply_html(command_list)
                return
            if admin_message == f"{bot_config.admin_command_start}{command}_off" and \
                    chats[chat].admin_commands[command]['state'] is True:
                await update.effective_chat.send_message(
                    chats[chat].admin_commands[command]['answer_off'],
                    parse_mode=ParseMode.HTML,
                )
                chats[chat].admin_commands[command]['state'] = False
                chat_config_writer({'support_chat': chats[chat].support_chat,
                                    'admin_commands': chats[chat].admin_commands}, chat)
                return
            elif admin_message == f"{bot_config.admin_command_start}{command}_on" and \
                    chats[chat].admin_commands[command]['state'] is False:
                await update.effective_chat.send_message(
                    chats[chat].admin_commands[command]['answer_on'],
                    parse_mode=ParseMode.HTML,
                )
                chats[chat].admin_commands[command]['state'] = True
                chat_config_writer({'support_chat': chats[chat].support_chat,
                                    'admin_commands': chats[chat].admin_commands}, chat)
                return
    else:
        await update.message.reply_html(bot_config.non_admin_answer)


async def helper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = support_chats[update.effective_chat.id]
    try:
        if update.message is not None:
            for helper_entity in chats[chat].helper:
                keyword = replace_letters(update.message.text)
                if helper_entity['command'] == keyword:
                    if helper_entity['delay'] == 'Yes':
                        await update.message.reply_html(
                            f"{random.choice(chats[chat].rand_pervoe)}")
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


async def chat_mute(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.set_chat_permissions(chat_id=job.chat_id, permissions=ChatPermissions(can_send_messages=False))
    if chats[job.chat_id].admin_commands['hello']['state'] is True:
        chats[job.chat_id].admin_commands['hello']['state'] = False
    if chats[job.chat_id].admin_commands['goodbye']['state'] is True:
        chats[job.chat_id].admin_commands['goodbye']['state'] = False
    await context.bot.send_message(chat_id=job.chat_id, text='Комментарии закрываются! Спокойной ночи. ✨')


async def chat_unmute(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.set_chat_permissions(chat_id=job.chat_id, permissions=ChatPermissions(can_send_messages=True,
                                                                                            can_send_audios=True,
                                                                                            can_send_videos=True,
                                                                                            can_send_documents=True,
                                                                                            can_send_polls=True,
                                                                                            can_send_video_notes=True,
                                                                                            can_send_voice_notes=True,
                                                                                            can_send_other_messages=True,
                                                                                            can_add_web_page_previews=True,
                                                                                            can_send_photos=True))

    await context.bot.send_message(chat_id=job.chat_id, text='Комментарии открыты! Доброе утро. 🌼')


def mute_jobs(job_queue, chat):
    job_queue.run_daily(chat_mute, datetime.time(hour=21, minute=30, tzinfo=pytz.timezone("Europe/Moscow")),
                        chat_id=chat, name=str(chat))
    job_queue.run_daily(chat_unmute, datetime.time(hour=9, minute=0, tzinfo=pytz.timezone("Europe/Moscow")),
                        chat_id=chat, name=str(chat))


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_config.telegram_token).build()

    # Chats night mute scheduler
    job_queue = application.job_queue
    for chat in chats:
        print(chats[chat].admin_commands['night_mute']['state'])
        if chats[chat].admin_commands['night_mute']['state'] is True:
            mute_jobs(job_queue, chat)
        print(job_queue.get_jobs_by_name(str(chat)))
    for job in job_queue.jobs():
        print(job.chat_id, job.name)

    # Keep track of which chats the bot is in
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    # application.add_handler(CommandHandler("show_chats", show_chats))

    # Handle members joining/leaving chats.
    application.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start, filters.ChatType.PRIVATE & filters.UpdateType.MESSAGE))

    # Forward the pm messages on Telegram
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE, forward))

    # VIP chat special
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.UpdateType.CHANNEL_POST, forward_vip))

    # New post announce
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.Chat(-1001540432154) & filters.Regex(f"^Бусти https://boosty.to/"),
        new_post))

    # Admin commands
    application.add_handler(MessageHandler(
            filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.Regex(f"^{bot_config.admin_command_start}"),
            adm_chat_commands))

    # Warning users
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.REPLY & filters.Regex(bot_config.warn_keyword),
        warn_user))

    # Mute users
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.REPLY & filters.Regex(f"^[M|m]ute"), mute_user))

    # Ban users
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.REPLY & filters.Regex(f"Ban"), ban_user))

    # Random fun messages
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.Regex(bot_config.random_fun_keyword),
        random_fun))

    # Random numbers game
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.Regex(bot_config.random_game_keyword),
        random_game))

    # Chat content request
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.Regex(bot_config.helper_keyword), helper))

    # Delete chat join messages
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.StatusUpdate.NEW_CHAT_MEMBERS, delete_join))

    # Moderating chats
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, moderation_msg))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.CAPTION, moderation_caption))

    # Run the bot until the user presses Ctrl-C
    # We pass 'allowed_updates' handle *all* updates including `chat_member` updates
    # To reset this, simply pass `allowed_updates=[]`
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
