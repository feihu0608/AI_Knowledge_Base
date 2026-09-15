from __future__ import annotations

from .definition import AgentDefinition, AgentResult, ModelInvoker


class AgentRunner:
    def __init__(self, invoke_model: ModelInvoker, *, provider_mode: str) -> None:
        self._invoke_model = invoke_model
        self._provider_mode = provider_mode

    def run(self, definition: AgentDefinition, input_data: dict) -> AgentResult:
        raw = self._invoke_model(definition, input_data)
        output = definition.output_schema.model_validate(raw)
        return AgentResult(
            agent_name=definition.name,
            agent_version=definition.version,
            provider_mode=self._provider_mode,
            output=output,
        )

