import random


def ticket_unique() -> int:
    return random.getrandbits(160)
