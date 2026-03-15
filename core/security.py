import secrets
import string
import time

def generate_secure_token(length: int = 16) -> str:
    """Generates a highly secure cryptographic token."""
    # Uses secrets module which is cryptographically secure (unlike the random module)
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def verify_time_gap(start_time: float, min_gap_seconds: int) -> bool:
    """
    Checks if the time elapsed since start_time is at least min_gap_seconds.
    Returns True if valid (user didn't bypass), False if bypassed.
    """
    elapsed = time.time() - start_time
    return elapsed >= min_gap_seconds

def is_expired(start_time: float, max_validity_minutes: int = 10) -> bool:
    """
    Checks if the user took too long to complete the shortener link.
    """
    elapsed = time.time() - start_time
    max_seconds = max_validity_minutes * 60
    return elapsed > max_seconds