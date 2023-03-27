from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from googletrans import Translator
from playhouse.sqlite_ext import SqliteExtDatabase

from config import TOKEN
from data_base import *

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
translator = Translator()


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await bot.send_message(message.chat.id, f'Добро пожаловать, {message.from_user.first_name}!')
    await bot.send_message(message.chat.id,
                           'Вот перечень моих команд:\n /help - напомнит вам о моих функциях\n /reg - регистрирует вас в'
                           ' моей базе данных (для хранения ваших выученных слов)\n/new_words - вы отправляете мне слово на '
                           'русском, я его перевожу и сохраняю в свою базу данных\n/words - показывает уже выученные вами '
                           'слова и их перевод\n/quiz - устраивает для вас небольшой опрос для проверки ваших знаний')


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    await bot.send_message(message.chat.id,
                           'Вот перечень моих команд:\n /start - запускает наш диалог\n /reg - регистрирует вас в'
                           ' моей базе данных (для хранения ваших выученных слов)\n/new_words - вы отправляете мне слово на '
                           'русском, я его перевожу и сохраняю в свою базу данных\n/words - показывает уже выученные вами '
                           'слова и их перевод\n/quiz - устраивает для вас небольшой опрос для проверки ваших знаний')


@dp.message_handler(commands=['reg'])
async def process_registration_command(message: types.Message):
    with db:
        user = Users(chat_id=message.chat.id, username=message.from_user.first_name)
        user.save()
    await bot.send_message(message.chat.id,
                           'Поздравляю, вы зарегистрированы! Теперь вы можете отправлять выученные вами слова мне. Я сохраню их для вас в виде словаря и помогу проверить ваши знания.')


@dp.message_handler(commands=['reg'])
async def process_registration_command(message: types.Message):
    with db:
        user = Users(chat_id=message.chat.id, username=message.from_user.first_name)
        user.save()
    await bot.send_message(message.chat.id,
                           'Поздравляю, вы зарегистрированы! Теперь вы можете отправлять выученные вами слова мне. Я сохраню их для вас в виде словаря и помогу проверить ваши знания.')


@dp.message_handler(commands=['new_words'])
async def process_new_words_command(message: types.Message):
    await bot.send_message(message.chat.id,
                           "Привет! Теперь я буду переводить с русского на английский все, что ты напишешь мне. Чтобы остановить меня, просто напиши /stop.")
    if message.text == '/stop':
        await message.answer('Остановлено')
        return
    dest = 'en'
    translation = translator.translate(message.text, dest=dest).text
    await message.answer(translation)

    with db:
        user, _ = Users.get_or_create(chat_id=message.chat.id)
        Words.create(user=user, en_words=translation, ru_words=message.text)

    dp.register_message_handler(translated_words)


async def translated_words(message: types.Message):
    await process_new_words_command(message)


@dp.message_handler(commands=['words'])
async def process_knownwords_command(message: types.Message):
    await bot.send_message(message.chat.id, "Вот то, что вы уже знаете:")
    with db:
        user, _ = Users.get_or_create(chat_id=message.chat.id)
        known_words = Words.select().where(Words.user == user)
        words_list = [f"{word.en_words}-{word.ru_words}" for word in known_words]
    await bot.send_message(message.chat.id, '\n'.join(words_list))


@dp.message_handler(commands=['quiz'])
async def process_quiz_command(message: types.Message):
    if message.text == '/stop':
        await bot.send_message(message.chat.id, 'Остановлено')
        return
    with db:
        user, _ = Users.get_or_create(chat_id=message.chat.id)
        random_data = Words.select().where(Words.user == user).order_by(fn.Random()).limit(1).get()
        en_word = random_data.en_words
        ru_word = random_data.ru_words

    await bot.send_message(message.chat.id, f"Как переводится слово \"{en_word}\"?")
    dp.register_message_handler(check_answer, lambda m: m.text.lower() == ru_word.lower())


async def check_answer(message: types.Message):
    with db:
        user, _ = Users.get_or_create(chat_id=message.chat.id)
        last_word = Words.select().where(Words.user == user).order_by(Words.id.desc()).get()
        en_word = last_word.en_words
        ru_word = last_word.ru_words

    if message.text.lower() == ru_word.lower():
        await bot.send_message(message.chat.id, "Верно! Поздравляю!")
        last_word.known = True
        last_word.save()
    else:
        await bot.send_message(message.chat.id, f"Неверно! Правильный ответ: {ru_word}")
        dp.register_message_handler(check_answer, lambda m: m.text.lower() == ru_word.lower())


if __name__ == '__main__':
    executor.start_polling(dp)
db.connect()
db.create_tables([Users, Words])
executor.start_polling(dp, skip_updates=True)
