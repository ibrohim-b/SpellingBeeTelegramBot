import asyncio
import logging

import yaml
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import StateFilter
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile

from Word import Word
from db_sdk import DatabaseRepository

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
messages_config = config['messages']

BOT_TOKEN = config.get('bot_token')
DATABASE_PATH = config.get('database_path')

storage = MemoryStorage()

logging.basicConfig(level=logging.INFO, filename="bot.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage, bot=bot)

db_sdk = DatabaseRepository()


class UserState(StatesGroup):
    start_training = State()
    spelling_a_word = State()
    picking_new_word = State()
    lastWord = Word("", "", "")


# Handle /start command
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    keyboard_markup = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Pick a word")]],
        resize_keyboard=True,
        input_field_placeholder="Pick the action"
    )
    # Insert user into the database if not exists
    db_sdk.create_user(message.from_user.id)

    logging.info(f"User {message.from_user.username} {message.from_user.id} started chat.")
    await message.answer(
        text=messages_config['welcome_message'],
        reply_markup=keyboard_markup
    )
    await state.set_state(UserState.start_training)


@dp.message(F.text.lower() == "pick a word" or UserState.start_training or UserState.picking_new_word)
async def pick_a_word(message: types.Message, state: FSMContext):
    word = db_sdk.get_random_word(str(message.from_user.id))
    audio = FSInputFile(path=f"words_mp3/{word.word_spell}.mp3")
    translation = word.word_translation
    await bot.send_voice(message.chat.id, audio, caption=translation, reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(UserState.spelling_a_word)
    await state.update_data(lastWord=word)


@dp.message(StateFilter(UserState.spelling_a_word))
async def spelling_a_word(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    user_word: Word = user_data['lastWord']
    keyboard_markup = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Pick a word")]],
        resize_keyboard=True,
        input_field_placeholder="Pick the action"
    )
    logging.info(f"User {message.from_user.id} tries to pick a {user_word}.")

    db_sdk.add_suggestion(user_word.word_id, user_id)

    if message.text.lower().strip() == user_word.word_spell.lower().strip():
        db_sdk.update_suggestion(user_word.word_id, user_id, 1)
        logging.info(f"User {message.from_user.id} picked up {user_word} correctly.")
        await message.answer(
            text=messages_config["congratulations_message"],
            reply_markup=keyboard_markup)
        await state.set_state(UserState.start_training)
    else:
        logging.info(f"User {message.from_user.id} picked up {user_word} incorrectly.")
        await message.answer(
            text=messages_config["incorrect_spelling_message"].format(word=user_word.word_spell), parse_mode="HTML",
            reply_markup=keyboard_markup)
        await state.set_state(UserState.start_training)


@dp.message(Command("stats"))
async def stats(message: types.Message):
    user_id = message.from_user.id
    passed_words = db_sdk.get_total_words_passed_count(user_id)
    total_words = db_sdk.get_total_words_count()
    total_words_left = total_words - passed_words
    logging.info(f"User {message.from_user.id} requested stats.")
    await message.answer(
        text=messages_config["stats_message"].format(passed_words_count=passed_words, total_words_count=total_words,
                                                     total_words_left=total_words_left),
        parse_mode="HTML")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
