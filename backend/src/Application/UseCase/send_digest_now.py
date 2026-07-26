from datetime import datetime, timezone
from uuid import UUID

from src.Application.DTO.send_digest_now_result import SendDigestNowResult
from src.Application.Gateway.email_template_renderer_gateway import EmailTemplateRendererGateway
from src.Application.Gateway.mailer_gateway import MailerGateway
from src.Application.UseCase.digest_assembler import DigestAssembler
from src.Domain.Entity.digest_history import DigestHistory, DigestStatus
from src.Domain.Repository.digest_history_repository import DigestHistoryRepository


class SendDigestNow:
    """Sends the current user's daily digest email on demand, independent of the
    automatic pipeline cadence and DigestPolicy — an explicit user request already
    is the consent DigestPolicy exists to gate on automatic (scheduler/system)
    triggers, so it is never consulted here.

    Depends on DigestAssembler (a shared helper, not a Use Case) plus the Mailer/
    Renderer Gateways directly — mirrors SendDigest's render→send steps inline
    rather than injecting it, since a Use Case must never depend on another Use Case.
    Records a DigestHistory entry with pipeline_run_id=None, since this send is not
    tied to any PipelineRun.
    """

    def __init__(
        self,
        digest_assembler: DigestAssembler,
        renderer: EmailTemplateRendererGateway,
        mailer: MailerGateway,
        digest_history_repository: DigestHistoryRepository,
    ) -> None:
        self._digest_assembler = digest_assembler
        self._renderer = renderer
        self._mailer = mailer
        self._digest_history_repository = digest_history_repository

    async def execute(self, user_id: UUID) -> SendDigestNowResult:
        digest = await self._digest_assembler.assemble(user_id)

        status = DigestStatus.SENT
        provider_message_id: str | None = None
        error_message: str | None = None
        try:
            html = await self._renderer.render(digest)
            provider_message_id = await self._mailer.send(to=digest.user_email, subject=digest.subject, html=html)
        except Exception as exc:
            status = DigestStatus.FAILED
            error_message = str(exc)

        missions_count = digest.mission_count if status == DigestStatus.SENT else 0

        await self._digest_history_repository.save(
            DigestHistory(
                user_id=user_id,
                pipeline_run_id=None,
                sent_at=datetime.now(timezone.utc),
                status=status,
                missions_count=missions_count,
                provider_message_id=provider_message_id,
                error_message=error_message,
            )
        )

        return SendDigestNowResult(
            status=status.value,
            missions_count=missions_count,
            provider_message_id=provider_message_id,
            error_message=error_message,
        )
