from src.Application.Gateway.email_template_renderer_gateway import EmailTemplateRendererGateway
from src.Application.Gateway.mailer_gateway import MailerGateway
from src.Domain.Entity.digest_email import DigestEmail


class SendDigest:
    """Renders a DigestEmail to HTML and sends it via the mailer.

    Orchestrates EmailTemplateRendererGateway → MailerGateway.
    Never instantiates Resend or Jinja2 directly.
    """

    def __init__(
        self,
        renderer: EmailTemplateRendererGateway,
        mailer: MailerGateway,
    ) -> None:
        self._renderer = renderer
        self._mailer = mailer

    async def execute(self, digest: DigestEmail) -> str | None:
        html = await self._renderer.render(digest)
        return await self._mailer.send(
            to=digest.user_email,
            subject=digest.subject,
            html=html,
        )
