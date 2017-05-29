from DataBase import DataBase
import random


class DebtDeligator(object):
    def __init__(self, user_ids):
        self.user_ids = user_ids
        self.data = DataBase(user_ids, 'data.json')
        self.transactions = {}

    def add_transaction(self, from_user, to_user, how_much):
        transaction_hash = '%032x' % random.getrandbits(128)
        count = len(to_user)
        if count > 1:
            self.transactions[transaction_hash] = {'amount': (how_much + count) // (count + 1),
                                                   'from': from_user,
                                                   'to': to_user,
                                                   'mask': [0] * count,
                                                   'transaction_hash': transaction_hash, }
        else:
            self.transactions[transaction_hash] = {'amount': how_much,
                                                   'from': from_user,
                                                   'to': to_user,
                                                   'mask': [0],
                                                   'transaction_hash': transaction_hash, }
        return self.transactions[transaction_hash]

    def accept_transaction(self, user_id, transaction_hash):
        pos = self.transactions[transaction_hash]['to'].index(user_id)
        assert pos != -1, 'Not in tra'
        self.transactions[transaction_hash]['mask'][pos] = 1
        if sum(self.transactions[transaction_hash]['mask']) == len(self.transactions[transaction_hash]['mask']):
            self.transact(self.transactions[transaction_hash])
            return self.transactions.pop(transaction_hash)

    def decline_transaction(self, user_id, transaction_hash):

        assert user_id == self.transactions[transaction_hash]['from'] or \
               user_id in self.transactions[transaction_hash]['to'], 'Not in tra'
        return self.transactions.pop(transaction_hash)

    def transact(self, transaction):
        for user_id in transaction['to']:
            self.data.add_to_debt(transaction['from'], user_id, transaction['amount'])

    def get_debt(self, user_id):
        return {to_id: self.data.get_debt(user_id, to_id) for to_id in self.user_ids if to_id != user_id}
