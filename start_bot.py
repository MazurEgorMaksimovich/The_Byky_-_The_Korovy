import random
import string
from itertools import product

import telebot

from config import BOT_TOKEN
from user import User, DFAULT_USER_LEVEL, get_or_create_user, save_user, del_user

GAME_MODES = ('Компьютер', 'Человек', 'Дуэль')

bot = telebot.TeleBot(BOT_TOKEN)
#guessed_number = ''
#tries = -1 # tries == -1 или -2, если игра неактивна.

def get_bulls_cows(text1, text2):
    bulls = cows = 0
    for i in range(min(len(text1), len(text2))):
        if text1[i] in text2:
            if text1[i] == text2[i]:
                bulls += 1
            else:
                cows += 1
    return bulls, cows

def get_buttons(*args):
    buttons = telebot.types.ReplyKeyboardMarkup(
        one_time_keyboard=True,
        resize_keyboard=True
    )
    buttons.add(*args)
    return buttons

@bot.message_handler(commands=['start', 'game'])
def select_mode(message):
    user = get_or_create_user(message.from_user.id)
    user.mode = ''
    user.reset()
    response = 'Выбери режим игры:'
    bot.send_message(message.from_user.id, response, reply_markup= get_buttons(*GAME_MODES))

@bot.message_handler(commands=['level'])
def select_level(message):
    user = get_or_create_user(message.from_user.id)
    user.level
    user.reset()
    save_user(message.from_user.id, user)
    response = 'Выбери количество цифр в числе:'
    bot.send_message(message.from_user.id, response, reply_markup= get_buttons('3', '4', '5'))

def start_game(message, level=DFAULT_USER_LEVEL):
    user = get_or_create_user(message.from_user.id)
    if not user.mode:
        select_mode(message)
        return
    if user.mode in ('bot', 'duel'):
        digits = [s for s in string.digits]
        guessed_number = ''
        for pos in range(level):
            if pos:
                digit = random.choice(digits)
            else:
                digit = random.choice(digits[1:])
            guessed_number += digit
            digits.remove(digit)
        print(f'{guessed_number} for {message.from_user.username}')
        user.level = level
        user.reset(guessed_number)
        save_user(message.from_user.id, user)
        if user.mode == 'bot':
            response = f'{message.from_user.first_name}, я загадал {level}-значное число с неповторяющимися цифрами. Ты обязан его отгадать.'
        else:
            response = f'{message.from_user.first_name}, я загадал {level}-значное число с неповторяющимися цифрами. Загадай тоже. Ты обязан отгадать моё число раньше, чем я отгадаю твоё. Но учти, у меня самая быстрая реакция на всём Диком Западе.'
        bot.reply_to(message, response)
    elif user.mode == 'user':
        user.level = level
        save_user(message.from_user.id, user)
        bot.reply_to(message, f'{message.from_user.first_name}, загадай {level}-значное число. Я попробую его отгадать, а ты присылай мне количество быков с коровами в моих вариантах.')
        bot_answer_with_guess(message, user)

@bot.message_handler(commands=['help'])
def show_help(message):
    bot.reply_to(message,"""Игра "Быки и коровы" --- игра, Ваша цель в которой --- отгадать многозначное число (цифры в котором не повторяются). После каждой попытки, Вас уведомляют о количестве угаданных цифр, расположенных на своих местах (быки) и цифр, которые в числе имеются, но стоят на иной позиции (коровы).""" )

@bot.message_handler(content_types=['text'])
def bot_answer(message):
    text = message.text
    user = get_or_create_user(message.from_user.id)
    if user.number and (user.mode == 'bot' or (user.mode == 'duel' and user.next_turn)):
        bot_answer_to_user_guess(message, user, text)
    elif user.mode == 'user' and text not in ('3', '4', '5', 'Ладно', 'Просто признай поражение', 'Нет, не хочу тебя расстраивать'):
        bot_answer_with_guess(message, user)
    elif user.mode == 'duel' and not user.next_turn:
        if bot_has_won(message, user):
            return
        response = ''
        for number, bulls, cows in user.user_history:
            response += f'\n{number} | {bulls} | {cows}'
        response += f'\n\n{user.tries + 1}-ая попытка\nХоди.'
        bot.send_message(message.from_user.id, response)
        user.next_turn = True
        save_user(message.from_user.id, user)
    else:
        bot_answer_not_in_game(message, user, text)

def bot_answer_to_user_guess(message, user, text):
    oklmn = ''
    if len(text) == user.level and text.isnumeric() and len(text) == len(set(text)):
        bulls, cows = get_bulls_cows(text, user.number)
        history = list(user.user_history)
        history.append((text, bulls, cows))
        user.user_history = tuple(history)
        user.tries += 1
        user.next_turn = False
        if bulls == user.level:
            response = f'{user.tries}-ая попытка. \n Ты угадал :(. \n Я требую реванша!'
            user.reset()
            save_user(message.from_user.id, user)
            bot.send_message(message.from_user.id, response, reply_markup=get_buttons('Ладно', 'Горе побеждённым!'))
            return
        else:
            response = f'{user.tries}-ая попытка. \n Быки -- {bulls}, коровы -- {cows}.'
            save_user(message.from_user.id, user)
            if user.mode == 'duel':
                oklmn = 'ugu'
    else:
        response = f'Это не {user.level}-значное число с неповторяющимися цифрами.'
    bot.send_message(message.from_user.id, response)
    if oklmn == 'ugu':
        bot_answer_with_guess(message, user)

def bot_answer_not_in_game(message, user, text):
    if text in ('3', '4', '5'):
        start_game(message, int(text))
        return
    if text == 'Ладно':
        select_level(message)
        return
    elif not user.mode and text in GAME_MODES:
        if text == 'Компьютер':
            user.mode = 'bot'
        elif text == 'Человек':
            user.mode = 'user'
        elif text == 'Дуэль':
            user.mode = 'duel'
        save_user(message.from_user.id, user)
        select_level(message)
        return
    else:
        if text == 'Горе побеждённым!':
            response = 'Ничтожество и трус! Тебе просто повезло!'
        elif text == 'Просто признай поражение':
            response = 'Жулик и зазнайка! Ты ещё рассплатишься за содеянное!'
        elif text == 'Нет, не хочу тебя расстраивать':
            response = 'Испугался, трусишка? Правильно, беги, поджав хвост, пока цел!'
    bot.send_message(message.from_user.id, response)

def bot_answer_with_guess(message, user):
    if user.mode == 'user' and bot_has_won(message, user):
        return
    history = list(user.history)
    all_variants = [''.join(x) for x in product(string.digits, repeat=user.level)
                    if len(x) == len(set(x)) and x[0] != '0']
    while all_variants:
        guess = random.choice(all_variants)
        all_variants.remove(guess)
        if is_complatible(guess, history):
            break
    else:
        response = 'Обмануть меня вздумал, да? \n \nК сожелению, ты слишком глуп для этого! При такой комбинации ответов правильного числа не существует! \n \nЯ требую переиграть эту партию!' #К сожалению, ты дебил.
        user.reset()
        save_user(message.from_user.id, user)
        bot.send_message(message.from_user.id, response, reply_markup=get_buttons('Ладно', 'Просто признай поражение'))
        return
    history.append((guess, None, None))
    user.history = tuple(history)
    save_user(message.from_user.id, user)
    keys = []
    for bulls in range(user.level + 1):
        for cows in range(user.level + 1 - bulls):
            keys.append(f'{bulls}-{cows}')
    if user.mode == 'user':
        user.tries += 1
    response = f'{user.tries}-ая попытка. \nМоё предположение: {guess}\nНасколько я прав?'
    bot.send_message(message.from_user.id, response, reply_markup=get_buttons(*keys))

def is_complatible(guess, history):
    return all(get_bulls_cows(guess, previous_guess) == (bulls, cows)
               for previous_guess, bulls, cows in history)

def bot_has_won(message, user):
    history = list(user.history)
    if history:
        try:
            history[-1] = (history[-1][0], *[int(x) for x in message.text.split('-')])
            if history[-1][1] == user.level:
                response = 'Это было слишком просто. Не хочешь доказать свою никчёмность ещё разок?'
                user.reset()
                save_user(message.from_user.id, user)
                bot.send_message(message.from_user.id, response, reply_markup=get_buttons('Ладно', 'Нет, не хочу тебя расстраивать'))
                return True
            user.history = tuple(history)
            save_user(message.from_user.id, user)
        except ValueError:
            user.reset()
            save_user(message.from_user.id, user)
            bot.send_message(message.from_user.id, 'Игра приостановленна из-за нарушений законов Республики Беларусь.')
            return True
    return False

if __name__ == '__main__':
    print("Schallom!")
    bot.polling(non_stop=True)