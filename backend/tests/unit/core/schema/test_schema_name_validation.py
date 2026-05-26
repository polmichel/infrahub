import pytest
from pydantic import ValidationError

from infrahub.core.constants import RelationshipCardinality, RelationshipKind
from infrahub.core.schema import AttributeSchema, RelationshipSchema


class TestSchemaElementNamesRejectConsecutiveUnderscores:
    """``__`` is reserved as a path separator (e.g. ``name__value``).

    Attribute and relationship names must therefore not contain consecutive
    underscores. Relationship identifiers are explicitly excluded from this
    rule because they legitimately encode two kinds joined by ``__`` (e.g.
    ``testcar__testperson``).
    """

    def test_attribute_schema_name_rejects_double_underscore(self) -> None:
        with pytest.raises(ValidationError, match=r"name"):
            AttributeSchema(name="name__asc", kind="Text")

    def test_relationship_schema_name_rejects_double_underscore(self) -> None:
        with pytest.raises(ValidationError, match=r"name"):
            RelationshipSchema(
                name="peer__alt",
                peer="TestPerson",
                kind=RelationshipKind.ATTRIBUTE,
                cardinality=RelationshipCardinality.ONE,
            )

    def test_relationship_schema_identifier_allows_double_underscore(self) -> None:
        """Identifiers join two kinds with ``__`` and must keep accepting that form."""
        relationship = RelationshipSchema(
            name="owner",
            peer="TestPerson",
            kind=RelationshipKind.ATTRIBUTE,
            cardinality=RelationshipCardinality.ONE,
            identifier="testcar__testperson",
        )
        assert relationship.identifier == "testcar__testperson"
