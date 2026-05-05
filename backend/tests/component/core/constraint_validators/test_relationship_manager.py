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
async def generic_peer_schema(db: InfrahubDatabase, default_branch: Branch) -> SchemaRoot:
    SCHEMA = {
        "generics": [
            {
                "name": "IPAddress",
                "namespace": "Test",
                "attributes": [
                    {"name": "address", "kind": "Text"},
                ],
            }
        ],
        "nodes": [
            {
                "name": "UnicastAddress",
                "namespace": "Test",
                "inherit_from": ["TestIPAddress"],
                "relationships": [
                    {
                        "name": "interface",
                        "peer": "TestInterface",
                        "identifier": "iface__ip",
                        "cardinality": "one",
                        "direction": "inbound",
                        "optional": True,
                    }
                ],
            },
            {
                "name": "AnycastAddress",
                "namespace": "Test",
                "inherit_from": ["TestIPAddress"],
                "relationships": [
                    {
                        "name": "interfaces",
                        "peer": "TestInterface",
                        "identifier": "iface__ip",
                        "cardinality": "many",
                        "direction": "inbound",
                        "optional": True,
                    }
                ],
            },
            {
                "name": "Interface",
                "namespace": "Test",
                "attributes": [
                    {"name": "name", "kind": "Text"},
                ],
                "relationships": [
                    {
                        "name": "ip_address",
                        "peer": "TestIPAddress",
                        "identifier": "iface__ip",
                        "cardinality": "many",
                        "direction": "outbound",
                        "optional": True,
                    }
                ],
            },
        ],
    }
    schema = SchemaRoot(**SCHEMA)
    registry.schema.register_schema(schema=schema, branch=default_branch.name)
    return schema


async def test_cardinality_one_enforced_when_peer_is_generic(
    db: InfrahubDatabase, default_branch: Branch, generic_peer_schema: SchemaRoot
) -> None:
    unicast_schema = registry.schema.get(name="TestUnicastAddress")
    target = await Node.init(db=db, schema=unicast_schema)
    await target.new(db=db, address="192.0.2.1")
    await target.save(db=db)

    interface_schema = registry.schema.get(name="TestInterface")
    iface1 = await Node.init(db=db, schema=interface_schema)
    await iface1.new(db=db, name="eth0", ip_address=[target.id])
    await iface1.save(db=db)

    iface2 = await Node.init(db=db, schema=interface_schema)
    await iface2.new(db=db, name="eth1", ip_address=[target.id])

    constraint = RelationshipCountConstraint(db=db, branch=default_branch)
    with pytest.raises(ValidationError, match=r"maximum of 1 allowed"):
        await constraint.check(relm=iface2.ip_address, node_schema=iface2.get_schema(), node=iface2)
