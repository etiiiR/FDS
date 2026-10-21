import contextlib
import io
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

from EX1.tests.helpers import ROOT, load_task

task = load_task(3)


class ElectionTests(unittest.TestCase):
    def setUp(self):
        task.shutdown()
        task.buffer.clear()
        self.now = 100.0
        self.clock = patch.object(task.time, "monotonic", lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.create_nodes(3)

    def create_nodes(self, count):
        task.buffer.clear()
        task.nodes = [task.Node(i) for i in range(count)]

    def advance(self, seconds):
        for _ in range(round(seconds / 0.1)):
            self.now += 0.1
            with task.network_lock:
                for node in task.nodes:
                    if node.working:
                        while task.buffer[node.id]:
                            node.deliver(*task.buffer[node.id].pop(0))
                        node.tick()

    def leaders(self):
        return [node for node in task.nodes if node.working and node.state == "leader"]

    def start_candidate(self, node, term):
        node.current_term = term
        node.state = "candidate"
        node.voted_for = node.id
        node.votes = {node.id}
        node.vote_collection_start = self.now

    def test_startup_failover_and_recovery(self):
        with patch.object(task.random, "uniform", side_effect=[1.1, 1.5, 1.8, 1.1, 1.8]):
            self.advance(7)
            self.assertEqual(len(self.leaders()), 1)
            original = self.leaders()[0]
            self.assertTrue(all(n.leader_id == original.id for n in task.nodes))
            original.crash()
            self.advance(7)
            self.assertEqual(len(self.leaders()), 1)
            replacement = self.leaders()[0]
            self.assertNotEqual(original.id, replacement.id)
            original.recover()
            self.advance(1)
            self.assertEqual(original.state, "follower")
            self.assertEqual(original.leader_id, replacement.id)

    def test_a_minority_cannot_elect_a_leader(self):
        task.nodes[1].crash()
        task.nodes[2].crash()
        with patch.object(task.random, "uniform", return_value=1.2):
            self.advance(20)
        self.assertEqual(self.leaders(), [])

    def test_single_node_can_elect_itself(self):
        self.create_nodes(1)
        with patch.object(task.random, "uniform", return_value=1.2):
            self.advance(5)
        self.assertEqual([n.id for n in self.leaders()], [0])

    def test_voter_cannot_vote_twice_after_crash_and_recovery(self):
        a, voter, c = task.nodes
        self.start_candidate(a, 1)
        self.start_candidate(c, 1)
        voter.deliver("candidacy", (1, a.id))
        a.deliver("vote", (1, voter.id, a.id))
        voter.crash()
        voter.recover()
        voter.deliver("candidacy", (1, c.id))
        self.assertEqual(voter.voted_for, a.id)
        self.assertFalse(any(kind == "vote" and value == (1, voter.id, c.id)
                             for messages in task.buffer.values() for kind, value in messages))
        self.advance(3)
        self.assertEqual([n.id for n in self.leaders()], [a.id])

    def test_old_votes_and_heartbeats_do_not_affect_new_term(self):
        candidate = task.nodes[0]
        self.start_candidate(candidate, 2)
        candidate.deliver("vote", (1, 1, candidate.id))
        candidate.deliver("heartbeat", (1, 1))
        self.assertEqual(candidate.votes, {candidate.id})
        self.assertEqual(candidate.state, "candidate")
        self.assertEqual(candidate.current_term, 2)

    def test_duplicate_votes_are_counted_once(self):
        candidate = task.nodes[0]
        self.start_candidate(candidate, 1)
        candidate.deliver("vote", (1, 1, candidate.id))
        candidate.deliver("vote", (1, 1, candidate.id))
        self.assertEqual(candidate.votes, {0, 1})

    def test_candidacy_cancels_random_wait(self):
        node = task.nodes[1]
        self.now += 1.1
        node.tick()
        self.assertEqual(node.state, "candidate")
        node.deliver("candidacy", (1, 0))
        self.assertEqual(node.state, "follower")
        self.assertEqual(node.voted_for, 0)
        self.assertIsNone(node.election_wait_start)

    def test_heartbeat_cancels_vote_collection(self):
        candidate = task.nodes[0]
        self.start_candidate(candidate, 1)
        candidate.deliver("heartbeat", (2, 1))
        self.assertEqual(candidate.state, "follower")
        self.assertEqual(candidate.leader_id, 1)
        self.assertIsNone(candidate.vote_collection_start)
        self.assertFalse(candidate.votes)

    def test_failed_split_vote_is_retried_in_a_new_term(self):
        for node in task.nodes:
            self.start_candidate(node, 1)
        with patch.object(task.random, "uniform", side_effect=[1.1, 1.5, 1.8]):
            self.advance(8)
        self.assertEqual(len(self.leaders()), 1)
        self.assertGreater(self.leaders()[0].current_term, 1)


class ThreadedElectionTests(unittest.TestCase):
    def test_real_threads_survive_failover_and_rapid_crash_recovery(self):
        failures = []
        with contextlib.redirect_stdout(io.StringIO()), \
                patch.object(threading, "excepthook", lambda args: failures.append(args.exc_value)), \
                patch.object(task.random, "uniform", return_value=1.1):
            try:
                task.initialize(3)

                def wait_for_leader(excluded=None):
                    deadline = time.monotonic() + 7
                    while time.monotonic() < deadline:
                        with task.network_lock:
                            leaders = [n for n in task.nodes if n.working and n.state == "leader"]
                            if len(leaders) == 1 and leaders[0].id != excluded:
                                return leaders[0]
                        time.sleep(0.05)
                    self.fail("No unique leader was elected within seven seconds.")

                original = wait_for_leader()
                original.crash()
                replacement = wait_for_leader(excluded=original.id)
                original.recover()
                time.sleep(0.7)
                self.assertEqual(original.state, "follower")
                self.assertEqual(original.leader_id, replacement.id)
                for _ in range(100):
                    original.crash()
                    time.sleep(0.001)
                    original.recover()
                time.sleep(0.2)
                self.assertTrue(all(n.thread.is_alive() for n in task.nodes))
                self.assertEqual(failures, [])
            finally:
                task.shutdown()
            self.assertTrue(all(not n.thread.is_alive() for n in task.nodes))

    def test_cli_handles_bad_input_quit_and_eof(self):
        for commands in ["crash\nabc\nrecover\n99\nstate\nquit\n", ""]:
            with self.subTest(commands=commands):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "template/task3/main.py")],
                    input=commands, text=True, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
