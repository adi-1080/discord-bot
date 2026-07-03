from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey


def verify_discord_signature(
    body: bytes, signature: str, timestamp: str, public_key: str
) -> bool:
    if not signature or not timestamp or not public_key:
        return False
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key))
        message = timestamp.encode() + body
        verify_key.verify(message, bytes.fromhex(signature))
        return True
    except (BadSignatureError, ValueError):
        return False
