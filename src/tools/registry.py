from typing import Type
from langchain_core.tools import BaseTool

from .base import BaseEcommerceTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Type[BaseEcommerceTool]] = {}
        self._instances: dict[str, BaseTool] = {}
        self._categories: dict[str, list[str]] = {}

    def register(self, tool_class: Type[BaseEcommerceTool], category: str | None = None) -> None:
        tool_name = tool_class.__name__
        self._tools[tool_name] = tool_class
        if category:
            self._categories.setdefault(category, []).append(tool_name)

    def get_tool(self, tool_name: str, **config) -> BaseTool:
        cache_key = f"{tool_name}:{hash(frozenset(config.items()))}"
        if cache_key not in self._instances:
            if tool_name not in self._tools:
                raise ValueError(f"未注册的工具: {tool_name}")
            self._instances[cache_key] = self._tools[tool_name](**config)
        return self._instances[cache_key]

    def get_all_tools(self, **config) -> list[BaseTool]:
        return [self.get_tool(name, **config) for name in self._tools]

    def get_tools_by_category(self, category: str, **config) -> list[BaseTool]:
        return [self.get_tool(name, **config) for name in self._categories.get(category, [])]

    def list_tools(self) -> list[dict]:
        result = []
        for name, cls in self._tools.items():
            for cat, tools in self._categories.items():
                if name in tools:
                    result.append({"name": name, "description": cls.__doc__ or "", "category": cat})
        return result


tool_registry = ToolRegistry()
