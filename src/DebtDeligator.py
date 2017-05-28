from DataBase import DataBase
import random


class DebtDeligator(object):
    def __init__(self, user_ids):
        self.user_ids = user_ids
        self.want_to_pay = {user_id: -1 for user_id in user_ids}
        self.data = DataBase(user_ids, 'data.json')
        self.transactions = {}

    def set_amount(self, from_user, how_much):
        self.want_to_pay[from_user] = how_much

    def is_amount_set(self, from_user):
        return self.want_to_pay[from_user] > 0

    def add_transaction(self, from_user, to_user):
        if self.want_to_pay[from_user] == -1:
            return False
        transaction_hash = '%032x' % random.getrandbits(128)
        if to_user == 0:
            self.transactions[transaction_hash] = {
                'amount': (self.want_to_pay[from_user] + len(self.user_ids) - 1) // len(self.user_ids),
                'from': from_user,
                'to': [user_id for user_id in self.user_ids if user_id != from_user],
                'mask': [0] * (len(self.user_ids) - 1)
            }
        else:
            self.transactions[transaction_hash] = {'amount': self.want_to_pay[from_user],
                                                   'from': from_user,
                                                   'to': [to_user],
                                                   'mask': [0]}
        self.want_to_pay[from_user] = -1;
        return transaction_hash, self.transactions[transaction_hash]

    def accept_transaction(self, user_id, transaction_hash):
        if transaction_hash not in self.transactions.keys():
            return False
        pos = self.transactions[transaction_hash]['to'].index(user_id)
        assert pos != -1, 'Not in tra'
        self.transactions[transaction_hash]['mask'][pos] = 1
        if sum(self.transactions[transaction_hash]['mask']) == len(self.transactions[transaction_hash]['mask']):
            self.transact(self.transactions[transaction_hash])
            return self.transactions.pop(transaction_hash)

    def decline_transaction(self, user_id, transaction_hash):
        if transaction_hash not in self.transactions.keys():
            return False
        pos = self.transactions[transaction_hash]['to'].index(user_id)
        assert pos != -1, 'Not in tra'
        return self.transactions.pop(transaction_hash)

    def transact(self, transaction):
        for user_id in transaction['to']:
            self.data.add_to_debt(transaction['from'], user_id, transaction['amount'])

    def get_debt(self, user_id):
        return {to_id: self.data.get_debt(user_id, to_id) for to_id in self.user_ids if to_id != user_id}
