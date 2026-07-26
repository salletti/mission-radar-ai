class ApifyError(Exception):
    """Erreur de base pour les appels Apify."""


class ApifyTokenMissingError(ApifyError):
    """Token Apify absent ou vide."""


class ApifyRequestError(ApifyError):
    """Erreur lors de l'appel à l'API Apify (réseau, acteur, dataset)."""
