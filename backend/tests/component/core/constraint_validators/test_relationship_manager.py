import pytest

from infrahub.core.branch import Branch
from infrahub.core.node import Node
from infrahub.core.relationship.constraints.count import RelationshipCountConstraint
from infrahub.core.schema import SchemaRoot
from infrahub.database import InfrahubDatabase
from infrahub.exceptions import ValidationError


async def test_relationship_count_constraint_enforced_for_cardinality_one_on_generic_concrete_child(
    db: InfrahubDatabase,
    default_branch: Branch,
    generic_peer_cardinality_schema: SchemaRoot,
) -> None:
    # GIVEN a unicast address (concrete child of TestGenericAddress, cardinality:one inbound from TestInterface)
    unicast_addr = await Node.init(db=db, schema="TestUnicastAddress", branch=default_branch)
    await unicast_addr.new(db=db, address="192.0.2.1/32")
    await unicast_addr.save(db=db)

    # GIVEN a first interface already saved and linked to that unicast address
    first_iface = await Node.init(db=db, schema="TestInterface", branch=default_branch)
    await first_iface.new(db=db, name="eth0", addresses=[unicast_addr.id])
    await first_iface.save(db=db)

    # WHEN a second interface is created pointing to the same unicast address
    second_iface = await Node.init(db=db, schema="TestInterface", branch=default_branch)
    await second_iface.new(db=db, name="eth1", addresses=[unicast_addr.id])

    constraint = RelationshipCountConstraint(db=db, branch=default_branch)

    # THEN the cardinality:one constraint on TestUnicastAddress.interface must be enforced,
    # even though the writing-side peer is declared as TestGenericAddress (the generic parent)
    with pytest.raises(ValidationError, match=r"maximum of 1 allowed"):
        await constraint.check(relm=second_iface.addresses, node_schema=second_iface.get_schema(), node=second_iface)


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
