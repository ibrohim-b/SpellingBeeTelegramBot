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
from aiogram.types import FSInputFile
from dotenv import load_dotenv

from Word import Word
from db_sdk import DatabaseRepository
from dictionary_sdk import DictionaryClient, DictionaryWord

setproctitle.setproctitle("SpellingBeeBot")

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
messages_config = config['messages']

load_dotenv()
BOT_TOKEN = os.getenv('api_key')
storage = MemoryStorage()

dictionary_sdk = DictionaryClient()
db_sdk = DatabaseRepository()

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
    lastWord = Word("", "", "")


# Handle /start command
@dp.message(Command("start"))
async def authorize(message: types.Message, state: FSMContext):
    if db_sdk.user_exists(message.from_user.id) or db_sdk.user_has_name(message.from_user.id):
        await state.set_state(UserState.authorized)
        await start(message)
    else:
        await state.set_state(UserState.registration)
        await registration(message, state)


async def registration(message: types.Message, state: FSMContext):
    if not db_sdk.user_exists(message.from_user.id) or not db_sdk.user_has_name(message.from_user.id):
        await message.answer(
            text=messages_config['registration_message'],
        )
        await state.set_state(UserState.entering_name)


@dp.message(StateFilter(UserState.entering_name))
async def entering_name(message: types.Message, state: FSMContext):
    if not db_sdk.user_exists(message.from_user.id):
        db_sdk.create_user(message.from_user.id, message.text)
    elif not db_sdk.user_has_name(message.from_user.id):
        db_sdk.update_user_name(message.from_user.id, message.text)
    await state.set_state(UserState.authorized)
    await start(message)


async def start(message: types.Message):
    keyboard = [[types.InlineKeyboardButton(text="Start training",
                                            callback_data="start_training"),
                 types.InlineKeyboardButton(text="Statistics",
                                            callback_data="statistics")]]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        text=messages_config['welcome_message'],
        reply_markup=keyboard_markup,
    )


@dp.message(Command("cancel"))
async def cancel(message: types.Message, state: FSMContext):
    await state.set_state(None)
    await message.answer(
        "canceled"
    )
    await authorize(message, state)


@dp.callback_query(F.data == "start_training")
async def pick_a_word(callback: types.CallbackQuery, state: FSMContext):
    await pick_a_word(callback.message, state)


@dp.message(StateFilter(UserState.picking_new_word) or StateFilter(UserState.spelling_a_word))
async def pick_a_word(message: types.Message, state: FSMContext):
    word: Word = db_sdk.get_random_word(str(message.from_user.id))
    dictionary_word: DictionaryWord | None = dictionary_sdk.get_definition(word.word_spell)
    audio = FSInputFile(path=f"words_mp3/{word.word_spell}.mp3")
    translation = word.word_translation
    if dictionary_word:
        phonetics_list = ", ".join(dictionary_word.phonetics) if dictionary_word.phonetics else "No phonetics available"
        def_obj = dictionary_word.meanings[0].definitions[0]
        definition = def_obj.definition if def_obj.definition else "No definition available"
        example_sentence = def_obj.example.replace(word.word_spell,
                                                   "___") if def_obj.example else "No example sentence available"
        synonyms_list = ", ".join(dictionary_word.meanings[0].synonyms) if dictionary_word.meanings[
            0].synonyms else "No synonyms available"
        antonyms_list = ", ".join(dictionary_word.meanings[0].antonyms) if dictionary_word.meanings[
            0].antonyms else "No antonyms available"
    else:
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


@dp.message(StateFilter(UserState.spelling_a_word))
async def spelling_a_word(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    user_word: Word = user_data['lastWord']
    logging.info(f"User {message.from_user.id} tries to pick a {user_word}.")

    db_sdk.add_suggestion(user_word.word_id, user_id)

    if message.text.lower().strip() == user_word.word_spell.lower().strip():
        db_sdk.update_suggestion(user_word.word_id, user_id, 1)
        logging.info(f"User {message.from_user.id} picked up {user_word} correctly.")
        await message.answer(
            text=messages_config["congratulations_message"], )
        await state.set_state(UserState.start_training)
        await pick_a_word(message=message, state=state)

    else:
        logging.info(f"User {message.from_user.id} picked up {user_word} incorrectly.")
        await message.answer(
            text=messages_config["incorrect_spelling_message"].format(word=user_word.word_spell), parse_mode="HTML", )
        await state.set_state(UserState.picking_new_word)
        await pick_a_word(message=message, state=state)


@dp.callback_query(F.data == "statistics")
async def stats(callback: types.CallbackQuery):
    message = callback.message
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
