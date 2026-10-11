"""The resolver's declared-input rule (ADR-0017): a reference whose root is a declared
non-``any`` input is never JSON-parsed — at the simple-template leaf or mid-path.

The declarations ride the context under ``DECLARED_INPUT_TYPES_KEY``; without the key
(or for ``any``) today's parse is unchanged — every case below has that presence half.
"""

from typing import Any, ClassVar

import pytest

from pflow.core.templates import DECLARED_INPUT_TYPES_KEY, TemplateResolver, parse_path, resolve, unparsed_declared_text

KEY = DECLARED_INPUT_TYPES_KEY


def _ctx(values: dict[str, Any], types: dict[str, str] | None) -> dict[str, Any]:
    return {**values, KEY: types} if types is not None else dict(values)


class TestTheLeaf:
    """A simple template's JSON text is parsed under ``auto_parse`` — unless it is a declared input's."""

    def test_declared_string_text_stays_text(self) -> None:
        context = _ctx({"s": '{"a":1}'}, {"s": "string"})
        assert resolve("${s}", context, auto_parse=True).value == '{"a":1}'

    @pytest.mark.parametrize("types", [None, {"s": "any"}, {"other": "string"}])
    def test_undeclared_or_any_text_is_parsed(self, types: dict[str, str] | None) -> None:
        assert resolve("${s}", _ctx({"s": '{"a":1}'}, types), auto_parse=True).value == {"a": 1}

    def test_coalesce_is_judged_by_the_operand_that_supplied_the_value(self) -> None:
        upstream = {"u": {"out": '{"b":2}'}}
        absent_input = _ctx(upstream, {"s": "string"})
        assert resolve("${s ?? u.out}", absent_input, auto_parse=True).value == {"b": 2}
        present_input = _ctx({**upstream, "s": '{"a":1}'}, {"s": "string"})
        assert resolve("${s ?? u.out}", present_input, auto_parse=True).value == '{"a":1}'


class TestTheWalkIsRootWide:
    """Ruling (i): a string descendant of a declared object/array input stays text too."""

    DATA: ClassVar[dict[str, Any]] = {"d": {"payload": '{"a":1}'}}

    def test_declared_object_descendant_text_is_not_walked_into(self) -> None:
        resolution = resolve("${d.payload.a}", _ctx(self.DATA, {"d": "object"}))
        assert resolution.unresolved == {"d.payload.a"}
        assert resolution.value == "${d.payload.a}"

    def test_without_the_declaration_the_walk_parses(self) -> None:
        assert resolve("${d.payload.a}", _ctx(self.DATA, None)).value == 1

    def test_the_text_itself_resolves(self) -> None:
        assert resolve("${d.payload}", _ctx(self.DATA, {"d": "object"}), auto_parse=True).value == '{"a":1}'

    def test_a_path_through_real_containers_still_resolves(self) -> None:
        context = _ctx({"arr": [{"x": 5}]}, {"arr": "array"})
        assert resolve("${arr[0].x}", context).value == 5

    def test_an_index_into_declared_text_is_a_miss(self) -> None:
        context = _ctx({"d": {"items": "[1, 2]"}}, {"d": "object"})
        assert resolve("${d.items[0]}", context).unresolved == {"d.items[0]"}
        assert resolve("${d.items[0]}", _ctx({"d": {"items": "[1, 2]"}}, None)).value == 1

    def test_any_keeps_the_traversal_parse(self) -> None:
        assert resolve("${v.a}", _ctx({"v": '{"a":1}'}, {"v": "any"})).value == 1

    def test_raw_path_readers_inherit_the_rule(self) -> None:
        protected = _ctx(self.DATA, {"d": "object"})
        assert TemplateResolver.variable_exists("d.payload.a", protected) is False
        assert TemplateResolver.variable_exists("d.payload", protected) is True
        assert TemplateResolver.variable_exists("d.payload.a", _ctx(self.DATA, None)) is True


class TestWhyItMissed:
    def _ref(self, text: str) -> Any:
        ref = parse_path(text)
        assert ref is not None
        return ref

    def test_names_the_text_the_walk_stopped_at(self) -> None:
        context = _ctx({"d": {"payload": '{"a":1}'}}, {"d": "object"})
        assert unparsed_declared_text(self._ref("d.payload.a"), context) == ("d.payload", '{"a":1}')

    def test_names_an_indexed_text(self) -> None:
        context = _ctx({"d": ['{"a":1}']}, {"d": "array"})
        assert unparsed_declared_text(self._ref("d[0].a"), context) == ("d[0]", '{"a":1}')

    @pytest.mark.parametrize(
        ("values", "types", "path"),
        [
            ({"d": {"payload": '{"a":1}'}}, None, "d.payload.a"),  # not declared
            ({"d": {"payload": '{"a":1}'}}, {"d": "object"}, "d.nope"),  # a plain missing field
            ({"d": {"payload": "plain"}}, {"d": "object"}, "d.payload.a"),  # text, but not JSON
            ({"d": {"payload": '{"a":1}'}}, {"d": "object"}, "d.payload"),  # it resolves
        ],
    )
    def test_other_misses_have_no_such_reason(self, values: dict, types: dict | None, path: str) -> None:
        assert unparsed_declared_text(self._ref(path), _ctx(values, types)) is None
