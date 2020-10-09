import requests
import telebot
from datetime import date, timedelta
import time
from dateutil.parser import *
from re import *
import json

from telebot import types

bot = telebot.TeleBot('1389053246:AAGte_l6RHFz2ecLbWtQQTYszMO91VVo2T8')

api_url = 'https://stepik.akentev.com/api/weather'

pattern = compile('\d{2}\.\d{2}')

MAIN_STATE = "main"
WEATHER_DATE_STATE = "weather_date_handler"

DAYS = {
    0: "Сегодня",
    1: "Завтра",
    2: "Послезавтра",
    3: "Через 3 дня"
}
REVERSED_DAYS = dict(map(reversed, DAYS.items()))
BTNS = [item for item in DAYS.values()]
BTNS.append('Сменить город')
markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)  # создаем клавиатуру
markup.add(*BTNS)
try:
    data = json.load(open('db/data.json', 'r', encoding='utf-8'))
except FileNotFoundError:
    data = {
        "states": {},
        "main": {},
        "city": {},
        "weather_date_handler": {}
    }


# функция обновления даты
def change_data(key, user_id, value):
    data[key][user_id] = value
    json.dump(
        data,
        open('db/data.json', 'w', encoding='utf-8'),
        indent=4,
        ensure_ascii=False)


def weather(city, day=0):
    errors_api = 0
    while True:
        try:
            return requests.get(
                api_url,
                params={'city': city, 'forecast': day}
            ).json()
        except Exception:
            if errors_api != 2:
                errors_api += 1
                print("Ошибка API")
                time.sleep(10)
            else:
                errors_api = 0
                return {}
        else:
            break


def text_weather(city, day=0):
    temp_weather = weather(city, day)
    if not temp_weather:
        summary = "Ошибка API погоды. Повторите попытку позже. В следующем месяце, например."
    else:
        summary = "{} {}. Температура воздуха: {}".format(DAYS[day], temp_weather["description"], temp_weather["temp"])
    return summary


@bot.message_handler(func=lambda message: data['states'].get(str(message.from_user.id), MAIN_STATE) == MAIN_STATE)
def main_handler(message):
    user_id = str(message.from_user.id)

    if (message.text == '/start') or (message.text == 'Сменить город'):
        data["city"].clear()
        bot.reply_to(message,
                     "Это бот-погода. Поможет узнать погоду в любом городе. Какой город интересует?",
                     reply_markup=types.ReplyKeyboardRemove())
        change_data('states', user_id, WEATHER_DATE_STATE)
    else:
        bot.reply_to(message, "Я тебя не понял. Напиши \"/start\" если хочешь узнать погоду ")


@bot.message_handler(
    func=lambda message: data['states'].get(str(message.from_user.id), MAIN_STATE) == WEATHER_DATE_STATE)
def weather_date_handler(message):
    user_id = str(message.from_user.id)
    words_list = message.text.split()  # создаем список слов в сообщении
    if user_id not in data["city"].keys():
        if "error" not in weather(message.text):  # проверяем существование города
            bot.send_message(message.from_user.id,
                             text_weather(message.text),
                             reply_markup=markup)  # Выдаем погоду на сегодня в указанном городе
            change_data('city', user_id, message.text)

        elif len(words_list) == 2:

            if words_list[1] in REVERSED_DAYS.keys():
                # погода на завтра
                bot.send_message(message.from_user.id, text_weather(words_list[0], REVERSED_DAYS[words_list[1]]),
                                 reply_markup=markup)
                change_data('city', user_id, words_list[0])

            elif pattern.match(words_list[1]):  # проверяем не указана ли погода числом
                three_days = {
                    date.today(): 0,
                    date.today() + timedelta(days=1): 1,
                    date.today() + timedelta(days=2): 2,
                    date.today() + timedelta(days=3): 3
                }
                requested_day = parse("{}.{}".format(words_list[1], date.today().year), dayfirst=True)
                requested_day = requested_day.date()

                if requested_day in three_days.keys():  # проверка на попадание в диапазон

                    bot.send_message(message.from_user.id, text_weather(words_list[0], three_days[requested_day]),
                                     reply_markup=markup)
                    change_data('city', user_id, words_list[0])
                else:
                    bot.send_message(message.from_user.id, "Я не волшебник, давай другую дату")
            else:
                bot.send_message(message.from_user.id, "Не понятный запрос. Попробуйте еще раз")
        else:
            bot.reply_to(message, "Это город, которого нет. Я тебя не понял. Повтори запрос")
    else:
        if message.text in REVERSED_DAYS.keys():
            bot.send_message(message.from_user.id, text_weather(data['city'][user_id], REVERSED_DAYS[message.text]))

        elif message.text == 'Сменить город':
            change_data('states', user_id, MAIN_STATE)
            main_handler(message)

        else:
            bot.send_message(message.from_user.id, "Я вас не понял. Выберите в меню подходящий день или смените город")


bot.polling()
