import re

def is_valid_email(email: str) -> bool:
    """Validates an email address format."""
    pattern = r"^[a-zA-Z0-zA-Z0-9\._%+\-]+@[a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def is_valid_phone(phone: str) -> bool:
    """Validates a professional phone number."""
    # This is a very permissive regex just to ensure it looks roughly phone-like
    pattern = r"^\+?[0-9\-\s\(\)]{7,20}$"
    return bool(re.match(pattern, phone)) or not phone.strip()

def is_valid_url(url: str) -> bool:
    """Validates an HTTP/HTTPS URL."""
    pattern = r"^(https?:\/\/)?([\da-z\.\-]+)\.([a-z\.]{2,6})([\/\w \.\-]*)*\/?$"
    return bool(re.match(pattern, url)) or not url.strip()
