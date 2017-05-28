import json
import os


class DataBase(object):
    def __init__(self, user_ids, file_name):
        self.file_name = file_name
        self.pattern = '{}:{}'
        if not os.path.isfile(file_name):
            self.data = {self.pattern.format(first_id, second_id): 0 for first_id in user_ids for second_id in user_ids
                         if first_id < second_id}
            self.save_dump()
        else:
            with open(file_name) as infile:
                self.data = json.load(infile)
            for p in self.data.keys():
                self.data[p] = int(self.data[p])

    def save_dump(self):
        with open(self.file_name, 'w') as outfile:
            json.dump(self.data, outfile)

    def get_debt(self, from_id, to_id):
        if from_id < to_id:
            return self.data[self.pattern.format(from_id, to_id)]
        else:
            return -self.data[self.pattern.format(to_id, from_id)]

    def add_to_debt(self, from_id, to_id, how_much):
        if from_id < to_id:
            self.data[self.pattern.format(from_id, to_id)] += how_much
        else:
            self.data[self.pattern.format(to_id, from_id)] -= how_much
        self.save_dump()
