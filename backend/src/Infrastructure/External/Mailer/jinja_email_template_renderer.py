from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.Application.Gateway.email_template_renderer_gateway import EmailTemplateRendererGateway

if TYPE_CHECKING:
    from src.Domain.Entity.digest_email import DigestEmail

_DEFAULT_TEMPLATES_DIR = Path(__file__).parent / "Templates"


class JinjaEmailTemplateRenderer(EmailTemplateRendererGateway):
    """Renders a DigestEmail to HTML using Jinja2 templates.

    Templates live in Infrastructure/External/Mailer/Templates/.
    Jinja2 rendering is synchronous — no to_thread() needed for in-process template rendering.
    """

    def __init__(self, templates_dir: Path | None = None) -> None:
        loader_dir = templates_dir if templates_dir is not None else _DEFAULT_TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(loader_dir)),
            autoescape=select_autoescape(["html", "j2"]),
        )

    async def render(self, digest: "DigestEmail") -> str:
        template = self._env.get_template("digest.html.j2")
        return template.render(digest=digest)
