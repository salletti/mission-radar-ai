from src.Application.DTO.cv_profile_draft import CVProfileDraft
from src.Application.DTO.process_cv_command import ProcessCVCommand
from src.Application.Gateway.cv_extractor_gateway import CVExtractorGateway
from src.Application.Gateway.llm_gateway import LLMGateway


class ProcessCV:
    """Extracts a structured profile draft from a CV file.

    Does not persist — the caller is responsible for confirmation and storage (Phase 2.4).
    """

    def __init__(self, cv_extractor: CVExtractorGateway, llm: LLMGateway) -> None:
        self._cv_extractor = cv_extractor
        self._llm = llm

    async def execute(self, command: ProcessCVCommand) -> CVProfileDraft:
        cv_text = await self._cv_extractor.extract_text(command.file_path)
        profile_dto = await self._llm.extract_profile_from_cv(cv_text)
        return CVProfileDraft(profile=profile_dto, cv_raw_text=cv_text)
