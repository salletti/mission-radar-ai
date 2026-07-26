from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.ValueObject.pipeline_enums import PipelineStatus, PipelineStep, PipelineTrigger, PipelineType, StepOutcome
from src.Infrastructure.Persistence.SQLAlchemy.Models.pipeline_run_model import PipelineRunModel


class PipelineRunMapper:
    @staticmethod
    def to_domain(model: PipelineRunModel) -> PipelineRun:
        return PipelineRun(
            id=model.id,
            user_id=model.user_id,
            pipeline_type=PipelineType(model.pipeline_type),
            trigger_type=PipelineTrigger(model.trigger_type),
            status=PipelineStatus(model.status),
            current_step=PipelineStep(model.current_step),
            progress=model.progress,
            started_at=model.started_at,
            finished_at=model.finished_at,
            error_message=model.error_message,
            step_outcomes={
                PipelineStep(k): StepOutcome(v)
                for k, v in (model.step_outcomes or {}).items()
            },
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(run: PipelineRun) -> PipelineRunModel:
        return PipelineRunModel(
            id=run.id,
            user_id=run.user_id,
            pipeline_type=run.pipeline_type.value,
            trigger_type=run.trigger_type.value,
            status=run.status.value,
            current_step=run.current_step.value,
            progress=run.progress,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error_message=run.error_message,
            step_outcomes={s.value: o.value for s, o in run.step_outcomes.items()},
            created_at=run.created_at,
        )
