class OrchestratorError(Exception):
    """Base orchestrator error."""


class RequiredStepFailed(OrchestratorError):
    """Raised when a required step fails and execution must halt."""

    def __init__(self, step_id: str, message: str | None = None) -> None:
        self.step_id = step_id
        super().__init__(message or f"Required step failed: {step_id}")
