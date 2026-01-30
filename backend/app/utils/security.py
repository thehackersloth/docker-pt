"""
Security utility functions
"""

import hashlib
import hmac
import secrets
import base64
import re
from typing import Tuple, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure token"""
    return secrets.token_urlsafe(length)


def generate_api_key() -> str:
    """Generate an API key"""
    return f"pk_{secrets.token_urlsafe(32)}"


def hash_token(token: str) -> str:
    """Hash a token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """Verify a token against its hash"""
    return hmac.compare_digest(hash_token(token), token_hash)


def generate_otp(length: int = 6) -> str:
    """Generate a one-time password"""
    return ''.join(secrets.choice('0123456789') for _ in range(length))


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data, showing only last N characters"""
    if len(data) <= visible_chars:
        return '*' * len(data)
    return '*' * (len(data) - visible_chars) + data[-visible_chars:]


def mask_email(email: str) -> str:
    """Mask email address for display"""
    if '@' not in email:
        return mask_sensitive_data(email)

    local, domain = email.rsplit('@', 1)

    if len(local) <= 2:
        masked_local = '*' * len(local)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]

    return f"{masked_local}@{domain}"


def mask_ip(ip: str) -> str:
    """Mask IP address for logging"""
    parts = ip.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    return mask_sensitive_data(ip)


def sanitize_input(input_str: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    # Remove null bytes
    sanitized = input_str.replace('\x00', '')

    # Remove control characters except newline and tab
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized)

    return sanitized


def sanitize_command_arg(arg: str) -> str:
    """Sanitize argument for shell command (escape special chars)"""
    # Remove dangerous characters
    dangerous = ['|', ';', '&', '$', '`', '>', '<', '!', '(', ')', '{', '}', '[', ']']
    sanitized = arg
    for char in dangerous:
        sanitized = sanitized.replace(char, '')

    # Escape quotes
    sanitized = sanitized.replace("'", "\\'")
    sanitized = sanitized.replace('"', '\\"')

    return sanitized


def is_safe_path(path: str, base_dir: str) -> bool:
    """Check if path is safe and within base directory"""
    import os

    # Normalize paths
    base_dir = os.path.abspath(base_dir)
    full_path = os.path.abspath(os.path.join(base_dir, path))

    # Check if path is within base directory
    return full_path.startswith(base_dir + os.sep) or full_path == base_dir


def check_common_passwords(password: str) -> bool:
    """Check if password is in common passwords list"""
    common_passwords = [
        'password', '123456', '12345678', 'qwerty', 'abc123',
        'password1', '1234567890', 'letmein', 'welcome',
        'monkey', 'dragon', '111111', 'baseball', 'iloveyou',
        'trustno1', 'sunshine', 'princess', 'admin', 'password123',
        'root', 'toor', 'changeme', 'test', 'guest'
    ]
    return password.lower() in common_passwords


def calculate_password_entropy(password: str) -> float:
    """Calculate password entropy in bits"""
    import math

    charset_size = 0
    if re.search(r'[a-z]', password):
        charset_size += 26
    if re.search(r'[A-Z]', password):
        charset_size += 26
    if re.search(r'[0-9]', password):
        charset_size += 10
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        charset_size += 32
    if re.search(r'[\s]', password):
        charset_size += 1

    if charset_size == 0:
        return 0

    entropy = len(password) * math.log2(charset_size)
    return round(entropy, 2)


def rate_password_strength(password: str) -> Tuple[str, int]:
    """Rate password strength"""
    entropy = calculate_password_entropy(password)

    if entropy < 28:
        return "Very Weak", 1
    elif entropy < 36:
        return "Weak", 2
    elif entropy < 60:
        return "Moderate", 3
    elif entropy < 80:
        return "Strong", 4
    else:
        return "Very Strong", 5


def generate_secure_filename(original_name: str) -> str:
    """Generate a secure filename"""
    import os

    # Get extension
    _, ext = os.path.splitext(original_name)

    # Sanitize extension
    ext = re.sub(r'[^a-zA-Z0-9.]', '', ext)[:10]

    # Generate random filename
    random_name = secrets.token_hex(16)

    return f"{random_name}{ext}"


def encode_base64(data: bytes) -> str:
    """Encode bytes to base64 string"""
    return base64.b64encode(data).decode('utf-8')


def decode_base64(data: str) -> bytes:
    """Decode base64 string to bytes"""
    return base64.b64decode(data.encode('utf-8'))


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time"""
    return hmac.compare_digest(a.encode(), b.encode())


def generate_csrf_token() -> str:
    """Generate a CSRF token"""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    """Verify CSRF token"""
    if not token or not stored_token:
        return False
    return constant_time_compare(token, stored_token)
