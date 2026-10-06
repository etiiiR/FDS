import hashlib
import importlib.util
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
import uuid

from helpers import ROOT

HAS_GRPC = importlib.util.find_spec("grpc") is not None
if HAS_GRPC:
    import grpc

    sys.path.insert(0, str(ROOT / "template/task2/client"))
    import dservice_pb2
    import dservice_pb2_grpc
    import hservice_pb2
    import hservice_pb2_grpc


@unittest.skipUnless(HAS_GRPC and shutil.which("node"), "Install Python gRPC dependencies and Node.js.")
class DelegationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for port in [50051, 50052]:
            with socket.socket() as sock:
                sock.settimeout(0.2)
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(f"Port {port} is already in use. Stop your exercise server first.")
        cls.processes = []
        cls.channels = []
        cls.logs = []
        cls.addClassCleanup(cls.cleanup)
        commands = [
            [shutil.which("node"), str(ROOT / "template/task2/dataServer/dataServer.js")],
            [sys.executable, "-u", str(ROOT / "template/task2/hashServer/server.py")],
        ]
        for command, port in zip(commands, [50051, 50052]):
            log = tempfile.TemporaryFile(mode="w+b")
            cls.logs.append(log)
            cls.processes.append(subprocess.Popen(
                command, cwd=ROOT, stdout=log, stderr=log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)))
            channel = grpc.insecure_channel(f"127.0.0.1:{port}")
            cls.channels.append(channel)
            try:
                grpc.channel_ready_future(channel).result(timeout=8)
            except grpc.FutureTimeoutError:
                log.seek(0)
                raise RuntimeError(f"Server on {port} did not start: {log.read().decode(errors='replace')}")
        cls.data = dservice_pb2_grpc.DBStub(cls.channels[0])
        cls.hash = hservice_pb2_grpc.HSStub(cls.channels[1])

    @classmethod
    def cleanup(cls):
        for channel in cls.channels:
            channel.close()
        for process in cls.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
        for log in cls.logs:
            log.close()

    def register_and_store(self, message, username=None):
        user = dservice_pb2.UserPass(username=username or uuid.uuid4().hex, password="test-password")
        self.assertTrue(self.data.RegisterUser(user, timeout=5).success)
        self.assertTrue(self.data.StoreData(dservice_pb2.StoreReq(
            username=user.username, password=user.password, msg=message), timeout=5).success)
        return user

    def request_hash(self, passcode):
        return self.hash.GetHash(hservice_pb2.Request(
            passcode=passcode, ip="127.0.0.1", port=50051), timeout=5).hash

    def test_hash_of_ascii_unicode_and_empty_text_and_one_time_use(self):
        for message in ["distributed systems", "Grüezi 🌍", ""]:
            with self.subTest(message=message):
                user = self.register_and_store(message)
                self.assertEqual(self.data.GetData(user, timeout=5).msg, message)
                passcode = self.data.GenPasscode(user, timeout=5).code
                self.assertEqual(self.request_hash(passcode), hashlib.sha256(message.encode()).hexdigest())
                self.assertEqual(self.data.GetAuthData(
                    dservice_pb2.Passcode(code=passcode), timeout=5).msg, "")

    def test_duplicate_user_and_wrong_password(self):
        user = self.register_and_store("private text")
        self.assertFalse(self.data.RegisterUser(user, timeout=5).success)
        wrong = dservice_pb2.UserPass(username=user.username, password="wrong")
        self.assertEqual(self.data.GenPasscode(wrong, timeout=5).code, "")
        self.assertFalse(self.data.StoreData(dservice_pb2.StoreReq(
            username=wrong.username, password=wrong.password, msg="overwrite"), timeout=5).success)
        self.assertEqual(self.data.GetData(wrong, timeout=5).msg, "")
        self.assertEqual(self.data.GetData(user, timeout=5).msg, "private text")

    def test_invalid_passcode_returns_empty_text_from_supplied_server(self):
        self.register_and_store("private text")
        for code in ["", "unknown-code"]:
            with self.subTest(code=code):
                self.assertEqual(self.data.GetAuthData(
                    dservice_pb2.Passcode(code=code), timeout=5).msg, "")
        with self.assertRaises(grpc.RpcError) as caught:
            self.request_hash("")
        self.assertEqual(caught.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

    def test_replacing_a_passcode_invalidates_the_previous_one(self):
        user = self.register_and_store("hello")
        old = self.data.GenPasscode(user, timeout=5).code
        new = self.data.GenPasscode(user, timeout=5).code
        self.assertNotEqual(old, new)
        self.assertEqual(self.data.GetAuthData(
            dservice_pb2.Passcode(code=old), timeout=5).msg, "")
        self.assertEqual(self.request_hash(new), hashlib.sha256(b"hello").hexdigest())

    def test_client_runs_twice_against_the_same_server(self):
        message = "client integration"
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, str(ROOT / "template/task2/client/client.py"), "--message", message],
                cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(hashlib.sha256(message.encode()).hexdigest(), result.stdout)
