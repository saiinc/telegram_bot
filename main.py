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

import logging
from typing import Optional, Tuple

from telegram import __version__ as TG_VER

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
from telegram import Chat, ChatMember, ChatMemberUpdated, Update, ForceReply
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
    'е': '[е|e|ё]',
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
    ' ': '[.|,|!|?|&|)|(|\\|\/|*|-|_|"|\'|;|®]'
}
# Регулярки для замены похожих букв и символов на русские

CWF = open('CurseWords.txt', 'r', encoding='utf-8')
CurseWords = ''.join(CWF.readlines()).split('\n')
CWF.close()


# reading the settings from the file
with open('config.json') as cf:
    js = cf.read()
    cf.close()
config = json.loads(js)
telegram_token = config.get('telegram_token')
admin1_pm = config.get('admin1_pm')
admin2_pm = config.get('admin2_pm')
test_chat1 = config.get('test_chat1')
test_chat2 = config.get('test_chat2')


hf1 = open('hello1.txt', 'r', encoding='utf-8')
hello_msg1 = ''.join(hf1.readlines()).split('{member_name}')
hf1.close()
hf2 = open('hello2.txt', 'r', encoding='utf-8')
hello_msg2 = ''.join(hf2.readlines()).split('{member_name}')
hf2.close()
gf = open('goodbye.txt', 'r', encoding='utf-8')
lynx_ruc = ''.join(gf.readlines()).split('\n')
gf.close()


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
        for word in CurseWords:
            b = fuzz.token_sort_ratio(word, w)  # Проверяю сходство слов из списка
            if b >= 85:
                logger.info(f"{w} | {b}% Матерное слово {word}")
                return f"{w} | {b}% Матерное слово {word}"
            else:
                pass
    return False


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

    if not was_member and is_member:
        await update.effective_chat.send_message(
            hello_msg1[0] + member_name + hello_msg1[1],
            parse_mode=ParseMode.HTML,
        )
        time.sleep(10)
        await update.effective_chat.send_message(
            member_name + hello_msg2[1],
            parse_mode=ParseMode.HTML,
        )
    elif was_member and not is_member:
        await update.effective_chat.send_message(
            f"{random.choice(lynx_ruc)}",
            parse_mode=ParseMode.HTML,
        )


async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward the user message."""
    await update.message.forward(admin2_pm)


async def moderation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks chat messages for unacceptable content."""
    try:
        tested_text = ""
        if update.message is not None:
            if update.message.text is not None:
                tested_text = update.message.text
            elif update.message.caption is not None:
                tested_text = update.message.caption
        elif update.edited_message is not None:
            if update.edited_message.text is not None:
                tested_text = update.edited_message.text
            elif update.edited_message.caption is not None:
                tested_text = update.edited_message.caption
        else:
            print(update)
        if tested_text:
            result_word = filter_word(tested_text)
            if result_word is not False:
                if update.message is not None:
                    await update.message.forward(admin1_pm)
                    await update.message.forward(admin2_pm)
                    if update.message.chat_id == test_chat1 or update.message.chat_id == test_chat2:
                        await update.message.reply_text(result_word)
                elif update.edited_message is not None:
                    await update.edited_message.forward(admin1_pm)
                    await update.edited_message.forward(admin2_pm)
                    if update.edited_message.chat_id == test_chat1 or update.edited_message.chat_id == test_chat2:
                        await update.message.reply_text(result_word)

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

    # Forward the pm messages on Telegram
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE, forward))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS, moderation))

    # Run the bot until the user presses Ctrl-C
    # We pass 'allowed_updates' handle *all* updates including `chat_member` updates
    # To reset this, simply pass `allowed_updates=[]`
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
