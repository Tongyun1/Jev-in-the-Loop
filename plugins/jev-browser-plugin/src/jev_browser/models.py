from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class TextValue(StrictModel):
    id: Annotated[str, Field(min_length=1, max_length=64)]
    field: Annotated[str, Field(min_length=1, max_length=300)]
    value: Annotated[str, Field(min_length=1, max_length=1000)]

    @field_validator("id", "field", "value")
    @classmethod
    def nonblank(cls, value: str):
        if not value.strip():
            raise ValueError("value must be nonblank")
        return value


class Condition(StrictModel):
    source: Literal["text", "url", "title", "value", "checked", "selected", "action"]
    expected: Annotated[str, Field(min_length=1, max_length=1000)]
    label: Annotated[str, Field(max_length=300)] = ""
    match: Literal["exact", "contains", "line"] = "exact"

    @model_validator(mode="after")
    def require_label(self):
        if self.source in {"value", "checked", "selected"} and not self.label.strip():
            raise ValueError("control conditions require an exact accessible label")
        if not self.expected.strip():
            raise ValueError("condition must be nonblank")
        if self.match == "line" and self.source != "text":
            raise ValueError("line matching is only supported for page text")
        return self


def require_completion_evidence(conditions):
    """Substring text and action history alone cannot certify task completion."""
    if conditions and not any(
        c.source != "action" and not (c.source in {"text", "title"} and c.match == "contains")
        for c in conditions
    ):
        raise ValueError(
            "completion requires URL/control evidence or exact/line text; "
            "text/title substrings and action history alone are insufficient"
        )


class Transition(StrictModel):
    after_label: Annotated[str, Field(min_length=1, max_length=300)]
    require_before: Annotated[list[Condition], Field(max_length=20)] = []
    until: Annotated[list[Condition], Field(min_length=1, max_length=20)]
    timeout_ms: Annotated[int, Field(ge=100, le=10000)] = 3000


class Stage(StrictModel):
    goal: Annotated[str, Field(min_length=1, max_length=2000)]
    complete_when: Annotated[list[Condition], Field(min_length=1, max_length=20)]
    transitions: Annotated[list[Transition], Field(max_length=20)] = []

    @model_validator(mode="after")
    def unique_transitions(self):
        require_completion_evidence(self.complete_when)
        labels = [t.after_label for t in self.transitions]
        if len(labels) != len(set(labels)):
            raise ValueError("transition labels must be unique within a stage")
        return self


class ResumeRequest(StrictModel):
    session_id: str
    text_values: Annotated[list[TextValue], Field(max_length=20)] = []
    max_steps: Annotated[int, Field(ge=1, le=60)] = 40


class Viewport(StrictModel):
    width: Annotated[int, Field(ge=320, le=3840)]
    height: Annotated[int, Field(ge=240, le=2160)]


class RunRequest(StrictModel):
    url: AnyHttpUrl
    goal: Annotated[str, Field(min_length=1, max_length=4000)]
    text_values: Annotated[list[TextValue], Field(max_length=20)] = []
    allowed_domains: Annotated[list[str], Field(max_length=20)] = []
    stop_before: Annotated[list[str], Field(max_length=30)] = []
    max_steps: Annotated[int, Field(ge=1, le=60)] = 40
    visible: bool = True
    keep_open: bool = False
    viewport: Viewport | None = None
    stages: Annotated[list[Stage], Field(max_length=20)] = []
    success_when: Annotated[list[Condition], Field(max_length=20)] = []
    stop_when: Annotated[list[Condition], Field(max_length=20)] = []

    @field_validator("goal")
    @classmethod
    def goal_nonblank(cls, value: str):
        if not value.strip():
            raise ValueError("goal must be nonblank")
        return value

    @field_validator("allowed_domains")
    @classmethod
    def normalize_domains(cls, values: list[str]):
        normalized = []
        for value in values:
            domain = value.strip().lower().rstrip(".")
            if not domain or "/" in domain or ":" in domain:
                raise ValueError("allowed_domains must contain hostnames only")
            normalized.append(domain)
        if len(normalized) != len(set(normalized)):
            raise ValueError("allowed_domains must be unique")
        return normalized

    @field_validator("stop_before")
    @classmethod
    def normalize_stops(cls, values: list[str]):
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("stop_before entries must be nonblank")
        return normalized

    @model_validator(mode="after")
    def unique_text_ids(self):
        require_completion_evidence(self.success_when)
        ids = [item.id for item in self.text_values]
        if len(ids) != len(set(ids)):
            raise ValueError("text value IDs must be unique")
        return self
