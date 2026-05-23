from typing import Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..config import get_settings, PromptTemplates


class SubTask(BaseModel):
    description: str
    tool_name: str | None = None
    parameters: dict = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    priority: int = 0


class TaskPlan(BaseModel):
    original_request: str
    subtasks: list[SubTask] = Field(default_factory=list)
    reasoning: str


class TaskPlanner:
    def __init__(self, llm: ChatOpenAI | None = None):
        self.settings = get_settings()
        self.llm = llm or ChatOpenAI(
            model=self.settings.llm_model_name,
            temperature=0.1,
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url
        )

    async def plan(self, user_request: str, available_tools: list[str],
                   context: dict[str, Any] | None = None) -> TaskPlan:
        prompt = ChatPromptTemplate.from_messages([
            ("system", PromptTemplates.TASK_PLANNING),
            ("human", "{user_request}")
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke({
            "user_request": user_request,
            "available_tools": ", ".join(available_tools)
        })
        subtasks = self._parse_subtasks(response.content)
        return TaskPlan(original_request=user_request, subtasks=subtasks, reasoning=response.content)

    def _parse_subtasks(self, response: str) -> list[SubTask]:
        subtasks = []
        for i, line in enumerate(response.strip().split("\n")):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                desc = line.lstrip("0123456789.-) ")
                if desc:
                    subtasks.append(SubTask(description=desc, priority=i))
        return subtasks
