import shelve
from dataclasses import dataclass

from config import DB_NAME, DEBUG

DFAULT_USER_LEVEL = 4

if DEBUG:
    storage = shelve.open(DB_NAME, writeback=True, flag='n')
else:
    storage = shelve.open(DB_NAME, writeback=True)


@dataclass
class User:
    number: str = ''
    tries: int = 0
    level: int = DFAULT_USER_LEVEL
    mode: str = '' # 'bot', 'user', 'duel'
    history: tuple = ()
    user_history: tuple = ()
    next_turn: bool = True

    def reset(self, new_number = ''):
        self.number = new_number
        self.tries = 0
        self.history = ()
        self.user_history = ()
        self.next_turn = True


def get_or_create_user(id):
    return storage.get(str(id), User())

def save_user(id, user):
    storage[str(id)] = user

def del_user(id):
    id = str(id)
    if id in storage:
        del storage[id]