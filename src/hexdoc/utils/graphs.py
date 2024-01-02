from typing import Any, Generic, Iterable, TypeVar

import networkx as nx
from typing_extensions import override

_Node = TypeVar("_Node")


class TypedDiGraph(nx.DiGraph, Generic[_Node]):  # type: ignore
    """A very incomplete wrapper type over `nx.DiGraph` to add some type hints."""

    @override
    def add_edge(self, u_of_edge: _Node, v_of_edge: _Node, **attr: Any) -> None:
        super().add_edge(u_of_edge, v_of_edge, **attr)  # type: ignore

    def iter_out_edges(self, node: _Node) -> Iterable[tuple[_Node, _Node]]:
        return self.out_edges(node)  # type: ignore

    def find_cycle(self) -> list[tuple[_Node, _Node]] | None:
        try:
            return nx.find_cycle(self)  # type: ignore
        except nx.NetworkXNoCycle:
            return None

    def topological_sort(self) -> Iterable[_Node]:
        return nx.topological_sort(self)  # type: ignore
