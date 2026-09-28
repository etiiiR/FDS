import json
import os


def load_graph():
    # Load the graph from a JSON file.
    #
    # Expected structure:
    # {
    #     "BranchName": {
    #         "CommitName": ["ParentCommit1", "ParentCommit2", ...]
    #     }
    # }
    #
    # Example:
    # {
    #     "A": {
    #         "A1": ["B2"],
    #         "A2": ["A1"]
    #     },
    #     "B": {
    #         "B1": [],
    #         "B2": ["B1"]
    #     }
    # }
    #
    # Branches represent processes.
    # Commits represent events.
    # Parent lists represent causal dependencies.

    with open('./template/task1/data.json', 'r') as f:
        graph = json.load(f)

    return graph


def get_metadata(graph: dict) -> tuple[list[str], int, dict]:
    # Extract the branch names from the outer JSON keys.
    #
    # Example:
    # ["A", "B", "C", "D"]

    branches = list(graph.keys())

    # Number of branches = number of components
    # in every vector clock.
    #
    # Example:
    # 4 branches -> vector clock has 4 entries:
    # [A, B, C, D]

    n = len(branches)

    # Create an empty structure that will later contain
    # the calculated vector clock of EVERY COMMIT.
    #
    # Important:
    # vector clocks belong to commits/events, not to branches.
    #
    # Desired structure later:
    #
    # {
    #     "B1": [0, 1, 0, 0],
    #     "B2": [0, 2, 0, 0],
    #     "A1": [1, 2, 0, 0],
    #     ...
    # }
    #
    # Therefore this probably should initially be an empty dict.

    vector_clocks = {}

    return branches, n, vector_clocks


def calculate_vector_clocks(graph):
    # Calculate one vector clock for every commit/event in the DAG.
    #
    # General idea:
    #
    # Repeat until every commit has a vector clock:
    #
    #   1. Iterate over every branch.
    #
    #   2. Iterate over every commit inside that branch.
    #
    #   3. Skip the commit if its vector clock was already calculated.
    #
    #   4. Get the list of parent commits.
    #
    #   5. Check whether ALL parents already have a vector clock.
    #
    #      Special case:
    #      A commit with [] has no parents, so it can immediately
    #      be calculated.
    #
    #   6. If not all parents are calculated yet:
    #      skip this commit for now.
    #
    #   7. If all parents are available:
    #
    #      a) Create a zero vector of length number_of_branches.
    #
    #         Example with 4 branches:
    #         [0, 0, 0, 0]
    #
    #      b) For every parent:
    #         merge the parent's vector clock into the new vector
    #         component-wise using max().
    #
    #         Example:
    #
    #         parent 1: [2, 1, 0, 0]
    #         parent 2: [1, 2, 1, 0]
    #
    #         merged:   [2, 2, 1, 0]
    #
    #      c) Determine on which branch the current commit occurs.
    #
    #      d) Find the index of that branch in the branch list.
    #
    #         Example:
    #
    #         branches = ["A", "B", "C", "D"]
    #
    #         branch C -> index 2
    #
    #      e) Increment exactly that component by 1.
    #
    #         Example:
    #
    #         before event on C:
    #         [2, 2, 1, 0]
    #
    #         after event on C:
    #         [2, 2, 2, 0]
    #
    #      f) Store the resulting vector under the commit name.
    #
    #         vector_clocks[commit_name] = calculated_clock
    #
    #
    # Important:
    # Do NOT depend on the order of commits in the JSON file.
    #
    # The algorithm should work even if a child appears in the
    # JSON before its parent. In that case the child simply has
    # to wait until a later iteration.

    vector_clocks = {}

    # Determine branches dynamically from the JSON.
    branches = list(graph.keys())

    # Count the total number of commits.
    #
    # IMPORTANT:
    # len(graph) only gives the number of BRANCHES,
    # not the number of COMMITS.
    #
    # You need the total number of commits so that the loop
    # knows when all events have been processed.

    total_commits = None  # TODO

    # Continue until:
    #
    # number of calculated commit clocks == total number of commits

    while False:  # TODO: replace with correct condition

        # Iterate over every branch.
        #
        # graph.items() gives something like:
        #
        # branch_name = "A"
        #
        # commits = {
        #     "A1": ["B2"],
        #     "A2": ["A1"]
        # }

        for branch_name, commits in graph.items():

            # Iterate over every commit belonging to this branch.
            #
            # commit_name might be "A1"
            # parents might be ["B2"]

            for commit_name, parents in commits.items():

                # TODO:
                # Skip commits that already have a vector clock.

                # TODO:
                # Check whether all parent commits are already
                # present in vector_clocks.

                # TODO:
                # If one or more parents are missing:
                # continue and try this commit again later.

                # TODO:
                # Create a zero vector with one entry per branch.

                # TODO:
                # Merge all parent vector clocks component-wise
                # using maximum values.

                # TODO:
                # Find the component corresponding to branch_name.

                # TODO:
                # Increment that component by one.

                # TODO:
                # Store the finished clock:
                #
                # vector_clocks[commit_name] = ...

                pass

    # TODO:
    # Return the completed dictionary.
    return vector_clocks


def causally_precedes(a, b):
    # Determine whether vector clock a causally precedes b.
    #
    # According to the vector-clock ordering:
    #
    # a precedes b if:
    #
    # 1. Every component of a is <= the corresponding component of b
    #
    # AND
    #
    # 2. At least one component of a is strictly < the corresponding
    #    component of b.
    #
    # Example:
    #
    # a = [1, 1, 0]
    # b = [2, 1, 1]
    #
    # -> True
    #
    # Example:
    #
    # a = [2, 0, 0]
    # b = [1, 1, 0]
    #
    # -> False
    #
    # They are incomparable / concurrent because one component
    # is larger and another is smaller.

    pass


def build_causal_graph():
    # Build a graph from the calculated vector clocks.
    #
    # Nodes:
    #   every commit
    #
    # Edges:
    #   add edge A -> B whenever:
    #
    #       causally_precedes(clock[A], clock[B])
    #
    # Important:
    # At this stage ALL causal relationships should be included,
    # even if some edges are redundant.
    #
    # Example:
    #
    # A -> B
    # B -> C
    # A -> C
    #
    # A -> C should still exist here.

    pass


def reduce_causal_graph():
    # Remove redundant/transitive edges from the causal graph.
    #
    # Example:
    #
    # A -> B
    # B -> C
    # A -> C
    #
    # A -> C is redundant because A can already reach C via B.
    #
    # Reduced graph:
    #
    # A -> B -> C
    #
    # Goal:
    # preserve the same causal partial order while using the
    # minimum necessary edges.
    #
    # This operation is called a "transitive reduction".

    pass


if __name__ == '__main__':
    graph = load_graph()

    branches, n, vector_clocks = get_metadata(graph)

    print(f"Branches: {branches}, Number of branches: {n}")

    vector_clocks = calculate_vector_clocks(graph)

    # Later:
    #
    # causally_precedes(a, b)
    # build_causal_graph()
    # reduce_causal_graph()