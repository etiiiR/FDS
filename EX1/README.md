# Foundations of Distributed Systems: Tasks 1–3

Solutions to the first three tasks in `exercise_sheet.pdf`.
Run the commands below from the repository root. Python 3 and Node.js are required.

## Setup on Windows / PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci --prefix template/task2/dataServer
.\.venv\Scripts\python.exe template/task2/generate_stubs.py
```

The virtual environment includes `pypdf`, a Python PDF reader. Read the exercise:

```powershell
.\.venv\Scripts\python.exe tools/read_pdf.py exercise_sheet.pdf
```

## Task 1: Vector clocks

```powershell
.\.venv\Scripts\python.exe template/task1/main.py
```

This reads the bundled `data.json` and writes the following to `output/task1/`:

- `vector_clocks.json`: commit IDs mapped to clock vectors; components follow the
  input JSON's branch order.
- `causal_graph.json` and `causal_graph.dot`: every strict causal relationship.
- `reduced_graph.json` and `reduced_graph.dot`: the transitive reduction, retaining
  all reachability with the minimum edges for this DAG.

Use another graph or output directory:

```powershell
.\.venv\Scripts\python.exe template/task1/main.py path/to/graph.json --output-dir output/custom
```

The `.dot` files satisfy the exercise's Graphviz export option. If Graphviz is
installed, render them with `dot -Tsvg output/task1/reduced_graph.dot -o output/task1/reduced_graph.svg`.
The script rejects duplicate commit IDs, missing parents, and cycles.

## Task 2: gRPC delegation

Open three terminals at the repository root. Run one command in each:

```powershell
node template/task2/dataServer/dataServer.js
```

```powershell
.\.venv\Scripts\python.exe template/task2/hashServer/server.py
```

```powershell
.\.venv\Scripts\python.exe template/task2/client/client.py --message "distributed systems"
```

Connect to the servers at `127.0.0.1:50051` and `127.0.0.1:50052`. The client registers
a user, stores its text, obtains a one-time passcode, and asks the hash server to
retrieve the text and return its SHA-256 hash. The hash server receives the
passcode, data-server IP, and port; the password stays between client and data server.

Each invocation chooses a fresh default username. You can specify `--username`
and `--password`; an existing username is rejected. Data is kept in memory and
cleared when the data server stops. The supplied `dataServer.js` is kept unchanged.
It returns empty text for invalid or consumed passcodes, so the hash server cannot
distinguish those responses from valid empty text. RPC calls have timeouts.
Stop servers with Ctrl+C.

## Task 3: Leader election

```powershell
.\.venv\Scripts\python.exe template/task3/main.py --nodes 3
```

Commands: `state`, `crash`, `recover`, and `quit`. For `crash` and `recover`, enter
the node ID at the next prompt. Wait approximately 4–6 seconds for the initial
election, use `state` to find the leader, then crash it and observe a replacement
election when a majority is still working. Recover the former leader and it
returns as a follower. EOF and Ctrl+C also stop and join all node threads.

The exercise timings are preserved: a 1-second heartbeat timeout, a random
1–3-second wait before announcing candidacy, 2 seconds to collect votes, and
heartbeats every 0.5 seconds. A lock protects the shared buffer and node state.
Messages include an election term; a node votes once per term and keeps that
vote across simulated crashes. Older messages cannot interfere with a newer term.
Votes are counted against all configured nodes, including crashed nodes.

This is an educational leader-election simulator. It does not implement log
replication, durable storage across process restarts, or full Raft consensus.

## Verification

With ports 50051 and 50052 free:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover the exercise's clock example, causal graph reduction, invalid graphs,
real gRPC servers with passcode consumption and Unicode/empty text, deterministic
election scenarios, threaded failover/recovery, and clean CLI exit.
The integration tests start and stop their own server processes.
