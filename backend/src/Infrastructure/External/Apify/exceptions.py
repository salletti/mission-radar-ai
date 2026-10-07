class ApifyError(Exception):
    """Erreur de base pour les appels Apify."""


class ApifyTokenMissingError(ApifyError):
    """Token Apify absent ou vide."""


class ApifyRequestError(ApifyError):
    """Erreur lors de l'appel à l'API Apify (réseau, acteur, dataset)."""


class ApifyQuotaExceededError(ApifyRequestError):
    """Compte Apify à court de quota (limite mensuelle atteinte ou rate limit persistant) —
    un autre compte peut prendre le relais, contrairement à une erreur d'acteur ou de réseau."""
