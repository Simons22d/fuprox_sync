import secrets


def ticket_unique() -> int:
    return secrets.token_hex(16)
