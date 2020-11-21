import secrets


def ticket_unique() -> str:
    return secrets.token_hex(16)
