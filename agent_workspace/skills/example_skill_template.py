"""Example deterministic calculator skill.

This file demonstrates the LAS tool reflection contract:

1. Define a Pydantic BaseModel for arguments.
2. Expose a public function whose first parameter uses that model.
3. Return a plain text result or an `Error:` string.
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
