from infrahub.graphql.types.attribute import AttributeInterface


def test_attribute_interface_does_not_expose_is_inherited() -> None:
    """AttributeInterface must not declare is_inherited: the runtime model removed it."""
    assert "is_inherited" not in AttributeInterface._meta.fields
