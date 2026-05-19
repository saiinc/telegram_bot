#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# Copyright 2025 by Anton Sorokin

"""
Simple Bot to handle '(my_)chat_member' updates.
Greets new users & keeps track of which chats the bot is in.
Usage:
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.

Телеграм бот для тематических чатов. Он работает как навигатор по тематическому контенту, удаляет спам, 
развлекает пользователей выполняя игровые команды.
"""
import traceback
import html
from typing import Dict
import datetime
import os

import rapidfuzz
from dotenv import load_dotenv
import logging
from typing import Optional, Tuple
import asyncio

import pytz
from telegram import __version__ as TG_VER, ChatPermissions, Message
from telegram.error import RetryAfter

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
from telegram import Chat, ChatMember, ChatMemberUpdated, Update, Bot
from telegram.constants import ParseMode
from telegram.ext import Application, ChatMemberHandler, CommandHandler, ContextTypes, MessageHandler, filters, ExtBot
import time
import random
import re
from fuzzywuzzy import fuzz
import json
from collections import defaultdict
from html import escape
from telegram.helpers import mention_html
import psycopg2
from psycopg2 import OperationalError
from psycopg2 import Error

import gspread  # импортируем библиотеку для работы с гугл таблицами

# Enable logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

load_dotenv(override=True)
DATABASE_URL = os.getenv("DATABASE_URL")

multi_map = {
    "ch": "ч",
    "ĳ": "й"
}

dict_re = {
    'а': '[@|а|а́|a|À|Á|Â|Ã|Ä|ͣ|Α|ά|α|ɑ|ᴀ|ᾶ|ἀ|å]',
    'б': '[б|6|b|δ|Ϭ|ϭ]',
    'в': '[в|v|ͮ|Β|ᴠ|ʙ|w]',
    'г': '[г|g|Γ|ᴦ|ɢ]',
    'д': '[д|d|ͩ|ᵭ|ᴅ]',
    'е': '[е|e|ё|ë|ᧉ|ɘ|ə|Ε|ε|ξ|Ѐ|€|é|è|ē|ě|ɇ]',
    'ж': '[ж|*|j|ʐ|*|ψ]',
    'з': '[з|3|z|Ζ|ż|ʒ|ź|ž]',
    'и': '[и|i|ͥ|Ι|μ|ῑ|ɪ|ì|í|ï|î|ι]',
    'й': '[й|ĭ]',
    'к': '[к|k|Κ|κ|Ϗ|ϗ|ᴋ|q|ƙ]',
    'л': '[л|l|Λ|λ|ʟ|ɭ]',
    'м': '[м|m|ͫ|Μ|Ϻ|ϻ|ӎ|ᴍ|ɯ]',
    'н': '[н|n|Ν|η|ħ]',
    'о': '[о|o|0|ᴏ|ͦ|Ο|ο|σ|ό|ϴ|ō|ö|ò|ó|ô|õ]',
    'п': '[п|π|Π|η|ᴨ|p]',
    'р': '[р|r|ͬ|Ρ|ρ|ᴘ|ŕ|ṙ]',
    'с': '[с|c|s|5|$|ͨ|ς|ϲ|Ϲ|Ͼ|ć|ç|$|ᴄ|č]',
    'т': '[т|t|ꚍ|τ|ͭ|Τ|τ|ᴛ|ť|†|ţ]',
    'у': '[у́|у|u|ʸ|ͧ|Υ|γ|υ|u|Ү|ÿ|ý|ỵ]',
    'ф': '[ф|f|Φ|φ|ϕ]',
    'х': '[х|x|h|ͪ|ͯ|Η|Χ|χ|ʜ|ᕽ|×|☓]',
    'ц': '[ц|ʨ|ʦ]',
    'ч': '[ч|4|Ϥ|ϥ]',
    'ш': '[ш|щ|Ϣ|ϣ]',
    'ь': '[ь]',
    'ы': '[ы]',
    #  'ъ' :   '[ъ|ь]',
    'э': '[э|ϵ|Є]',
    'ю': '[ю|u]',
    'я': '[я]',
    '': '[_|.|,|#|%|*|!|?|/]',
    # ' ': '[.|,|!|?|&|)|(|\\|\/|*|-|_|"|\'|;|®]'

}
char_map = {}

for normal_letter, regular in dict_re.items():
    # убираем квадратные скобки
    chars = regular.strip('[]').split('|')
    for ch in chars:
        char_map[ch] = normal_letter


def safe(text: str) -> str:
    return escape(text) if text else ""


def mention_user(user) -> str:
    return mention_html(user.id, user.full_name)


def execute_query(query, *params):
    connection_db = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = connection_db.cursor()
    try:
        cursor.execute(query, *params)
        connection_db.commit()
        print("Query '%s' executed successfully" % query)
    except OperationalError as e:
        print(query)
        print(f"The error '{e}' occurred")
    finally:
        if connection_db:
            cursor.close()
            connection_db.close()
            print("Close connection to PostgreSQL")


def execute_read_query(query):
    connection_db = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = connection_db.cursor()
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        print("Query '%s' executed successfully" % query)
        return result
    except OperationalError as e:
        print(query)
        print(f"The error '{e}' occurred")
    finally:
        if connection_db:
            cursor.close()
            connection_db.close()
            print("Close connection to PostgreSQL")


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
        self.private_spammers = private_spammers  # Спамят в личку боту, будут игнорироваться


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


def chat_list_bdread():
    bd_chat_list = execute_read_query(f"SELECT chat_id FROM chats_test")
    chat_list_read = []
    for bd_chat_list_record in bd_chat_list:
        chat_list_read.append(bd_chat_list_record[0])
    return chat_list_read


chat_list = chat_list_bdread()


class Helper:
    def __init__(self, delay: bool, content: str):
        self.delay = delay
        self.content = content


def helper_bdread(chat_id):
    bd_helper = execute_read_query(f"SELECT command, delay, content FROM helper_test WHERE chat_id='{chat_id}'")
    helper_dict = {}

    for helper_record in bd_helper:
        helper_dict[helper_record[0]] = Helper(delay=helper_record[1], content=helper_record[2])

    return helper_dict


'''
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
    
    # db_insert = ""
    for helper_record in file_helper_list:
        db_insert += f"('{chat}', $${helper_record['command']}$$, '{'Yes' in helper_record['delay']}', $${helper_record['content']}$$),"
    db_insert_temp = db_insert[:-1]
    db_insert = db_insert_temp + ";"
    execute_query(f"INSERT INTO helper (chat_id, command, delay, content) "
                  f"VALUES {db_insert}")
    
    return file_helper_list
'''


def msg_content_bdread(chat):
    bd_msg_content = execute_read_query(f"SELECT key, value FROM msg_content_test WHERE chat_id='{chat}'")
    msg_content = {}
    for bd_msg in bd_msg_content:
        msg_content[bd_msg[0]] = bd_msg[1]
    return msg_content


'''
def my_msg_content_read(chat):
    file_msg_content = {}
    for root, dirs, files in os.walk(f"chats/{chat}/msg_content"):
        for filename in files:
            with open(f"chats/{chat}/msg_content/" + filename, 'r', encoding="utf-8") as msgf:
                msgc = msgf.read()
                msgf.close()
            file_msg_content[filename[:filename.rfind('.')].lower()] = msgc
    return file_msg_content
'''


def str_content_bdread(chat):
    bd_str_content_raw = execute_read_query(
        f"SELECT content_type, value FROM str_content_test WHERE chat_id='{chat}' AND active='true'")
    str_content_defaultdict = defaultdict(list)
    for bd_row in bd_str_content_raw:
        str_content_defaultdict[bd_row[0]].append(bd_row[1])
    return str_content_defaultdict


'''
    temp_db = execute_read_query(f"SELECT content_type, value, chat_id FROM str_content WHERE content_type = 'rand_pervoe' AND chat_id = '-1001802121542';")
    str_temp_defaultdict = defaultdict(list)
    for temp_row in temp_db:
        str_temp_defaultdict[temp_row[0]].append(temp_row[1])

    db_insert = ""
    for key, value in str_temp_defaultdict.items():
        for single_str in value:
            db_insert += f"('-1001685882736', 'rand_pervoe', $${single_str}$$),"
    db_insert_temp = db_insert[:-1]
    db_insert = db_insert_temp + ";"
    execute_query(f"INSERT INTO str_content (chat_id, content_type, value) "
                  f"VALUES {db_insert}")
    '''

'''
def my_str_content_file_read(chat):
    file_str_content = {}
    for root, dirs, files in os.walk(f"chats/{chat}/str_content"):
        for filename in files:
            with open(f"chats/{chat}/str_content/" + filename, 'r', encoding="utf-8") as strf:
                strc = list(filter(None, strf.read().split('\n')))
                strf.close()
            file_str_content[filename[:filename.rfind('.')].lower()] = strc
    
    #db_insert = ""
    for key, value in file_str_content.items():
        for single_str in value:
            db_insert += f"('{chat}', $${key}$$, $${single_str}$$),"
    db_insert_temp = db_insert[:-1]
    db_insert = db_insert_temp + ";"
    execute_query(f"INSERT INTO str_content (chat_id, content_type, value) "
                  f"VALUES {db_insert}")
    
    return file_str_content
'''


def rp_actions_bdread(chat):
    bd_rp_actions = execute_read_query(f"SELECT action, reaction FROM rp_actions_test WHERE chat_id='{chat}'")
    rp_actions_dict = {}

    for rp_actions_record in bd_rp_actions:
        rp_actions_dict[rp_actions_record[0]] = RolePlayActions(reaction=rp_actions_record[1])

    # rp_actions_file_list = my_rp_actions_read(chat)
    return rp_actions_dict


'''
def my_rp_actions_read(chat):
    with open(f"chats/{chat}/rp_actions.json", 'r', encoding='utf-8') as rpf:
        js = rpf.read()
        rpf.close()

    file_rp_actions_dict = json.loads(js)
    
    # db_insert = ""
    for key, value in file_rp_actions_dict.items():
        db_insert += f"('{chat}', $${key}$$, $${value}$$),"
    db_insert_temp = db_insert[:-1]
    db_insert = db_insert_temp + ";"
    execute_query(f"INSERT INTO rp_actions (chat_id, action, reaction) "
                  f"VALUES {db_insert}")
    
    return file_rp_actions_dict
'''


def antispam_exceptions_bdread(chat):
    antispam_exceptions_bd = execute_read_query(
        f"SELECT channel_id FROM antispam_exceptions_test WHERE chat_id='{chat}'")
    antispam_exceptions = []
    for antispam_exceptions_record in antispam_exceptions_bd:
        antispam_exceptions.append(antispam_exceptions_record[0])
    return antispam_exceptions


def chat_config_bdread(chat):
    chat_config_list = execute_read_query(f"SELECT command, state, answer_on, answer_off FROM chat_config_test "
                                          f"WHERE chat_id='{chat}'")
    chat_config = {}
    for chat_config_record in chat_config_list:
        chat_config[chat_config_record[0]] = ChatConfig(state=chat_config_record[1], answer_on=chat_config_record[2],
                                                        answer_off=chat_config_record[3])
    return chat_config


def chat_config_bdupdate(command, state, chat):
    execute_query(
        f"UPDATE chat_config_test SET state = {state} WHERE chat_id = '{str(chat)}' AND command = '{command}';")


def support_chat_bdread(chat):
    support_chat_bd = execute_read_query(
        f"SELECT support_chat_id FROM chats_test WHERE chat_id='{chat}'")
    return int(support_chat_bd[0][0])


def bdupdate_chat_title(chat, title):
    execute_query("UPDATE chats_test SET title = %s WHERE chat_id = %s", (title, chat))


'''
def chat_config_read(chat):
    with open(f"chats/{chat}/config.json", 'r', encoding='utf-8') as cf:
        js = cf.read()
        cf.close()

        file_config = json.loads(js)
        admin_commands = file_config['admin_commands']
        db_insert = ""
        for key in admin_commands:
            print(admin_commands[key])
            db_insert += f"('{chat}', $${key}$$, '{admin_commands[key]['state']}', $${admin_commands[key]['answer_on']}$$, $${admin_commands[key]['answer_off']}$$),"
        db_insert_temp = db_insert[:-1]
        db_insert = db_insert_temp + ";"
        execute_query(f"INSERT INTO chat_config (chat_id, command, state, answer_on, answer_off) "
                      f"VALUES {db_insert}")
    return json.loads(js)
'''

'''
def chat_config_writer(config_dict, chat):
    json_object = json.dumps(config_dict, ensure_ascii=False, indent=4)
    with open(f"chats/{chat}/config.json", "w", encoding='utf-8') as outfile:
        outfile.write(json_object)
        outfile.close()
'''


def chat_content_load(chat):
    msg_content = msg_content_bdread(chat)
    str_content = str_content_bdread(chat)
    chat_title = ''
    my_chat = ChatMy(int(chat),
                     msg_content['hello'],
                     msg_content['hello_spoil'],
                     str_content['goodbye'],
                     str_content['ping_words'],
                     str_content['delete_words'],
                     str_content['profile_words'],
                     str_content['ping_rand'],
                     str_content['rand_pervoe'],
                     helper_bdread(chat),
                     rp_actions_bdread(chat),
                     chat_config_bdread(chat),  # admin_commands
                     support_chat_bdread(chat),
                     antispam_exceptions_bdread(chat),
                     chat_title)
    return my_chat


class RolePlayActions:
    def __init__(self, reaction: str):
        self.reaction = reaction


class ChatConfig:
    def __init__(self, state: bool, answer_on: str, answer_off: str):
        self.state = state
        self.answer_on = answer_on
        self.answer_off = answer_off


class ChatMy:
    def __init__(self, chat: int, hello, hello_spoil, goodbye: list, ping_words, delete_words: list,
                 profile_words: list, ping_rand, rand_pervoe, helper: Dict[str, Helper],
                 rp_actions: Dict[str, RolePlayActions], chat_config: Dict[str, ChatConfig], support_chat: int,
                 antispam_exceptions, chat_title):
        self.chat = chat
        self.hello = hello
        self.hello_spoil = hello_spoil

        self.goodbye = goodbye
        self.ping_words = ping_words
        self.delete_words = delete_words
        self.profile_words = profile_words
        self.ping_rand = ping_rand
        self.rand_pervoe = rand_pervoe

        self.helper = helper
        self.rp_actions = rp_actions

        self.chat_config = chat_config
        self.support_chat = support_chat
        self.antispam_exceptions = antispam_exceptions  # Кому можно писать в чат от имени своего канала (id каналов, от имени которых можно писать в чат)
        self.chat_title = chat_title


chats = {}
ADMIN_CACHE = {}
ADMIN_CACHE_TTL = 600  # 10 минут

for user_chat_id in chat_list:
    chats[int(user_chat_id)] = chat_content_load(user_chat_id)

for dict_key in chats:
    user_chat_id = chats[dict_key]
    print(dict_key, user_chat_id.support_chat, user_chat_id.rp_actions)

ignore = []


def get_chat_by_support(chat_id):
    for chat_val in chats.values():
        if chat_val.support_chat == chat_id:
            return chat_val.chat


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
    # сначала multi-char
    for k, v in multi_map.items():
        word = word.replace(k, v)
    return ''.join(char_map.get(c, c) for c in word)


def delete_word(msg, chat):
    if chats.get(chat) is not None:
        pass
    else:
        chat = get_chat_by_support(chat)

    msg = msg.lower()
    for word in chats[chat].delete_words:
        if word in msg:
            return f"Фраза-триггер: {word}"

    msg = msg.split()
    for w in msg:
        w_normalize = ''.join([w[i] for i in range(len(w) - 1) if w[i + 1] != w[i]] + [
            w[-1]])  # Здесь убираю символы которые повторяються "Приииииивет" -> "Привет"
        w_normalize = replace_letters(w_normalize)

        for word in chats[chat].delete_words:
            b = rapidfuzz.fuzz.token_sort_ratio(word, w_normalize)  # Проверяю сходство слов из списка
            if b >= 100:
                return f"{w} | {b}% Слово-триггер: {word}"
            else:
                pass

        '''admin trigger words'''
        if chats[chat].chat_config["ping_words"].state is True:
            for word in chats[chat].ping_words:
                if word == w:
                    return f"Пинг-триггер: {word}"
                else:
                    pass

    return False


def profile_word(user, chat, context):
    if chats.get(chat) is not None:
        pass
    else:
        chat = get_chat_by_support(chat)

    username = user.full_name.lower()
    username = ''.join([username[i] for i in range(len(username) - 1) if username[i + 1] != username[i]] + [
        username[-1]])  # Здесь убираю символы которые повторяються "Приииииивет" -> "Привет"
    username = replace_letters(username)

    username = F"{username} {user.id}"

    for word in chats[chat].profile_words:
        if word in username:
            return f"Профиль-триггер: {word}"

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


async def get_admin_ids(chat):
    now = time.time()

    if chat.id in ADMIN_CACHE:
        cached, ts = ADMIN_CACHE[chat.id]
        if now - ts < ADMIN_CACHE_TTL:
            return cached

    admins = await chat.get_administrators()
    ids = {adm.user.id for adm in admins}

    ADMIN_CACHE[chat.id] = (ids, now)
    return ids


async def antispam(update, context):
    msg = update.effective_message
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = get_chat_by_support(update.effective_chat.id)
    """Delete messages from user as channel's sender"""
    if msg.sender_chat is not None:
        if msg.sender_chat.id != msg.chat.id:
            if str(msg.sender_chat.id) not in chats[chat].antispam_exceptions:
                if (msg.reply_to_message is None) and (
                        chats[chat].chat_config['delete_from_channel_alone_msg'].state is True):
                    await context.bot.deleteMessage(msg.chat.id, msg.message_id)
                    return "message_deleted"
                if (msg.reply_to_message is not None) and (
                        chats[chat].chat_config['delete_from_channel_reply'].state is True):
                    await context.bot.deleteMessage(msg.chat.id, msg.message_id)
                    return "message_deleted"
            else:
                return "channel_post"
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

    admin_ids = await get_admin_ids(msg.chat)
    if msg.from_user.id not in admin_ids:
        for message_entity in message_entities:
            if message_entity.type == 'url' or message_entity.type == 'text_link':
                if chats[chat].chat_config['delete_links'].state is True:
                    if chats[chat].chat_config['alerts'].state is True:
                        await moderation_alert_sender(update, "Detect link!", context)
                    await context.bot.deleteMessage(msg.chat.id, msg.message_id)
                    await asyncio.sleep(0.1)
                    return "message_deleted"
            elif message_entity.type == 'mention' or message_entity.type == 'phone_number' or message_entity.type == 'hashtag':
                if chats[chat].chat_config['delete_mention&phone'].state is True:
                    if chats[chat].chat_config['alerts'].state is True:
                        await moderation_alert_sender(update, "Detect mention or phone or hashtag!", context)
                    await context.bot.deleteMessage(msg.chat.id, msg.message_id)
                    await asyncio.sleep(0.1)
                    return "message_deleted"
        return


async def moderation_alert_sender(update, result_word, context, edited=False):
    from_user = update.effective_message.from_user
    caption = update.effective_message.caption_html
    text = update.effective_message.text_html
    link = update.effective_message.link

    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = get_chat_by_support(update.effective_chat.id)
    username = ("@" + from_user.username) if from_user.username is not None else ""
    user = f"{mention_user(from_user)}{(', ' + username) if username != '' else ''}, {from_user.id}"
    edit_str = "сообщение отредактировано"
    empty_str = ""
    try:
        await context.bot.send_message(chat_id=chats[chat].support_chat,
                                       text=f"<b>{user}</b> \n{text if text is not None else caption} \n{link} \n"
                                            f"{result_word} \n"
                                            f"{edit_str if edited is not False else empty_str}",
                                       parse_mode=ParseMode.HTML)
    except RetryAfter as e:
        chats[chat].chat_config['alerts'].state = False
        await asyncio.sleep(0.1)
        # chat_config_bdupdate('alerts', chats[chat].chat_config['alerts'].state, chat)
        await context.bot.send_message(text=f"Аварийное {e}: "
                                            f"{chats[chat].chat_config['alerts'].answer_off}",
                                       parse_mode=ParseMode.HTML,
                                       chat_id=chats[chat].support_chat)
        await asyncio.sleep(e.retry_after)
    except Exception as e:
        chats[chat].chat_config['alerts'].state = False
        await asyncio.sleep(0.1)
        # chat_config_bdupdate('alerts', chats[chat].chat_config['alerts'].state, chat)
        await context.bot.send_message(text=f"Аварийное {e}: "
                                            f"{chats[chat].chat_config['alerts'].answer_off}",
                                       parse_mode=ParseMode.HTML,
                                       chat_id=chats[chat].support_chat)


async def moderatorial_user_sender(update, context):
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = get_chat_by_support(update.effective_chat.id)
    msg = update.message
    msg_reply = update.message.reply_to_message
    await context.bot.send_message(chat_id=chats[chat].support_chat,
                                   text=f'{str(msg_reply.text_html or "") + str(msg_reply.caption_html or "")} |{msg.text_html}| '
                                        f'{safe(msg_reply.from_user.first_name)}, '
                                        f'{safe(msg_reply.from_user.username)}, id: {msg_reply.from_user.id}',
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
        chat_id = get_chat_by_support(chat.id)

    if not was_member and is_member:
        if chat.permissions.can_send_messages:
            if chats[chat_id].chat_config['notify_join'].state is True:
                user = f"{update.chat_member.new_chat_member.user.first_name}, " \
                       f"{update.chat_member.new_chat_member.user.username}, " \
                       f"{update.chat_member.new_chat_member.user.id}"
                text = "now joined."
                await context.bot.send_message(chat_id=chats[chat_id].support_chat, text=f"‼<b>{user}</b> \n{text}‼",
                                               parse_mode=ParseMode.HTML)
            if chats[chat_id].chat_config['hello'].state is True:
                if chats[chat_id].chat_config['spoilers'].state is False:
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
        if chats[chat_id].chat_config['goodbye'].state is True:
            await update.effective_chat.send_message(
                f"{random.choice(chats[chat_id].goodbye)}",
                parse_mode=ParseMode.HTML,
            )


async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward the private user message."""
    """Пересылка сообщений пользователей из лички бота главному админу. Админ может пользователя отправить в игнор."""
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
        chat = get_chat_by_support(update.effective_chat.id)
    if chats[chat].chat_config['delete_join'].state is True:
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
    if update.effective_message.text_html is not None:
        message_text = update.effective_message.text_html
    elif update.effective_message.caption_html is not None:
        message_text = update.effective_message.caption_html
    else:
        message_text = None

    """Copy all massages from anon admin"""
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = get_chat_by_support(update.effective_chat.id)
    if chats[chat].chat_config['q&a'].state is True:
        if update.message is not None and update.message.sender_chat is not None:
            anon = update.message.sender_chat.id
            if anon == update.message.chat.id:
                if update.message.reply_to_message is not None:
                    await context.bot.send_message(chat_id=chats[chat].support_chat,
                                                   text=f"From: {update.message.author_signature}\n\n"
                                                        f"Original: {update.message.reply_to_message.from_user.id}, {update.message.reply_to_message.from_user.username}, {update.message.reply_to_message.from_user.full_name}\n"
                                                        f"{update.message.reply_to_message.text}\n\n"
                                                        f"Text: {message_text}"
                                                   )
                else:
                    await context.bot.send_message(chat_id=chats[chat].support_chat,
                                                   text=f"From: {update.message.author_signature}\n\n"
                                                        f"Text: {message_text}"
                                                   )

    """Role-play commands"""
    if update.message is not None and update.message.reply_to_message is not None:
        user_command = [word for word in message_text.split()]
        for action in chats[chat].rp_actions:
            if user_command[0].lower() == action:
                await context.bot.send_message(chat_id=update.message.chat.id,
                                               text=f"{chats[chat].rp_actions[action].reaction} "
                                                    f"{update.message.reply_to_message.from_user.mention_html()} "
                                                    f"{' '.join(user_command[1:])}",
                                               parse_mode=ParseMode.HTML)

    """Checks channel comments for spam urls."""
    antispam_result = await antispam(update, context)
    if antispam_result == "channel_post":
        return
    elif antispam_result == "message_deleted":
        return

    """Checks chat messages for unacceptable content."""
    result_word = delete_word(message_text, update.effective_chat.id)
    if result_word is not False:
        if chats[chat].chat_config['alerts'].state is True:
            try:
                if update.edited_message is None:
                    await moderation_alert_sender(update, result_word, context, edited=False)
                else:
                    await moderation_alert_sender(update, result_word, context, edited=True)
            except Exception as e:
                logger.exception(e)
        if 'Пинг-триггер' not in result_word:
            try:
                await context.bot.deleteMessage(update.effective_chat.id, update.effective_message.id)
                await asyncio.sleep(0.1)
            except Exception as error:
                print(f"[{time.strftime('%H:%M:%S')}] Failed to delete message {update.effective_message.id}: {error}")
            return

    """Checks sender profile for unacceptable content."""
    result_word = profile_word(update.effective_user, update.effective_chat.id, context)
    if result_word is not False:
        if chats[chat].chat_config['alerts'].state is True:
            await moderation_alert_sender(update, result_word, context, edited=False)
            try:
                await context.bot.deleteMessage(update.effective_chat.id, update.effective_message.id)
                await asyncio.sleep(0.1)
            except Exception as error:
                print(f"[{time.strftime('%H:%M:%S')}] Failed to delete message {update.effective_message.id}: {error}")


async def random_fun(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot replies a random string from list"""
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = get_chat_by_support(update.effective_chat.id)
    await update.message.reply_html(random.choice(chats[chat].ping_rand))


async def random_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot replies a random number"""
    global ignore
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = get_chat_by_support(update.effective_chat.id)
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
        chat = get_chat_by_support(update.effective_chat.id)
    if await detect_chat_adm(msg) is True:
        admin_message = msg.text
        if admin_message == f"{bot_config.admin_command_start}{bot_config.admin_command_update}":  # обновление конфигурации чатов
            bot_config = bot_config_load()
            chats[chat] = chat_content_load(chat)
            chat_info = await context.bot.getChat(chat)
            bdupdate_chat_title(str(chat), chat_info.title)
            current_jobs = context.job_queue.get_jobs_by_name(str(chat))
            if chats[chat].chat_config['night_mute'].state is True and not current_jobs:
                mute_jobs(context.job_queue, chat)
                await update.message.reply_html('Jobs created')
                return
            elif chats[chat].chat_config['night_mute'].state is False and current_jobs:
                for job in current_jobs:
                    job.enabled = False
                    job.schedule_removal()
                    await update.message.reply_html('Job destroyed')
                    return
            print(current_jobs)
            await update.message.reply_html(
                'Ok')
            return
        if admin_message == bot_config.admin_command_start:  # список настроек в чат
            chat_info = await context.bot.getChat(chat)
            command_list = []
            for command in chats[chat].chat_config:
                original_string = chats[chat].chat_config[command].answer_on
                words = original_string.split()  # Разделяем строку на слова
                words.pop()  # Удаляем последнее слово из списка
                result_string = " ".join(words)  # Собираем оставшиеся слова обратно в строку
                command_list.append(f"{result_string} ({command}): {str(chats[chat].chat_config[command].state)}")
            command_list_message = '\n'.join(sorted(command_list))
            await update.message.reply_html(f"Параметры чата {chat} {chat_info.title}: \n{command_list_message}")
            return
        for command in chats[chat].chat_config:  # изменение настроек чата
            if admin_message == f"{bot_config.admin_command_start}{command}_off" and \
                    chats[chat].chat_config[command].state is True:
                await update.effective_chat.send_message(
                    chats[chat].chat_config[command].answer_off,
                    parse_mode=ParseMode.HTML,
                )
                chats[chat].chat_config[command].state = False
                chat_config_bdupdate(command, chats[chat].chat_config[command].state, chat)
                return
            elif admin_message == f"{bot_config.admin_command_start}{command}_on" and \
                    chats[chat].chat_config[command].state is False:
                await update.effective_chat.send_message(
                    chats[chat].chat_config[command].answer_on,
                    parse_mode=ParseMode.HTML,
                )
                chats[chat].chat_config[command].state = True
                chat_config_bdupdate(command, chats[chat].chat_config[command].state, chat)
                return
    else:
        await update.message.reply_html(bot_config.non_admin_answer)


async def show_helper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if chats.get(update.effective_chat.id) is not None:
        chat = update.effective_chat.id
    else:
        chat = get_chat_by_support(update.effective_chat.id)
    try:
        if update.message is not None:
            command = replace_letters(update.message.text)
            if command in chats[chat].helper:
                if chats[chat].helper[command].delay is True:
                    await update.message.reply_html(
                        f"{random.choice(chats[chat].rand_pervoe)}")
                    time.sleep(8)
                await update.message.reply_html(
                    chats[chat].helper[command].content,
                    # reply_markup=ForceReply(selective=True),
                )
                return
            await moderation_msg(update, context)
    except AttributeError:
        print(AttributeError.args)
        print(update)


async def get_chat_info(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_info = await context.bot.getChat(job.chat_id)
    print(chat_info.title)
    chats[job.chat_id].chat_title = chat_info.title
    bdupdate_chat_title(str(job.chat_id), chat_info.title)


async def chat_mute(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.set_chat_permissions(chat_id=job.chat_id, permissions=ChatPermissions(can_send_messages=False))
    if chats[job.chat_id].chat_config['hello'].state is True:
        chats[job.chat_id].chat_config['hello'].state = False
    if chats[job.chat_id].chat_config['goodbye'].state is True:
        chats[job.chat_id].chat_config['goodbye'].state = False
    await context.bot.send_message(chat_id=job.chat_id, text='Комментарии закрываются! Спокойной ночи. ✨')


async def chat_unmute(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.set_chat_permissions(chat_id=job.chat_id, permissions=ChatPermissions(can_send_messages=True,
                                                                                            can_send_audios=False,
                                                                                            can_send_videos=False,
                                                                                            can_send_documents=False,
                                                                                            can_send_polls=False,
                                                                                            can_send_video_notes=False,
                                                                                            can_send_voice_notes=False,
                                                                                            can_send_other_messages=True,
                                                                                            can_add_web_page_previews=False,
                                                                                            can_send_photos=True))

    await context.bot.send_message(chat_id=job.chat_id, text='Комментарии открыты! Доброе утро. 🌼')


def mute_jobs(job_queue, chat):
    job_queue.run_daily(chat_mute, datetime.time(hour=22, minute=0, tzinfo=pytz.timezone("Europe/Moscow")),
                        chat_id=chat, name=str(chat))
    job_queue.run_daily(chat_unmute, datetime.time(hour=7, minute=0, tzinfo=pytz.timezone("Europe/Moscow")),
                        chat_id=chat, name=str(chat))


def info_job(job_queue, chat):
    job_queue.run_once(get_chat_info, 0, chat_id=chat, name=str(chat))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_config.telegram_token).concurrent_updates(True).build()

    # Chats night mute scheduler
    job_queue = application.job_queue
    for chat in chats:
        info_job(job_queue, chat)
        print(chats[chat].chat_config['night_mute'].state)
        if chats[chat].chat_config['night_mute'].state is True:
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
        filters.ChatType.GROUPS & filters.UpdateType.MESSAGE & filters.Regex(bot_config.helper_keyword), show_helper))

    # Delete chat join messages
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.StatusUpdate.NEW_CHAT_MEMBERS, delete_join))

    # Moderating chats
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, moderation_msg))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.CAPTION, moderation_msg))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS, antispam))

    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    # We pass 'allowed_updates' handle *all* updates including `chat_member` updates
    # To reset this, simply pass `allowed_updates=[]`
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
