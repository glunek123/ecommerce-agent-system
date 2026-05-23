from typing import Any
from pathlib import Path
import json
from pydantic import BaseModel, Field


class TestCase(BaseModel):
    id: str
    category: str
    user_input: str
    expected_intent: str
    expected_tools: list[str] = Field(default_factory=list)
    expected_response_keywords: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class EvaluationDataset:
    def __init__(self, name: str = "default"):
        self.name = name
        self.test_cases: list[TestCase] = []

    def load_from_file(self, file_path: str | Path) -> None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"数据集文件不存在: {file_path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.test_cases = [TestCase(**c) for c in data.get("test_cases", [])]

    def load_default(self) -> None:
        self.test_cases = [
            TestCase(id="inv_001", category="inventory", user_input="iPhone 15有货吗？",
                     expected_intent="inventory_check", expected_tools=["inventory_check"],
                     expected_response_keywords=["库存", "iPhone"]),
            TestCase(id="ord_001", category="order", user_input="我的订单ORD123456现在什么状态？",
                     expected_intent="order_query", expected_tools=["order_query"],
                     expected_response_keywords=["订单", "状态"]),
            TestCase(id="prod_001", category="product", user_input="我想买一个蓝牙耳机",
                     expected_intent="product_search", expected_tools=["product_search"],
                     expected_response_keywords=["耳机", "商品"]),
            TestCase(id="coup_001", category="coupon", user_input="我有哪些优惠券可以用？",
                     expected_intent="coupon_query", expected_tools=["coupon_query"],
                     expected_response_keywords=["优惠券"]),
        ]

    def get_by_category(self, category: str) -> list[TestCase]:
        return [tc for tc in self.test_cases if tc.category == category]
