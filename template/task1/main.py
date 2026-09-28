import json
import os
import copy

def load_graph():
    with open('./FDS/template/task1/data.json', 'r') as f:
        graph = json.load(f)

    return graph


def calculate_vector_clocks(graph):
    vector_clocks = {}
    branches = list(graph.keys())
    total_commits = sum(len(commits) for commits in graph.values())

    while len(vector_clocks) < total_commits:

        for branch_name, commits in graph.items():

            for commit_name, parents in commits.items():

                if commit_name in vector_clocks:
                    continue

                if not all(parent in vector_clocks for parent in parents):
                    continue

                parent_clocks = []

                for parent in parents:
                    parent_clocks.append(vector_clocks[parent])

                calculated_clock = [0] * len(branches)

                for parent_clock in parent_clocks:
                    for n_brnch in range(len(branches)):
                        calculated_clock[n_brnch] = max(
                            calculated_clock[n_brnch],
                            parent_clock[n_brnch]
                        )
                branch_index = branches.index(branch_name)
                calculated_clock[branch_index] += 1

                vector_clocks[commit_name] = calculated_clock

    return vector_clocks


def causally_precedes(a, b):
    # check 1
    smaller = False
    for i in range(len(a)):
        if a[i] > b[i]:
            return False
        if a[i] < b[i]:
            smaller = True
    return smaller


def build_causal_graph(vector_clocks):
    causal_graph = {}
    for commit_a in vector_clocks:
        for commit_b in vector_clocks:
            if commit_a == commit_b:
                continue
            if causally_precedes(vector_clocks[commit_a], vector_clocks[commit_b]):
                causal_graph[commit_a].append(commit_b)
    # für jeden Commit A
        # für jeden Commit B
            # A != B
            # wenn A causally_precedes B:
                # B als Nachfolger von A speichern

    return causal_graph


def reduce_causal_graph(causal_graph):
    reduced_graph = copy(causal_graph)

    for start in causal_graph:
        for target in causal_graph[start]:

            # edge start -> target testweise entfernen

            # prüfen:
            # kann ich target trotzdem noch von start aus erreichen?

            # wenn ja:
            # edge ist redundant

            # wenn nein:
            # edge wieder hinzufügen

    return reduced_graph


if __name__ == '__main__':
    graph = load_graph()
    vector_clocks = {}

    vector_clocks = calculate_vector_clocks(graph)
    print(vector_clocks)