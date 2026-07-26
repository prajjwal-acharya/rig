from __future__ import annotations

import dataclasses

import pytest

from rig.graph.properties import Properties


def test_of_builds_from_keyword_arguments() -> None:
    properties = Properties.of(name="Foo", is_exported=True, count=3)

    assert properties["name"] == "Foo"
    assert properties["is_exported"] is True
    assert properties["count"] == 3


def test_from_mapping_builds_from_dict() -> None:
    properties = Properties.from_mapping({"a": 1, "b": "x"})

    assert properties["a"] == 1
    assert properties["b"] == "x"


def test_get_returns_default_for_missing_key() -> None:
    properties = Properties.of(a=1)

    assert properties.get("missing") is None
    assert properties.get("missing", "fallback") == "fallback"


def test_getitem_raises_key_error_for_missing_key() -> None:
    properties = Properties.of(a=1)

    with pytest.raises(KeyError):
        properties["missing"]


def test_contains() -> None:
    properties = Properties.of(a=1)

    assert "a" in properties
    assert "b" not in properties


def test_len_and_iter() -> None:
    properties = Properties.of(a=1, b=2)

    assert len(properties) == 2
    assert set(properties) == {"a", "b"}


def test_empty_properties() -> None:
    properties = Properties()

    assert len(properties) == 0
    assert properties.items() == ()


def test_with_property_returns_new_instance() -> None:
    original = Properties.of(a=1)

    updated = original.with_property("b", 2)

    assert "b" not in original
    assert updated["a"] == 1
    assert updated["b"] == 2


def test_list_values_are_normalized_to_tuples() -> None:
    properties = Properties.of(tags=["a", "b", "c"])

    assert properties["tags"] == ("a", "b", "c")
    assert isinstance(properties["tags"], tuple)


def test_float_and_bool_values_are_supported() -> None:
    properties = Properties.of(score=1.5, flag=False)

    assert properties["score"] == 1.5
    assert properties["flag"] is False


def test_unsupported_value_type_raises() -> None:
    with pytest.raises(TypeError):
        Properties.of(bad={"nested": "dict"})


def test_unsupported_list_element_type_raises() -> None:
    with pytest.raises(TypeError):
        Properties.of(bad=[{"nested": "dict"}])


def test_properties_is_immutable() -> None:
    properties = Properties.of(a=1)

    with pytest.raises(dataclasses.FrozenInstanceError):
        properties._items = ()  # type: ignore[misc]


def test_properties_is_hashable() -> None:
    a = Properties.of(a=1, b=2)
    b = Properties.of(b=2, a=1)

    assert a == b
    assert hash(a) == hash(b)


def test_as_dict_returns_plain_dict() -> None:
    properties = Properties.of(a=1, b=2)

    assert properties.as_dict() == {"a": 1, "b": 2}
    assert isinstance(properties.as_dict(), dict)


def test_items_are_sorted_by_key() -> None:
    properties = Properties.of(zeta=1, alpha=2)

    assert [key for key, _ in properties.items()] == ["alpha", "zeta"]
