"""Threaded leader-election simulator with crash and recovery (Task 3)."""

import argparse
import random
import threading
import time

HEARTBEAT_INTERVAL = 0.5
HEARTBEAT_TIMEOUT = 1.0
VOTE_COLLECTION_TIME = 2.0
POLL_INTERVAL = 0.1
nodes = []
buffer = {}  # node_id: [(message_type, payload)]
# Protect the simulated network and node transitions with a reentrant lock.
network_lock = threading.RLock()


class Node:
    def __init__(self, id):
        self.id = id
        self.working = True
        self.state = "follower"
        self.leader_id = None
        # These survive a simulated crash: one vote per election term.
        self.current_term = 0
        self.voted_for = None
        self.last_heartbeat = time.monotonic()
        self.last_heartbeat_sent = 0.0
        self.election_wait_start = None
        self.election_delay = None
        self.vote_collection_start = None
        self.election_in_progress_until = None
        self.votes = set()
        self.stop_event = threading.Event()
        self.thread = None
        with network_lock:
            buffer[id] = []

    def start(self):
        if self.thread is not None:
            raise RuntimeError(f"Node {self.id} has already been started.")
        self.thread = threading.Thread(target=self.run, name=f"node-{self.id}")
        print(f"node {self.id} started")
        self.thread.start()

    def run(self):
        while not self.stop_event.is_set():
            with network_lock:
                if self.working:
                    while buffer[self.id]:
                        msg_type, value = buffer[self.id].pop(0)
                        self.deliver(msg_type, value)
                    self.tick()
                else:
                    buffer[self.id].clear()
            self.stop_event.wait(POLL_INTERVAL)

    def _cancel_election(self):
        self.election_wait_start = None
        self.election_delay = None
        self.vote_collection_start = None
        self.election_in_progress_until = None
        self.votes = set()

    def _adopt_term(self, term):
        self.current_term = term
        self.voted_for = None
        self.state = "follower"
        self.leader_id = None
        self._cancel_election()

    def tick(self):
        with network_lock:
            if not self.working:
                return
            now = time.monotonic()
            if self.state == "leader":
                if now - self.last_heartbeat_sent >= HEARTBEAT_INTERVAL:
                    self.broadcast("heartbeat", (self.current_term, self.id))
                    self.last_heartbeat_sent = now
                return

            if self.state == "follower":
                if self.election_in_progress_until is not None:
                    if now < self.election_in_progress_until:
                        return
                    self.election_in_progress_until = None
                if now - self.last_heartbeat > HEARTBEAT_TIMEOUT:
                    self.state = "candidate"
                    self.leader_id = None
                    self.election_wait_start = now
                    self.election_delay = random.uniform(1, 3)
                    print(f"node {self.id} wants to start an election "
                          f"(waiting {self.election_delay:.2f}s)")
                return

            if self.vote_collection_start is None:
                if now - self.election_wait_start >= self.election_delay:
                    self.current_term += 1
                    self.voted_for = self.id
                    self.votes = {self.id}
                    self.vote_collection_start = now
                    print(f"node {self.id} is starting an election "
                          f"(term {self.current_term})")
                    print(f"node {self.id} voted to node {self.id}")
                    self.broadcast("candidacy", (self.current_term, self.id))
                return

            if now - self.vote_collection_start >= VOTE_COLLECTION_TIME:
                count = len(self.votes)
                print(f"node {self.id} received {count} vote(s)")
                self._cancel_election()
                if count > len(nodes) / 2:
                    self.state = "leader"
                    self.leader_id = self.id
                    print(f"node {self.id} became leader")
                    self.broadcast("heartbeat", (self.current_term, self.id))
                    self.last_heartbeat_sent = now
                else:
                    self.state = "follower"
                    self.last_heartbeat = now
                    print(f"node {self.id} did not get a majority")

    def broadcast(self, msg_type, value):
        with network_lock:
            if self.working:
                for node in nodes:
                    if node.working:
                        buffer[node.id].append((msg_type, value))

    def deliver(self, msg_type, value):
        with network_lock:
            if not self.working:
                return
            if msg_type not in {"heartbeat", "candidacy", "vote"}:
                return
            term = value[0]
            if term < self.current_term:
                return  # Delayed messages cannot change a later election.
            if term > self.current_term:
                self._adopt_term(term)
            now = time.monotonic()

            if msg_type == "heartbeat":
                _, leader_id = value
                if self.state != "follower" and leader_id != self.id:
                    print(f"node {self.id} follows node {leader_id} as leader")
                self.state = "leader" if leader_id == self.id else "follower"
                self.leader_id = leader_id
                self.last_heartbeat = now
                self._cancel_election()

            elif msg_type == "candidacy":
                _, candidate_id = value
                self.election_in_progress_until = now + VOTE_COLLECTION_TIME + POLL_INTERVAL
                if (self.state == "candidate" and self.vote_collection_start is None
                        and candidate_id != self.id):
                    print(f"node {self.id} cancels its election because "
                          f"node {candidate_id} announced first")
                    self.state = "follower"
                    self.election_wait_start = None
                    self.election_delay = None
                if self.voted_for is None:
                    self.voted_for = candidate_id
                    print(f"node {self.id} voted to node {candidate_id}")
                    self.broadcast("vote", (term, self.id, candidate_id))

            else:
                _, voter_id, candidate_id = value
                if (self.state == "candidate" and self.vote_collection_start is not None
                        and candidate_id == self.id and any(n.id == voter_id for n in nodes)):
                    self.votes.add(voter_id)

    def crash(self):
        with network_lock:
            if self.working:
                self.working = False
                buffer[self.id].clear()
                print(f"node {self.id} crashed")

    def recover(self):
        with network_lock:
            if not self.working:
                buffer[self.id].clear()
                self.state = "follower"
                self.leader_id = None
                self.last_heartbeat = time.monotonic()
                self.last_heartbeat_sent = 0.0
                self._cancel_election()
                # Retain current_term and voted_for to avoid voting twice.
                self.working = True
                print(f"node {self.id} recovered")


def shutdown():
    for node in nodes:
        node.stop_event.set()
    for node in nodes:
        if node.thread is not None:
            node.thread.join()


def initialize(N):
    global nodes
    if N < 1:
        raise ValueError("The simulation needs at least one node.")
    shutdown()
    with network_lock:
        buffer.clear()
        nodes = [Node(i) for i in range(N)]
    for node in nodes:
        node.start()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=3)
    args = parser.parse_args(argv)
    if args.nodes < 1:
        parser.error("--nodes must be a positive integer")
    try:
        initialize(args.nodes)
        print("actions: state, crash, recover, quit")
        while True:
            action = input("\t$ ").strip().lower()
            if action in {"quit", "exit"}:
                break
            if action == "state":
                with network_lock:
                    for node in nodes:
                        status = "working" if node.working else "CRASHED"
                        print(f"\t\tnode {node.id}: {node.state} ({status}), "
                              f"leader={node.leader_id}, term={node.current_term}")
            elif action in {"crash", "recover"}:
                try:
                    node_id = int(input("\tid > "))
                except ValueError:
                    print("Enter an integer node ID.")
                    continue
                if not 0 <= node_id < len(nodes):
                    print(f"Node ID must be between 0 and {len(nodes) - 1}.")
                    continue
                getattr(nodes[node_id], action)()
            elif action:
                print("Unknown action. Use state, crash, recover, or quit.")
    except (EOFError, KeyboardInterrupt):
        print("\nStopping simulation.")
    finally:
        shutdown()


if __name__ == "__main__":
    main()
