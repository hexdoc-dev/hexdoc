# pyright: reportUnusedFunction=none

import copy

import pytest

from hexdoc.utils.deserialize.toml import TOMLDict, fill_placeholders


def _fill_placeholders_assert_valid(data: TOMLDict, want: TOMLDict):
    got = copy.deepcopy(data)
    fill_placeholders(got)
    assert got == want


def describe_fill_placeholders():
    def describe_valid_input():
        @pytest.mark.parametrize(
            ["data", "want"],
            [
                [{}, {}],
                [{"": ""}, {"": ""}],
                [{"key": "value"}, {"key": "value"}],
            ],
        )
        def no_placeholders(data: TOMLDict, want: TOMLDict):
            _fill_placeholders_assert_valid(data, want)

        @pytest.mark.parametrize(
            ["data", "want"],
            [
                [
                    {"key": "{var}", "var": "value"},
                    {"key": "value", "var": "value"},
                ],
                [
                    {"key": "foo {var} bar", "var": "value"},
                    {"key": "foo value bar", "var": "value"},
                ],
                [
                    {"key": "foo {var} bar {var}", "var": "value"},
                    {"key": "foo value bar value", "var": "value"},
                ],
            ],
        )
        def simple_placeholders(data: TOMLDict, want: TOMLDict):
            _fill_placeholders_assert_valid(data, want)

        @pytest.mark.parametrize(
            ["data", "want"],
            [
                [
                    {"foo": {"key": "{^var}"}, "var": "value"},
                    {"foo": {"key": "value"}, "var": "value"},
                ],
                [
                    {"foo": {"bar": {"key": "{^^var}"}}, "var": "value"},
                    {"foo": {"bar": {"key": "value"}}, "var": "value"},
                ],
                [
                    {"foo": {"bar": {"baz": {"key": "{^^^var}"}}}, "var": "value"},
                    {"foo": {"bar": {"baz": {"key": "value"}}}, "var": "value"},
                ],
            ],
        )
        def parent_references(data: TOMLDict, want: TOMLDict):
            _fill_placeholders_assert_valid(data, want)

        @pytest.mark.parametrize(
            ["data", "want"],
            [
                [
                    {"key": "{$var}", "var": "value"},
                    {"key": "value", "var": "value"},
                ],
                [
                    {"foo": {"key": "{$var}"}, "var": "value"},
                    {"foo": {"key": "value"}, "var": "value"},
                ],
                [
                    {"foo": {"bar": {"key": "{$var}"}}, "var": "value"},
                    {"foo": {"bar": {"key": "value"}}, "var": "value"},
                ],
                [
                    {"foo": {"bar": {"baz": {"key": "{$var}"}}}, "var": "value"},
                    {"foo": {"bar": {"baz": {"key": "value"}}}, "var": "value"},
                ],
            ],
        )
        def root_references(data: TOMLDict, want: TOMLDict):
            _fill_placeholders_assert_valid(data, want)

        @pytest.mark.parametrize(
            ["data", "want"],
            [
                [
                    {"foo": ["{var}"], "var": "value"},
                    {"foo": ["value"], "var": "value"},
                ],
                [
                    {"foo": [{"key": "{^var}"}], "var": "value"},
                    {"foo": [{"key": "value"}], "var": "value"},
                ],
                [
                    {"foo": ["{$var}"], "var": "value"},
                    {"foo": ["value"], "var": "value"},
                ],
                [
                    {"foo": [{"key": "{$var}"}], "var": "value"},
                    {"foo": [{"key": "value"}], "var": "value"},
                ],
            ],
        )
        def arrays(data: TOMLDict, want: TOMLDict):
            _fill_placeholders_assert_valid(data, want)

        def describe_intrinsic_functions():
            @pytest.mark.parametrize(
                ["data", "want"],
                [
                    [
                        {"key": {"!Raw": ""}},
                        {"key": ""},
                    ],
                    [
                        {"key": {"!Raw": "value"}},
                        {"key": "value"},
                    ],
                    [
                        {"key": {"!Raw": "{var}"}, "var": "value"},
                        {"key": "{var}", "var": "value"},
                    ],
                    [
                        {"key": {"!Raw": "^{.+}$"}},
                        {"key": "^{.+}$"},
                    ],
                    [
                        {"key": {"!Raw": {}}},
                        {"key": {}},
                    ],
                    [
                        {"key": {"!Raw": {"!Raw": "value"}}},
                        {"key": {"!Raw": "value"}},
                    ],
                ],
            )
            def raw(data: TOMLDict, want: TOMLDict):
                _fill_placeholders_assert_valid(data, want)

            @pytest.mark.parametrize(
                ["data", "want"],
                [
                    [
                        {"key": {"!None": ""}},
                        {"key": None},
                    ],
                    [
                        {"key": {"!None": "value"}},
                        {"key": None},
                    ],
                    [
                        {"key": {"!None": {}}},
                        {"key": None},
                    ],
                ],
            )
            def none(data: TOMLDict, want: TOMLDict):
                _fill_placeholders_assert_valid(data, want)

    @pytest.mark.parametrize(
        ["data", "want_err"],
        [
            [{"key": "{var}"}, KeyError],
            pytest.param(
                {"key": "{^var}", "var": "value"},
                KeyError,
                marks=pytest.mark.xfail,
            ),
            [{"key": "{var}", "var": 0}, TypeError],
        ],
    )
    def invalid_input(data: TOMLDict, want_err: type[Exception]):
        with pytest.raises(want_err):
            fill_placeholders(data)
