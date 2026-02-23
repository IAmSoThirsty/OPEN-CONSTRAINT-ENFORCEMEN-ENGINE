"""
Invariant Compiler: Parses and validates policy condition expressions.
"""
import re
from typing import Any, Dict, Set
from dataclasses import dataclass


@dataclass
class CompiledCondition:
    """Represents a compiled invariant condition."""
    expression: str
    variables: Set[str]


class InvariantCompiler:
    """Compiles and validates invariant conditions."""

    SAFE_OPERATORS = {'<=', '>=', '==', '!=', '<', '>', 'and', 'or', 'not', '+', '-', '*', '/', '%'}
    MAX_EXPRESSION_LENGTH = 1000
    MAX_EVALUATION_DEPTH = 100

    def __init__(self):
        self.compiled_cache: Dict[str, CompiledCondition] = {}

    def compile(self, condition: str) -> CompiledCondition:
        """Compile and validate a condition expression."""
        if condition in self.compiled_cache:
            return self.compiled_cache[condition]

        if len(condition) > self.MAX_EXPRESSION_LENGTH:
            raise ValueError(f"Condition exceeds maximum length of {self.MAX_EXPRESSION_LENGTH}")

        self._validate_syntax(condition)

        variables = self._extract_variables(condition)

        compiled = CompiledCondition(
            expression=condition,
            variables=variables
        )

        self.compiled_cache[condition] = compiled
        return compiled

    def _validate_syntax(self, condition: str) -> None:
        """Validate the syntax of a condition expression."""
        dangerous_patterns = [
            r'__\w+__',
            r'import\s',
            r'exec\s*\(',
            r'eval\s*\(',
            r'open\s*\(',
            r'compile\s*\(',
            r'\bwhile\b',
            r'\bfor\b',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, condition):
                raise ValueError(f"Invalid or unsafe pattern in condition: {pattern}")

        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.<>=!&|() +-*/%')
        if not all(c in allowed_chars for c in condition):
            raise ValueError("Condition contains invalid characters")

    def _extract_variables(self, condition: str) -> Set[str]:
        """Extract variable references from a condition."""
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\b'
        matches = re.findall(pattern, condition)

        variables = set()
        keywords = {'and', 'or', 'not', 'True', 'False', 'None'}

        for match in matches:
            if match not in keywords and not match.isdigit():
                variables.add(match)

        return variables

    def evaluate(self, compiled: CompiledCondition, context: Dict[str, Any],
                 depth: int = 0) -> bool:
        """Safely evaluate a compiled condition against a context."""
        if depth > self.MAX_EVALUATION_DEPTH:
            raise RuntimeError("Maximum evaluation depth exceeded - possible infinite loop")

        namespace, safe_expression = self._build_namespace(context, compiled)

        try:
            result = eval(safe_expression, {"__builtins__": {}}, namespace)
            return bool(result)
        except Exception as e:
            raise RuntimeError(f"Condition evaluation failed: {str(e)}")

    def _build_namespace(self, context: Dict[str, Any], compiled: CompiledCondition) -> tuple:
        """Build a safe namespace for evaluation."""
        namespace = {}
        variables = compiled.variables

        for var in variables:
            parts = var.split('.')
            value = context

            try:
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = getattr(value, part, None)

                    if value is None:
                        raise KeyError(f"Missing context binding: {var}")

                namespace[var.replace('.', '_')] = value

            except (KeyError, AttributeError, TypeError):
                raise KeyError(f"Missing context binding: {var}")

        safe_expression = compiled.expression
        for var in sorted(variables, key=len, reverse=True):
            safe_expression = safe_expression.replace(var, var.replace('.', '_'))

        return namespace, safe_expression
