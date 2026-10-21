import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from EX1.tests.helpers import ROOT, load_task

task = load_task(1)
EXAMPLE = {
    "B1": {"1111": [], "12f3": ["1111"], "f432": ["12f3", "2101"]},
    "B2": {"2101": ["1111"]},
    "B3": {"9634": ["2101"], "e13b": ["f432", "9634"]},
}
EXPECTED = {
    "1111": [1, 0, 0], "12f3": [2, 0, 0], "f432": [3, 1, 0],
    "2101": [1, 1, 0], "9634": [1, 1, 1], "e13b": [3, 1, 2],
}


def reachable(graph, source):
    found = set()
    pending = list(graph[source])
    while pending:
        current = pending.pop()
        if current not in found:
            found.add(current)
            pending.extend(graph[current])
    return found


class VectorClockTests(unittest.TestCase):
    def test_exercise_example(self):
        self.assertEqual(task.calculate_vector_clocks(EXAMPLE), EXPECTED)

    def test_repository_graph_merge_and_concurrency(self):
        clocks = task.calculate_vector_clocks(task.load_graph())
        self.assertEqual(clocks["D2"], [2, 2, 2, 2])
        self.assertFalse(task.causally_precedes(clocks["A2"], clocks["C2"]))
        self.assertFalse(task.causally_precedes(clocks["C2"], clocks["A2"]))
        self.assertTrue(task.causally_precedes(clocks["A2"], clocks["D2"]))

    def test_strict_partial_order(self):
        self.assertFalse(task.causally_precedes([1, 2], [1, 2]))
        self.assertTrue(task.causally_precedes([1, 2], [2, 2]))
        self.assertFalse(task.causally_precedes([2, 1], [1, 2]))
        with self.assertRaises(ValueError):
            task.causally_precedes([1], [1, 2])

    def test_empty_and_isolated_graphs(self):
        self.assertEqual(task.calculate_vector_clocks({}), {})
        clocks = task.calculate_vector_clocks({"A": {"a": []}, "B": {"b": []}})
        self.assertEqual(task.build_causal_graph(clocks), {"a": [], "b": []})

    def test_invalid_graphs_do_not_hang(self):
        for graph in [
            {"A": {"a": ["missing"]}},
            {"A": {"a": ["b"], "b": ["a"]}},
            {"A": {"a": []}, "B": {"a": []}},
            {"A": {"a": "parent"}},
        ]:
            with self.subTest(graph=graph), self.assertRaises(ValueError):
                task.calculate_vector_clocks(graph)

    def test_reduction_preserves_reachability_and_is_minimal(self):
        graph = task.build_causal_graph(EXPECTED)
        original = copy.deepcopy(graph)
        reduced = task.reduce_causal_graph(graph)
        self.assertEqual(graph, original)
        self.assertEqual(set(reduced["1111"]), {"12f3", "2101"})
        self.assertEqual(set(reduced["e13b"]), set())
        for source in graph:
            self.assertEqual(reachable(graph, source), reachable(reduced, source))
            for target in reduced[source]:
                without_edge = copy.deepcopy(reduced)
                without_edge[source].remove(target)
                self.assertNotIn(target, reachable(without_edge, source))

    def test_cli_outputs_json_and_both_dot_graphs_from_another_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "results"
            result = subprocess.run(
                [sys.executable, str(ROOT / "template/task1/main.py"),
                 "--output-dir", str(output)], cwd=temporary,
                capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            clocks = json.loads((output / "vector_clocks.json").read_text())
            self.assertEqual(clocks["D2"], [2, 2, 2, 2])
            for name in ["causal_graph", "reduced_graph"]:
                graph = json.loads((output / f"{name}.json").read_text())
                dot = (output / f"{name}.dot").read_text()
                self.assertIn('"D2" [label=', dot)
                self.assertEqual(dot.count(" -> "), sum(map(len, graph.values())))
