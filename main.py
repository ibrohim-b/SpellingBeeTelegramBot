import asyncio
import logging
import os

import setproctitle
import yaml
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import StateFilter
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, InputFile
from dotenv import load_dotenv

from spelling_bee_api_sdk import Word, SpellingBeeSdk

setproctitle.setproctitle("SpellingBeeBot")

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
messages_config = config['messages']

load_dotenv()
BOT_TOKEN = os.getenv('api_key')
storage = MemoryStorage()

spelling_bee_sdk = SpellingBeeSdk()

logging.basicConfig(level=logging.INFO, filename="bot.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage, bot=bot)

commands = ['start', 'cancel', 'stats']


class UserState(StatesGroup):
    # Auth
    authorized = State()
    registration = State()
    entering_name = State()
    # Training
    start_training = State()
    spelling_a_word = State()
    picking_new_word = State()
    lastWord = Word(0, "", "", None)


# Handle /start command
@dp.message(Command("start"))
async def authorize(message: types.Message, state: FSMContext):
    try:
        if spelling_bee_sdk.user_exists(message.from_user.id) or spelling_bee_sdk.user_has_name(message.from_user.id):
            await state.set_state(UserState.authorized)
            await start(message)
        else:
            await state.set_state(UserState.registration)
            await registration(message, state)

    except Exception as exception:
        logging.error(exception)


async def registration(message: types.Message, state: FSMContext):
    try:
        if not spelling_bee_sdk.user_exists(message.from_user.id) or not spelling_bee_sdk.user_has_name(
                message.from_user.id):
            await message.answer(
                text=messages_config['registration_message'],
            )
            await state.set_state(UserState.entering_name)
    except Exception as exception:
        logging.error(exception)


@dp.message(StateFilter(UserState.entering_name))
async def entering_name(message: types.Message, state: FSMContext):
    try:
        if not spelling_bee_sdk.user_exists(message.from_user.id):
            spelling_bee_sdk.create_user(message.from_user.id, message.text)
        elif not spelling_bee_sdk.user_has_name(message.from_user.id):
            spelling_bee_sdk.update_user_name(message.from_user.id, message.text)
        await state.set_state(UserState.authorized)
        await start(message)
    except Exception as exception:
        logging.error(exception)


@dp.callback_query(F.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    message = callback.message
    keyboard = [[types.InlineKeyboardButton(text="Start training",
                                            callback_data="start_training"),
                 types.InlineKeyboardButton(text="Statistics",
                                            callback_data="statistics_menu")]]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.edit_text(
        text=messages_config['welcome_message'],
        reply_markup=keyboard_markup,
    )


async def start(message: types.Message):
    keyboard = [[types.InlineKeyboardButton(text="Start training",
                                            callback_data="start_training"),
                 types.InlineKeyboardButton(text="Statistics",
                                            callback_data="statistics_menu")]]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        text=messages_config['welcome_message'],
        reply_markup=keyboard_markup,
    )


@dp.callback_query(F.data == "start_training")
async def pick_a_word(callback: types.CallbackQuery, state: FSMContext):
    await _pick_a_word(callback.message, state, user_id=callback.from_user.id)


@dp.message(StateFilter(UserState.picking_new_word) or StateFilter(UserState.spelling_a_word))
async def pick_a_word(message: types.Message, state: FSMContext):
    await _pick_a_word(message, state, user_id=message.from_user.id)


async def _pick_a_word(message: types.Message, state: FSMContext, user_id: int):
    try:
        word: Word = spelling_bee_sdk.get_random_word(user_id)
        extra_info = word.extra_info
        translation = word.word_translation
        audio: InputFile
        if extra_info:
            audio = FSInputFile(f"words_mp3/{word.word_spell}.mp3")
            phonetics_list = ", ".join(extra_info.phonetics) if extra_info.phonetics else "No phonetics available"
            def_obj = extra_info.meanings[0].definitions[0]
            definition = def_obj.definition if def_obj.definition else "No definition available"
            example_sentence = def_obj.example.replace(word.word_spell,
                                                       "___") if def_obj.example else "No example sentence available"
            synonyms_list = ", ".join(extra_info.meanings[0].synonyms) if extra_info.meanings[
                0].synonyms else "No synonyms available"
            antonyms_list = ", ".join(extra_info.meanings[0].antonyms) if extra_info.meanings[
                0].antonyms else "No antonyms available"
        else:
            audio = FSInputFile(f"words_mp3/{word.word_spell}.mp3")
            phonetics_list = "No phonetics available"
            definition = "No definition available"
            example_sentence = "No example sentence available"
            synonyms_list = "No synonyms available"
            antonyms_list = "No antonyms available"
        caption = messages_config['word_message'].format(translation=translation, phonetics_list=phonetics_list,
                                                         definition=definition,
                                                         example_sentence=example_sentence,
                                                         synonyms_list=synonyms_list,
                                                         antonyms_list=antonyms_list)
        await bot.send_voice(message.chat.id, audio, caption=caption, reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(UserState.spelling_a_word)
        await state.update_data(lastWord=word)

    except Exception as exception:
        logging.error(exception)


@dp.message(StateFilter(UserState.spelling_a_word))
async def spelling_a_word(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        user_word = user_data['lastWord']
        user_id = message.from_user.id
        logging.info(f"User {message.from_user.id} tries to pick a {user_word}.")

        spelling_bee_sdk.add_suggestion(user_word.word_id, user_id)

        if message.text.lower().strip() == user_word.word_spell.lower().strip():
            spelling_bee_sdk.update_suggestion(user_word.word_id, user_id, 1)
            logging.info(f"User {message.from_user.id} picked up {user_word} correctly.")
            await message.answer(
                text=messages_config["congratulations_message"], )
            await state.set_state(UserState.start_training)
            await pick_a_word(message=message, state=state)

        else:
            logging.info(f"User {message.from_user.id} picked up {user_word} incorrectly.")
            await message.answer(
                text=messages_config["incorrect_spelling_message"].format(word=user_word.word_spell),
                parse_mode="HTML", )
            await state.set_state(UserState.picking_new_word)
            await pick_a_word(message=message, state=state)

    except Exception as exception:
        logging.error(exception)
        await something_went_wrong(message)


@dp.callback_query(F.data == "statistics_menu")
async def stats_menu(callback: types.CallbackQuery):
    try:
        keyboard = [[types.InlineKeyboardButton(text="View your stats",
                                                callback_data="view_statistics"),
                     types.InlineKeyboardButton(text="Leaders board",
                                                callback_data="view_leaders_board")],
                    [types.InlineKeyboardButton(text="Back to main menu",
                                                callback_data="main_menu")]
                    ]
        keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
        message = callback.message
        logging.info(f"User {message.from_user.id} came into stats menu.")
        await message.edit_text(
            text=messages_config["stats_menu_message"],
            parse_mode="HTML",
            reply_markup=keyboard_markup)
    except Exception as exception:
        logging.error(exception)
        await something_went_wrong(callback.message)


@dp.callback_query(F.data == "view_statistics")
async def view_statistics(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        keyboard = [[types.InlineKeyboardButton(text="Back",
                                                callback_data="statistics_menu")]]
        keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
        message = callback.message
        words_passed = spelling_bee_sdk.get_total_words_passed_count(user_id=user_id)
        total_words = spelling_bee_sdk.get_total_words_count()
        words_left = total_words - words_passed
        logging.info(f"User {message.from_user.id} requested stats.")
        await message.edit_text(
            text=messages_config["stats_message"].format(passed_words_count=words_passed,
                                                         total_words_count=total_words,
                                                         total_words_left=words_left),
            parse_mode="HTML",
            reply_markup=keyboard_markup
        )
    except Exception as exception:
        logging.error(exception)
        await something_went_wrong(callback.message)


@dp.callback_query(F.data == "view_leaders_board")
async def view_leaders_board(callback: types.CallbackQuery):
    try:
        keyboard = [[types.InlineKeyboardButton(text="Back",
                                                callback_data="statistics_menu")]]
        keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
        message = callback.message
        logging.info(f"User {message.from_user.id} came into leaders board.")
        leaders_board = spelling_bee_sdk.get_top_list_of_users()
        leaders_board_list = ''
        for i, user in enumerate(leaders_board):
            leaders_board_list += messages_config["leaders_board_list_item"].format(
                place=i + 1,
                user_name=user.user_name,
                words_count=user.passed
            )

        await message.edit_text(
            text=messages_config["leaders_board_message"].format(leaders_board_list=leaders_board_list),
            parse_mode="HTML", reply_markup=keyboard_markup)

    except Exception as exception:
        logging.error(exception)
        await something_went_wrong(callback.message)


@dp.message(Command("cancel") and (StateFilter(UserState.start_training) or StateFilter(UserState.authorized)))
async def cancel(message: types.Message, state: FSMContext):
    await state.set_state(None)
    await message.answer(
        "canceled"
    )
    await authorize(message, state)


@dp.message()
async def something_went_wrong(message: types.Message):
    await message.answer(
        text=messages_config["something_went_wrong"],
        parse_mode="HTML"
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
