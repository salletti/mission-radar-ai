from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Domain.Entity.raw_post import RawPost

_SYSTEM_INSTRUCTIONS = """\
Tu es un extracteur JSON expert de posts LinkedIn de recrutement.

Réponds UNIQUEMENT avec un objet JSON valide — pas de markdown, pas de blocs de code, pas de texte avant ou après.
Utilise null pour tout champ absent ou indéterminable. Ne jamais inventer d'information.

JSON schema attendu :
{
  "is_job_offer": <boolean — true UNIQUEMENT si l'auteur du post propose une mission à pourvoir à un tiers, false si l'auteur cherche une mission pour lui-même>,
  "title": "<string | null — intitulé du poste ou de la mission>",
  "company": "<string | null — nom de l'entreprise ou du client final>",
  "location": "<string | null — ville ou région>",
  "contract_type": "<string | null — ex : freelance, CDI, CDD, stage>",
  "summary": "<string — résumé concis en 1-2 phrases : rôle principal et contexte>",
  "required_skills": ["<string>", "..."],
  "nice_to_have_skills": ["<string>", "..."],
  "seniority": "<string | null — ex : junior, confirmé, senior, lead>",
  "remote_policy": "<string | null — ex : full remote, hybride, présentiel>",
  "daily_rate": "<string | null — TJM ou salaire mentionné, ex : 650€/j>"
}

Règles :
- is_job_offer : true uniquement si l'auteur est un recruteur, un client ou un cabinet qui PROPOSE une mission/un poste à un tiers
- is_job_offer : false si l'auteur est un freelance/développeur qui CHERCHE une mission, ANNONCE sa disponibilité, ou fait la promotion de ses propres services
- required_skills : compétences explicitement requises ou obligatoires uniquement
- nice_to_have_skills : compétences souhaitées, un plus, ou optionnelles uniquement
- summary : 1-2 phrases maximum, centrées sur le rôle et le contexte principal
- Ne jamais remplir un champ avec une valeur inventée ou déduite par extrapolation\

Exemples de distinction is_job_offer :
- "Je suis disponible pour ma prochaine mission freelance à partir de septembre." → false (le freelance cherche)
- "Open to work : dev Python senior, 5 ans d'XP, dispo immédiatement." → false (le freelance cherche)
- "Nous recherchons pour notre client un développeur freelance Python/FastAPI." → true (le recruteur propose)\
"""


def build_analyze_post_prompt(raw_post: RawPost) -> str:
    """Build the complete LLM prompt for LinkedIn post analysis.

    Combines static extraction instructions with the full RawPost content.
    Pure function — deterministic, no I/O.
    """
    return (
        f"{_SYSTEM_INSTRUCTIONS}\n\n"
        "---\n\n"
        "Post LinkedIn à analyser :\n\n"
        f"Auteur : {raw_post.author_name}\n"
        f"Date de publication : {raw_post.published_at.isoformat()}\n"
        f"URL : {raw_post.post_url}\n\n"
        f"Contenu :\n{raw_post.content}"
    )
