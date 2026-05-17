# Skill Contract: calculate

## Runtime Mapping

- Module: `agent_workspace/skills/example_skill_template.py`
- Function: `calculate`
- Argument model: `CalculatorArgs`

## Purpose

Perform basic arithmetic for add, subtract, multiply, and divide operations.

## Input

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `operation` | string | yes | One of `add`, `subtract`, `multiply`, `divide` |
| `a` | number | yes | First operand |
| `b` | number | yes | Second operand |

## Output

Plain text result or an error string.

## Safety Notes

- Division by zero returns an error string.
- This skill is deterministic and does not access external systems.

## 中文說明

`calculate` 是基本四則運算工具。它不存取外部系統，屬於低風險 deterministic
skill。
