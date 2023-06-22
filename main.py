import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import datetime

# Set up Google Sheets credentials and open the spreadsheet
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open("Договор UZKIP 2023").sheet1

# Set up the Telegram bot
API_TOKEN = '6149154764:AAE1ElvT5mxrnuUaiWaHInVdOgrJox9EayA'
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


class Form(StatesGroup):
    company_name = State()
    price = State()
    inn = State()
    full_payment = State()
    signed = State()
    source = State()
    passed_to_accountant = State()
    extra_comments = State()


global counter
counter = 142


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await Form.company_name.set()
    await message.reply("Введите название компании")


@dp.message_handler(state=Form.company_name)
async def process_company_name(message: types.Message, state: FSMContext):
    await state.update_data(company_name=message.text)
    await Form.price.set()
    await message.reply("Введите название цены")


@dp.message_handler(state=Form.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await Form.inn.set()
    await message.reply("Введите ИНН")


@dp.message_handler(state=Form.inn)
async def process_inn(message: types.Message, state: FSMContext):
    await state.update_data(inn=message.text)
    await Form.full_payment.set()

    # Create inline keyboard with "Yes" and "No" buttons
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(text="Да", callback_data="full_payment_да"),
               types.InlineKeyboardButton(text="Нет", callback_data="full_payment_нет"))

    await message.reply("Была произведена полная оплата?", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith('full_payment_'), state=Form.full_payment)
async def process_full_payment(callback_query: types.CallbackQuery, state: FSMContext):
    full_payment = callback_query.data.split('_')[2]
    await state.update_data(full_payment=full_payment)
    await Form.signed.set()

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(text="Да", callback_data="signed_да"),
               types.InlineKeyboardButton(text="Нет", callback_data="signed_нет"))

    await bot.edit_message_text("Была ли подписана", callback_query.from_user.id, callback_query.message.message_id,
                                reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith('signed_'), state=Form.signed)
async def process_signed(callback_query: types.CallbackQuery, state: FSMContext):
    signed = callback_query.data.split('_')[1]
    await state.update_data(signed=signed)
    await Form.source.set()

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(text="Dedox.uz", callback_data="source_dedox.uz"),
               types.InlineKeyboardButton(text="Soliq.uz", callback_data="source_soliq.uz"))

    await bot.edit_message_text("Через какой веб-сайт произведена подпись?", callback_query.from_user.id,
                                callback_query.message.message_id, reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith('source_'), state=Form.source)
async def process_source(callback_query: types.CallbackQuery, state: FSMContext):
    source = callback_query.data.split('_')[1]
    await state.update_data(source=source)
    await Form.passed_to_accountant.set()

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(text="Да", callback_data="passed_да"),
               types.InlineKeyboardButton(text="Нет", callback_data="passed_нет"))

    await bot.edit_message_text("Переведено ли в бухгалтерию?", callback_query.from_user.id,
                                callback_query.message.message_id, reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data.startswith('passed_'), state=Form.passed_to_accountant)
async def process_passed(callback_query: types.CallbackQuery, state: FSMContext):
    passed = callback_query.data.split('_')[1]
    await state.update_data(passed_to_accountant=passed)
    await Form.extra_comments.set()
    await bot.edit_message_text("Добавьте комментарии(не обязательно)", callback_query.from_user.id,
                                callback_query.message.message_id)


@dp.message_handler(state=Form.extra_comments)
async def process_extra_comments(message: types.Message, state: FSMContext):
    extra_comments = message.text

    # Get all the gathered data from state
    data = await state.get_data()

    # Get the current date
    today = datetime.date.today().strftime("%d.%m.%Y")

    # Increment the counter
    global counter
    counter += 1

    snumber = str(counter - 9) + "/" + str(datetime.date.today().strftime("%m-%Y"))

    # Prepare the row to be inserted into the spreadsheet
    row = [counter, message.from_user.first_name, snumber, today, data.get('company_name'), data.get('price'),
           data.get('inn'), data.get('full_payment'),
           data.get('signed'), data.get('source'), data.get('passed_to_accountant'), extra_comments]

    # Insert the row into the spreadsheet
    sheet.insert_row(row, counter - 7)

    await bot.edit_message_text("Номер договора : \n")
    await bot.send_message(snumber)
    await state.finish()
    await message.reply("Ваша информация была добавлена!")


if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
