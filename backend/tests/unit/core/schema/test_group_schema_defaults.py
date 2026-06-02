import dataclasses

import pytest

from infrahub.core.constants import InfrahubKind
from infrahub.core.schema import SchemaRoot, core_models
from infrahub.core.schema.schema_branch import SchemaBranch


@dataclasses.dataclass
class GroupTypeDefaultCase:
    name: str
    kind: str
    expected_group_type: str


# System-managed group kinds must not be selectable as candidate groups in the UI.
# The selectors filter candidates to group_type == "default", so these kinds must
# default to "internal" to be excluded.
INTERNAL_SYSTEM_GROUP_CASES = [
    GroupTypeDefaultCase(name="account_group", kind=InfrahubKind.ACCOUNTGROUP, expected_group_type="internal"),
    GroupTypeDefaultCase(name="generator_group", kind=InfrahubKind.GENERATORGROUP, expected_group_type="internal"),
    GroupTypeDefaultCase(
        name="generator_aware_group", kind=InfrahubKind.GENERATORAWAREGROUP, expected_group_type="internal"
    ),
    GroupTypeDefaultCase(name="repository_group", kind=InfrahubKind.REPOSITORYGROUP, expected_group_type="internal"),
]


@pytest.fixture(scope="module")
def processed_core_schema() -> SchemaBranch:
    schema_branch = SchemaBranch(cache={}, name="test")
    schema_branch.load_schema(schema=SchemaRoot(**core_models))
    schema_branch.process()
    return schema_branch


@pytest.mark.parametrize("case", INTERNAL_SYSTEM_GROUP_CASES, ids=lambda case: case.name)
def test_system_group_kinds_default_to_internal(
    processed_core_schema: SchemaBranch, case: GroupTypeDefaultCase
) -> None:
    node_schema = processed_core_schema.get(name=case.kind, duplicate=False)
    group_type_attr = node_schema.get_attribute(name="group_type")
    assert group_type_attr.default_value == case.expected_group_type


def test_standard_group_remains_default(processed_core_schema: SchemaBranch) -> None:
    node_schema = processed_core_schema.get(name=InfrahubKind.STANDARDGROUP, duplicate=False)
    group_type_attr = node_schema.get_attribute(name="group_type")
    assert group_type_attr.default_value == "default"
