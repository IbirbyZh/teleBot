import time
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from configparser import ConfigParser
from DebtDeligator import DebtDeligator

config = ConfigParser()
config.read('config_secret')
TOKEN = config.get('Secret Key', 'token')

id_to_nick = {int(config['Chat Ids'].get(nick_name)): nick_name.capitalize() for nick_name in config['Chat Ids'].keys()}
nick_to_id = {nick_name.capitalize(): int(config['Chat Ids'].get(nick_name)) for nick_name in config['Chat Ids'].keys()}
deligator = DebtDeligator(list(id_to_nick.keys()))


def get_debt(amount, user_name):
    if amount < 0:
        return '{} to {}'.format(abs(amount), user_name)
    else:
        return '{} from {}'.format(abs(amount), user_name)


def on_chat_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if content_type != 'text' or chat_id not in id_to_nick.keys():
        return
    print(id_to_nick[chat_id], msg['text'])
    if msg['text'].isdigit():
        how_much = int(msg['text'])
        if how_much > 0:
            bot.sendMessage(chat_id, 'For who you paid {}?'.format(how_much),
                            reply_markup=ReplyKeyboardMarkup(
                                keyboard=[[KeyboardButton(text=id_to_nick[user_id]) for user_id in
                                           id_to_nick.keys()
                                           if msg['chat']['id'] != user_id] + [KeyboardButton(text='For all')]],
                                one_time_keyboard=True))
            deligator.set_amount(chat_id, how_much)
        else:
            debt = deligator.get_debt(chat_id)
            bot.sendMessage(chat_id,
                            '\n'.join([get_debt(debt[chat_id], id_to_nick[chat_id]) for chat_id in debt]))
    else:
        if not deligator.is_amount_set(chat_id):
            bot.sendMessage(chat_id, 'How much do you want to pay?')
            return
        if msg['text'] == 'For all':
            transaction_hash, transaction = deligator.add_transaction(chat_id, 0)
        elif msg['text'] in nick_to_id.keys() and msg['text'] != id_to_nick[chat_id]:
            transaction_hash, transaction = deligator.add_transaction(chat_id, nick_to_id[msg['text']])
        else:
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Yes', callback_data='y:{}'.format(transaction_hash)),
             InlineKeyboardButton(text='No', callback_data='n:{}'.format(transaction_hash))],
        ])

        for user_id in transaction['to']:
            bot.sendMessage(user_id,
                            'Accept payment {} from {}?'.format(transaction['amount'], id_to_nick[transaction['from']]),
                            reply_markup=keyboard)


def on_callback_query(msg):
    query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
    print(id_to_nick[from_id], query_data)
    if query_data[0] == 'y':
        transaction = deligator.accept_transaction(from_id, query_data[2:])
        if transaction == False:
            bot.answerCallbackQuery(query_id, text='Already accepted or canceled')
            return
        bot.answerCallbackQuery(query_id, text='You accept it!')
        if transaction is not None:
            bot.sendMessage(transaction['from'],
                            'We accept your payment: {}'.format(transaction['amount']))
            for user_id in transaction['to']:
                bot.sendMessage(user_id,
                                'We add {} to your dept to {}'.format(transaction['amount'],
                                                                      id_to_nick[transaction['from']]))
    else:
        transaction = deligator.decline_transaction(from_id, query_data[2:])
        if transaction == False:
            bot.answerCallbackQuery(query_id, text='Already accepted or canceled')
            return
        bot.sendMessage(transaction['from'],
                        'Sorry, {} decline payment from you: {}'.format(id_to_nick[from_id],
                                                                        transaction['amount']))
        bot.answerCallbackQuery(query_id, text='You decline it!')


bot = telepot.Bot(TOKEN)

MessageLoop(bot, {'chat': on_chat_message,
                  'callback_query': on_callback_query}).run_as_thread()
print('Listening ...')

while 1:
    time.sleep(10)
