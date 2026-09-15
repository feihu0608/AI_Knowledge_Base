from pydantic import BaseModel, Field


class QuestionPlan(BaseModel):
    use_local: bool = True
    use_mcp: bool = True
    use_general: bool = True
    rewritten_query: str = Field(min_length=1, max_length=1000)


class AnswerDraft(BaseModel):
    answer: str = Field(min_length=1)
    citation_ids: list[str] = Field(default_factory=list)
