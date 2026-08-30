class BlockedError(Exception):
    """La page retournée est un challenge antibot (CAPTCHA, etc.), pas du contenu."""


_MAX_ERROR_LENGTH = 200


def short_error(exc: Exception) -> str:
    """Isole la première ligne utile d'une exception pour l'affichage dans le
    salon log ou `/filtre dry-run`. Certaines erreurs Playwright ajoutent un
    bloc "Call log:" de plusieurs lignes (tentatives de retry internes) qui
    n'apporte rien à un message d'alerte et rend le salon log illisible."""
    text = str(exc).strip()
    first_line = text.splitlines()[0] if text else exc.__class__.__name__
    return first_line[:_MAX_ERROR_LENGTH]
