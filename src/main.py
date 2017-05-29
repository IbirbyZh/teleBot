import time
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telepot.delegate import (
    per_chat_id, create_open, pave_event_space, include_callback_query_chat_id)
from configparser import ConfigParser
from DebtDeligator import DebtDeligator

config = ConfigParser()
config.read('config_secret')
TOKEN = config.get('Secret Key', 'token')

id_to_nick = {int(config['Chat Ids'].get(nick_name)): nick_name.capitalize() for nick_name in config['Chat Ids'].keys()}
nick_to_id = {nick_name.capitalize(): int(config['Chat Ids'].get(nick_name)) for nick_name in config['Chat Ids'].keys()}
user_ids = list(id_to_nick.keys())
deligator = DebtDeligator(user_ids)
propose_records = telepot.helper.SafeDict()
transaction_msgs = telepot.helper.SafeDict()
transaction_hashes = telepot.helper.SafeDict()


def get_debt(amount, user_name):
    if amount < 0:
        return '{} -> {}'.format(abs(amount), user_name)
    else:
        return '{} -> {}'.format(user_name, abs(amount))


class DebtBot(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(DebtBot, self).__init__(*args, **kwargs)

        # Retrieve from database
        if self.id in propose_records:
            self._amount, self._to_ids, self._decline_msg_id = propose_records[self.id]
            self._transaction_hash = transaction_hashes[self.id]
        else:
            self._amount = None
            self._to_ids = None
            self._transaction_hash = None
            self._decline_msg_id = None
            transaction_hashes[self.id] = None

    def _request(self):
        if self._amount is None:
            self._request_amount()
        elif self._to_ids is None:
            self._request_recipient()
        else:
            print('All defined')

    def _request_amount(self):
        if self._to_ids is None:
            self.sender.sendMessage('Сколько ты хочешь заплатить?')
        else:
            self.sender.sendMessage(
                'Сколько ты хочешь заплатить за {}?'.format(
                    id_to_nick[self._to_ids[0]] if len(self._to_ids) == 1 else 'всех'))

    def _request_recipient(self):
        msg = 'За кого ты хочешь заплатить?' if self._amount is None \
            else 'За кого ты хочешь заплатить {}?'.format(self._amount)

        self.sender.sendMessage(msg,
                                reply_markup=ReplyKeyboardMarkup(
                                    keyboard=[[KeyboardButton(text=id_to_nick[user_id]) for user_id in
                                               user_ids
                                               if user_id != self.id] + [
                                                  KeyboardButton(text='За всех')]],
                                    one_time_keyboard=True))

    def _sorry(self):
        self.sender.sendMessage('Я не понимаю')

    def _start_transaction(self):
        self._transaction_hash = transaction_hashes[self.id]
        if self._transaction_hash is None:
            transaction = deligator.add_transaction(self.id, self._to_ids, self._amount)
            self._transaction_hash = transaction['transaction_hash']
            transaction_hashes[self.id] = transaction['transaction_hash']
            print('new transaction:{}'.format(transaction['transaction_hash']))
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Да', callback_data='y:{}'.format(transaction['transaction_hash'])),
                 InlineKeyboardButton(text='Нет', callback_data='n:{}'.format(transaction['transaction_hash']))],
            ])

            transaction_msgs[transaction['transaction_hash']] = {}
            for user_id in transaction['to']:
                transaction_msgs[transaction['transaction_hash']][user_id] = \
                    telepot.message_identifier(bot.sendMessage(user_id,
                                                               'Принять платеж {} от {}?'.format(
                                                                   transaction['amount'],
                                                                   id_to_nick[transaction['from']]),
                                                               reply_markup=keyboard))
            self._amount = None
            self._to_ids = None
            self._transaction_hash = None
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='Да', callback_data='Y:{}'.format(self._transaction_hash)),
                 InlineKeyboardButton(text='Нет', callback_data='N:{}'.format(self._transaction_hash))],
            ])
            self._decline_msg_id = telepot.message_identifier(
                self.sender.sendMessage('У вас уже есть текущий запрос, вы хотите его отменить?',
                                        reply_markup=keyboard))

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type != 'text':
            print('Not text')
            return
        print(id_to_nick[chat_id], msg['text'])

        if msg['text'].isdigit():
            amount = int(msg['text'])
            if amount > 0:
                self._amount = amount
            else:
                debt = deligator.get_debt(chat_id)
                self.sender.sendMessage(
                    '\n'.join([get_debt(debt[chat_id], id_to_nick[chat_id]) for chat_id in debt]))
                return
        else:
            if msg['text'] == 'За всех':
                self._to_ids = [user_id for user_id in user_ids if user_id != chat_id]
            elif msg['text'] in nick_to_id.keys() and msg['text'] != id_to_nick[chat_id]:
                self._to_ids = [nick_to_id[msg['text']]]
            else:
                self._sorry()

        if self._amount is None or self._to_ids is None:
            self._request()
        else:
            self._start_transaction()

    def _close_transaction(self, transaction, result):
        transaction_hash = transaction['transaction_hash']
        if result:
            bot.sendMessage(transaction['from'], 'Ваша транакция подтверждена')
            transaction_hashes[transaction['from']] = None
            for user_id in transaction['to']:
                bot.editMessageText(transaction_msgs[transaction_hash][user_id],
                                    'Оплата успешно подтверждена\n{} заплатил за вас {}'.format(
                                        id_to_nick[transaction['from']], transaction['amount']), reply_markup=None)
                bot.sendMessage(transaction['from'],
                                'Вы заплатили {1} за {0}'.format(id_to_nick[user_id], transaction['amount']))
            del transaction_msgs[transaction_hash]
        else:
            bot.sendMessage(transaction['from'], 'Вашу транакцию отменили')
            transaction_hashes[transaction['from']] = None
            for user_id in transaction['to']:
                msg = 'Вы отменили оплату' if user_id == self.id else '{} отменил оплату'.format(id_to_nick[self.id])
                bot.editMessageText(transaction_msgs[transaction_hash][user_id],
                                    msg, reply_markup=None)
            del transaction_msgs[transaction_hash]

    def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        print(id_to_nick[from_id], query_data)
        transaction_hash = query_data[2:]
        if query_data[0] == 'y':
            transaction = deligator.accept_transaction(from_id, transaction_hash)
            bot.answerCallbackQuery(query_id, text='You accept it!')
            bot.editMessageText(transaction_msgs[transaction_hash][self.id],
                                'Ожидаем подтверждения от других получателей', reply_markup=None)
            if transaction is not None:
                self._close_transaction(transaction, True)
        elif query_data[0] == 'n':
            transaction = deligator.decline_transaction(from_id, query_data[2:])
            bot.answerCallbackQuery(query_id, text='You decline it!')
            bot.editMessageText(transaction_msgs[transaction_hash][self.id],
                                'Ожидаем подтверждения от других получателей', reply_markup=None)
            self._close_transaction(transaction, False)
        elif query_data[0] == 'Y':
            transaction = deligator.decline_transaction(from_id, query_data[2:])
            bot.answerCallbackQuery(query_id, text='You decline it!')
            bot.editMessageText(self._decline_msg_id, 'Вы отменили оплату', reply_markup=None)
            self._close_transaction(transaction, False)
            self._start_transaction()
            pass
        elif query_data[0] == 'N':
            bot.answerCallbackQuery(query_id, text='Ok, waiting!')
            bot.editMessageText(self._decline_msg_id, 'Подождем', reply_markup=None)
        else:
            pass

    def on__idle(self, event):
        self.close()

    def on_close(self, ex):
        # Save to database
        propose_records[self.id] = (self._amount, self._to_ids, self._decline_msg_id)


bot = telepot.DelegatorBot(TOKEN, [
    include_callback_query_chat_id(
        pave_event_space())(
        per_chat_id(types=['private']), create_open, DebtBot, timeout=10),
])
MessageLoop(bot).run_as_thread()
print('Listening ...')

while 1:
    time.sleep(10)
