"""Compact public identifiers for consumer offer links."""

import secrets


_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # no 0/O/1/I/L
_LENGTH = 10


def generate_public_token() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_LENGTH))
