"""Regression test for the "internal groups appear in the add-to-group dropdown" bug.

The front-end lists candidate groups filtered by ``group_type__values: ["default"]``.
System groups such as ``CoreAccountGroup`` and ``CoreGeneratorGroup`` must therefore be
classified as ``internal`` so they are excluded; otherwise they leak into the dropdown.

See polmichel/infrahub#33 (copied from opsmill/infrahub#4872).
"""

import pytest

from infrahub.core.schema import SchemaRoot, core_models
from infrahub.core.schema.schema_branch import SchemaBranch


@pytest.fixture(scope="module")
def processed_core_schema() -> SchemaBranch:
    schema_branch = SchemaBranch(cache={}, name="test")
    schema_branch.load_schema(schema=SchemaRoot(**core_models))
    schema_branch.process_inheritance()
    return schema_branch


@pytest.mark.parametrize("kind", ["CoreAccountGroup", "CoreGeneratorGroup"])
def test_system_groups_default_to_internal(processed_core_schema: SchemaBranch, kind: str) -> None:
    """System groups must default to group_type 'internal'.

    They must be excluded from the add-to-group dropdown, which only lists group_type 'default'.
    """
    node = processed_core_schema.get(name=kind, duplicate=False)
    group_type = node.get_attribute(name="group_type")

    assert group_type.default_value == "internal", (
        f"{kind}.group_type defaults to {group_type.default_value!r}; "
        "it must be 'internal' so it is excluded from the user-facing group dropdown"
    )


def test_standard_group_stays_default(processed_core_schema: SchemaBranch) -> None:
    """Guard: the fix must be scoped to system groups.

    A user-facing StandardGroup must keep defaulting to 'default' so it still shows up as a
    selectable group.
    """
    node = processed_core_schema.get(name="CoreStandardGroup", duplicate=False)
    assert node.get_attribute(name="group_type").default_value == "default"
