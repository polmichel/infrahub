import pytest

from infrahub.core import registry
from infrahub.core.branch import Branch
from infrahub.core.node import Node
from infrahub.core.relationship.constraints.count import RelationshipCountConstraint
from infrahub.core.schema import SchemaRoot
from infrahub.database import InfrahubDatabase
from infrahub.exceptions import ValidationError


async def test_node_validate_constraint_relationship_count_failure(
    db: InfrahubDatabase, default_branch: Branch, car_accord_main: Node, car_volt_main: Node, person_john_main: Node
) -> None:
    constraint = RelationshipCountConstraint(db=db, branch=default_branch)
    person = await Node.init(db=db, schema="TestPerson", branch=default_branch)
    await person.new(db=db, name="Alfred", height=160, cars=[car_accord_main.id])

    with pytest.raises(ValidationError) as exc:
        await constraint.check(relm=person.cars, node_schema=person.get_schema(), node=person)

    assert "has 2 peers for testcar__testperson, maximum of 1 allowed" in exc.value.message


async def test_node_validate_constraint_relationship_count_success(
    db: InfrahubDatabase, default_branch: Branch, car_accord_main: Node, car_volt_main: Node, person_john_main: Node
) -> None:
    constraint = RelationshipCountConstraint(db=db, branch=default_branch)

    await constraint.check(relm=person_john_main.cars, node_schema=person_john_main.get_schema(), node=person_john_main)


@pytest.fixture
async def ip_address_generic_schema(db: InfrahubDatabase, default_branch: Branch) -> SchemaRoot:
    """Schema where the connector's peer is a generic type whose cardinality
    constraints are defined only on concrete subclasses, not on the generic itself."""
    SCHEMA = {
        "generics": [
            {
                "name": "IPAddress",
                "namespace": "Test",
                "attributes": [
                    {"name": "address", "kind": "Text", "unique": True},
                ],
            },
        ],
        "nodes": [
            {
                "name": "UnicastIPAddress",
                "namespace": "Test",
                "inherit_from": ["TestIPAddress"],
                "relationships": [
                    {
                        "name": "interface",
                        "peer": "TestLayer3",
                        "identifier": "ip__l3interface",
                        "cardinality": "one",
                        "direction": "inbound",
                        "optional": True,
                    },
                ],
            },
            {
                "name": "AnycastIPAddress",
                "namespace": "Test",
                "inherit_from": ["TestIPAddress"],
                "relationships": [
                    {
                        "name": "interface",
                        "peer": "TestLayer3",
                        "identifier": "ip__l3interface",
                        "cardinality": "many",
                        "direction": "inbound",
                        "optional": True,
                    },
                ],
            },
            {
                "name": "Layer3",
                "namespace": "Test",
                "attributes": [
                    {"name": "name", "kind": "Text", "unique": True},
                ],
                "relationships": [
                    {
                        "name": "ip_addresses",
                        "peer": "TestIPAddress",
                        "identifier": "ip__l3interface",
                        "cardinality": "many",
                        "direction": "outbound",
                        "optional": True,
                    },
                ],
            },
        ],
    }
    schema = SchemaRoot(**SCHEMA)
    registry.schema.register_schema(schema=schema, branch=default_branch.name)
    return schema


async def test_cardinality_one_enforced_when_peer_is_generic(
    db: InfrahubDatabase,
    default_branch: Branch,
    ip_address_generic_schema: SchemaRoot,
) -> None:
    unicast = await Node.init(db=db, schema="TestUnicastIPAddress", branch=default_branch)
    await unicast.new(db=db, address="192.168.0.1")
    await unicast.save(db=db)

    layer3_first = await Node.init(db=db, schema="TestLayer3", branch=default_branch)
    await layer3_first.new(db=db, name="eth0", ip_addresses=[unicast.id])
    await layer3_first.save(db=db)

    constraint = RelationshipCountConstraint(db=db, branch=default_branch)
    layer3_second = await Node.init(db=db, schema="TestLayer3", branch=default_branch)
    await layer3_second.new(db=db, name="eth1", ip_addresses=[unicast.id])

    with pytest.raises(ValidationError):
        await constraint.check(
            relm=layer3_second.ip_addresses,
            node_schema=layer3_second.get_schema(),
            node=layer3_second,
        )


async def test_cardinality_many_allowed_when_peer_is_generic(
    db: InfrahubDatabase,
    default_branch: Branch,
    ip_address_generic_schema: SchemaRoot,
) -> None:
    anycast = await Node.init(db=db, schema="TestAnycastIPAddress", branch=default_branch)
    await anycast.new(db=db, address="224.0.0.1")
    await anycast.save(db=db)

    layer3_first = await Node.init(db=db, schema="TestLayer3", branch=default_branch)
    await layer3_first.new(db=db, name="eth0", ip_addresses=[anycast.id])
    await layer3_first.save(db=db)

    constraint = RelationshipCountConstraint(db=db, branch=default_branch)
    layer3_second = await Node.init(db=db, schema="TestLayer3", branch=default_branch)
    await layer3_second.new(db=db, name="eth1", ip_addresses=[anycast.id])

    await constraint.check(
        relm=layer3_second.ip_addresses,
        node_schema=layer3_second.get_schema(),
        node=layer3_second,
    )
