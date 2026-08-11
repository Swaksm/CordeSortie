class BlockedError(Exception):
    """La page retournée est un challenge antibot (CAPTCHA, etc.), pas du contenu."""
