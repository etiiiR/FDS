"""Client for the Task 2 delegation scenario."""

import argparse

import grpc
import dservice_pb2
import dservice_pb2_grpc
import hservice_pb2
import hservice_pb2_grpc


def run(username, password, message):
    with grpc.insecure_channel("127.0.0.1:50051") as data_channel:
        data_stub = dservice_pb2_grpc.DBStub(data_channel)

        registered = data_stub.RegisterUser(
            dservice_pb2.UserPass(username=username, password=password)
        )
        if not registered.success:
            raise RuntimeError(
                "Registration failed. Choose a new username or remove the old "
                "data-server process."
            )

        stored = data_stub.StoreData(
            dservice_pb2.StoreReq(
                username=username,
                password=password,
                msg=message,
            )
        )
        if not stored.success:
            raise RuntimeError("The data server rejected the data.")

        passcode = data_stub.GenPasscode(
            dservice_pb2.UserPass(username=username, password=password)
        ).code

    if not passcode:
        raise RuntimeError("The data server did not issue a passcode.")

    with grpc.insecure_channel("127.0.0.1:50052") as hash_channel:
        hash_stub = hservice_pb2_grpc.HSStub(hash_channel)
        result = hash_stub.GetHash(
            hservice_pb2.Request(
                passcode=passcode,
                ip="127.0.0.1",
                port=50051,
            )
        )

    print(f"SHA-256: {result.hash}")
    return result.hash


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Task 2 gRPC client")
    parser.add_argument("--username", default="task2-user")
    parser.add_argument("--password", default="task2-password")
    parser.add_argument("--message", default="Hello from the gRPC client")
    args = parser.parse_args()
    run(args.username, args.password, args.message)
