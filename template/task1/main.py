"""Calculate vector clocks and reconstruct their causal DAG (Task 1)."""

import argparse
import json
from pathlib import Path


def load_graph(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name("data.json")
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def calculate_vector_clocks(graph):
    """Merge parent clocks componentwise, then advance the commit's branch."""
    if not isinstance(graph, dict):
        raise ValueError("The graph must map branch names to commits.")
    branches = list(graph)
    commits = {}
    for branch_index, (branch, branch_commits) in enumerate(graph.items()):
        if not isinstance(branch_commits, dict):
            raise ValueError(f"Branch {branch!r} must contain a commit dictionary.")
        for commit, parents in branch_commits.items():
            if commit in commits:
                raise ValueError(f"Duplicate commit ID: {commit}")
            if not isinstance(parents, list) or any(not isinstance(p, str) for p in parents):
                raise ValueError(f"Parents of {commit} must be a list of commit IDs.")
            commits[commit] = (branch_index, parents)
    for commit, (_, parents) in commits.items():
        missing = set(parents) - commits.keys()
        if missing:
            raise ValueError(f"Unknown parents of {commit}: {', '.join(sorted(missing))}")
    clocks = {}
    pending = dict(commits)
    while pending:
        ready = [commit for commit, (_, parents) in pending.items()
                 if all(parent in clocks for parent in parents)]
        if not ready:
            raise ValueError("The commit graph contains a cycle.")
        for commit in ready:
            branch_index, parents = pending.pop(commit)
            clock = [0] * len(branches)
            for parent in parents:
                clock = [max(a, b) for a, b in zip(clock, clocks[parent])]
            clock[branch_index] += 1
            clocks[commit] = clock
    return clocks


def causally_precedes(a, b):
    """Strict vector-clock order; equal and concurrent clocks do not precede."""
    if len(a) != len(b):
        raise ValueError("Vector clocks must have the same number of components.")
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def build_causal_graph(vector_clocks):
    return {
        source: [target for target, clock in vector_clocks.items()
                 if causally_precedes(source_clock, clock)]
        for source, source_clock in vector_clocks.items()
    }


def reduce_causal_graph(causal_graph):
    """Remove an edge only when another path preserves its reachability."""
    reduced = {source: list(targets) for source, targets in causal_graph.items()}
    for source, targets in causal_graph.items():
        for target in targets:
            reduced[source].remove(target)
            pending = list(reduced[source])
            visited = set()
            while pending:
                current = pending.pop()
                if current == target:
                    break
                if current not in visited:
                    visited.add(current)
                    pending.extend(reduced.get(current, []))
            else:
                reduced[source].append(target)
    return reduced


def write_dot(graph, path, vector_clocks=None):
    """Export a Graphviz graph, including isolated nodes and clock labels."""
    lines = ["digraph causality {", "  rankdir=LR;"]
    for commit, targets in graph.items():
        label = commit
        if vector_clocks is not None:
            label += "\n" + str(vector_clocks[commit])
        lines.append(f"  {json.dumps(commit)} [label={json.dumps(label)}];")
        for target in targets:
            lines.append(f"  {json.dumps(commit)} -> {json.dumps(target)};")
    lines.append("}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path,
                        default=Path(__file__).with_name("data.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/task1"))
    args = parser.parse_args(argv)
    try:
        clocks = calculate_vector_clocks(load_graph(args.input))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    causal = build_causal_graph(clocks)
    reduced = reduce_causal_graph(causal)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in [("vector_clocks", clocks), ("causal_graph", causal),
                        ("reduced_graph", reduced)]:
        (args.output_dir / f"{name}.json").write_text(
            json.dumps(value, indent=2) + "\n", encoding="utf-8")
    write_dot(causal, args.output_dir / "causal_graph.dot", clocks)
    write_dot(reduced, args.output_dir / "reduced_graph.dot", clocks)
    print(json.dumps(clocks, indent=2))
    print(f"JSON results and Graphviz graphs written to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
