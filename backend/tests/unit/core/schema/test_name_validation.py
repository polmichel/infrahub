from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from infrahub.core.schema import AttributeSchema, RelationshipSchema


@dataclass
class NameValidationTestCase:
    name: str
    """Descriptive name for the test scenario (used as test ID)."""

    field_name: str
    """The candidate attribute or relationship name to validate."""


REJECTED_NAME_TEST_CASES: list[NameValidationTestCase] = [
    NameValidationTestCase(
        name="name_with_double_underscore_in_middle",
        field_name="name__asc",
    ),
    NameValidationTestCase(
        name="name_with_double_underscore_after_prefix",
        field_name="foo__bar",
    ),
    NameValidationTestCase(
        name="name_with_triple_underscore",
        field_name="alpha___beta",
    ),
]


@pytest.mark.parametrize(
    "test_case",
    [pytest.param(tc, id=tc.name) for tc in REJECTED_NAME_TEST_CASES],
)
def test_attribute_schema_rejects_consecutive_underscores(test_case: NameValidationTestCase) -> None:
    """AttributeSchema names cannot contain consecutive underscores because `__` is reserved as the schema path separator."""
    with pytest.raises(ValidationError, match=r"name"):
        AttributeSchema(name=test_case.field_name, kind="Text")


@pytest.mark.parametrize(
    "test_case",
    [pytest.param(tc, id=tc.name) for tc in REJECTED_NAME_TEST_CASES],
)
def test_relationship_schema_rejects_consecutive_underscores(test_case: NameValidationTestCase) -> None:
    """RelationshipSchema names cannot contain consecutive underscores because `__` is reserved as the schema path separator."""
    with pytest.raises(ValidationError, match=r"name"):
        RelationshipSchema(name=test_case.field_name, peer="TestPerson")
