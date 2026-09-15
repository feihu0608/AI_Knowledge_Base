from agent_harness import AgentDefinition

from .schemas import AnswerDraft, QuestionPlan


QUERY_PLANNER = AgentDefinition(
    name="QueryPlannerAgent", version="1.0.0", prompt_version="query-plan-v1",
    output_schema=QuestionPlan, max_model_calls=1,
)

ANSWER_WRITER = AgentDefinition(
    name="AnswerWriterAgent", version="1.0.0", prompt_version="answer-write-v1",
    output_schema=AnswerDraft, max_model_calls=1,
)
