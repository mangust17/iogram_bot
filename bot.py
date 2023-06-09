from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from googletrans import Translator
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
import asyncio

from config import TOKEN
from data_base import *

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
translator = Translator()


class Form(StatesGroup):
    translate = State()
    stop = State()
    question = State()
    answer = State()


@dp.message_handler(state='*', commands='/stop')
@dp.message_handler(Text(equals='/stop', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await Form.stop.set()
    await message.answer("Остановлено")
    await state.finish()


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await bot.send_message(message.chat.id, f'Добро пожаловать, {message.from_user.first_name}!')
    await bot.send_message(message.chat.id,
                           'Вот перечень моих команд:\n /help - напомнит вам о моих функциях\n /reg - регистрирует вас в'
                           ' моей базе данных (для хранения ваших выученных слов)\n/new_words - вы отправляете мне слово на '
                           'русском, я его перевожу и сохраняю в свою базу данных\n/words - показывает уже выученные вами '
                           'слова и их перевод\n/quiz - устраивает для вас небольшой опрос для проверки ваших знаний\n'
                           '/stop - остановит любой мой процесс')


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    await bot.send_message(message.chat.id,
                           'Вот перечень моих команд:\n /start - запускает наш диалог\n /reg - регистрирует вас в'
                           ' моей базе данных (для хранения ваших выученных слов)\n/new_words - вы отправляете мне слово на '
                           'русском, я его перевожу и сохраняю в свою базу данных\n/words - показывает уже выученные вами '
                           'слова и их перевод\n/quiz - устраивает для вас небольшой опрос для проверки ваших знаний\n'
                           '/stop - остановит любой мой процесс')


@dp.message_handler(commands=['reg'])
async def process_registration_command(message: types.Message):
    with db:
        user = Users(chat_id=message.chat.id, username=message.from_user.first_name)
        user.save()
    await bot.send_message(message.chat.id,
                           'Поздравляю, вы зарегистрированы! Теперь вы можете отправлять выученные вами слова мне. Я сохраню их для вас в виде словаря и помогу проверить ваши знания.')


@dp.message_handler(commands=['new_words'])
async def cmd_new_words(message: types.Message):
    await Form.translate.set()
    await message.answer(
        "Теперь я буду переводить с русского на английский все, что ты напишешь мне."
    )


@dp.message_handler(state=Form.translate)
async def translate_message(message: types.Message, state: FSMContext):
    dest = "en"
    translation = translator.translate(message.text, dest=dest).text
    await message.answer(translation)

    with db:
        user, _ = Users.get_or_create(chat_id=message.chat.id)
        Words.create(user=user, en_words=translation, ru_words=message.text)

    await message.answer("Слово сохранено!")

    await Form.translate.set()


@dp.message_handler(commands=['words'])
async def process_knownwords_command(message: types.Message):
    await bot.send_message(message.chat.id, "Вот то, что вы уже знаете:")
    with db:
        user, _ = Users.get_or_create(chat_id=message.chat.id)
        known_words = Words.select().where(Words.user == user)
        words_list = [f"{word.en_words}-{word.ru_words}" for word in known_words]
    await bot.send_message(message.chat.id, '\n'.join(words_list))


@dp.message_handler(commands=['quiz'])
async def start_quiz(message, state):
    with db:
        user, _ = Users.get_or_create(chat_id=message.chat.id)
        random_data = Words.select().where(Words.user == user).order_by(fn.Random()).limit(1).get()
        en_word = random_data.en_words
        ru_word = random_data.ru_words

    async with state.proxy() as data:
        data['ru_word'] = ru_word

    await Form.question.set()
    await message.answer(f"Как переводится слово \"{en_word}\"?")


@dp.message_handler(state=Form.question)
async def check_question(message, state):
    async with state.proxy() as data:
        ru_word = data['ru_word']

    if message.text.lower() == ru_word:
        await bot.send_message(message.chat.id, "Ответ верный!")
    else:
        await bot.send_message(message.chat.id, f"К сожалению, ответ неверный. Правильный ответ: \"{ru_word}\".")

    await asyncio.sleep(1)

    with db:
        user, _ = Users.get_or_create(chat_id=message.chat.id)
        random_data = Words.select().where(Words.user == user).order_by(fn.Random()).limit(1).get()
        en_word = random_data.en_words
        ru_word = random_data.ru_words

    async with state.proxy() as data:
        data['ru_word'] = ru_word

    await Form.question.set()
    await message.answer(f"Как переводится слово \"{en_word}\"?")


if __name__ == '__main__':
    executor.start_polling(dp)
db.connect()
db.create_tables([Users, Words])
executor.start_polling(dp, skip_updates=True)
