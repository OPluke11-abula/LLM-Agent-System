"""
=========================================================================
 skills/example_skill_template.py — 範例技能 (同時也是可執行的測試工具)

 此檔案有兩個用途：
   1. 作為未來 AI 建立新技能時的格式範本
   2. 作為閉環測試時的真實可呼叫工具

[觸發時機] (Trigger Condition)
- 當使用者要求進行數學計算時。
- When the user asks for a mathematical calculation.

[限制條件] (Constraints)
- 僅支援基本四則運算 (加減乘除)。
- 不支援複雜的數學表達式或符號運算。
- Only supports basic arithmetic: add, subtract, multiply, divide.
=========================================================================
"""

from pydantic import BaseModel, Field


class CalculatorArgs(BaseModel):
    """Arguments for the calculator skill."""

    operation: str = Field(
        ...,
        description="The arithmetic operation to perform. Must be one of: add, subtract, multiply, divide.",
    )
    a: float = Field(..., description="The first number.")
    b: float = Field(..., description="The second number.")


def calculate(args: CalculatorArgs) -> str:
    """
    Perform a basic arithmetic calculation.
    Supports: add, subtract, multiply, divide.
    """
    op = args.operation.lower().strip()

    if op == "add":
        result = args.a + args.b
    elif op == "subtract":
        result = args.a - args.b
    elif op == "multiply":
        result = args.a * args.b
    elif op == "divide":
        if args.b == 0:
            return "Error: Division by zero is not allowed."
        result = args.a / args.b
    else:
        return f"Error: Unknown operation '{op}'. Supported: add, subtract, multiply, divide."

    return f"{args.a} {op} {args.b} = {result}"
