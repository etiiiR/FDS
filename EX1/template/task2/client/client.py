"""Client for the Task 2 delegation scenario."""

import argparse
import uuid

import grpc
import dservice_pb2
import dservice_pb2_grpc
import hservice_pb2
import hservice_pb2_grpc

RPC_TIMEOUT = 5.0


def run(username, password, message):
    with grpc.insecure_channel("127.0.0.1:50051") as data_channel:
        data_stub = dservice_pb2_grpc.DBStub(data_channel)

        registered = data_stub.RegisterUser(
            dservice_pb2.UserPass(username=username, password=password),
            timeout=RPC_TIMEOUT,
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
            ),
            timeout=RPC_TIMEOUT,
        )
        if not stored.success:
            raise RuntimeError("The data server rejected the data.")

        passcode = data_stub.GenPasscode(
            dservice_pb2.UserPass(username=username, password=password),
            timeout=RPC_TIMEOUT,
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
            ),
            timeout=RPC_TIMEOUT,
        )

    print(f"SHA-256: {result.hash}")
    return result.hash


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Task 2 gRPC client")
    parser.add_argument("--username", default=f"task2-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--password", default="task2-password")
    parser.add_argument("--message", default="Hello from the gRPC client")
    args = parser.parse_args()
    try:
        run(args.username, args.password, args.message)
    except grpc.RpcError as error:
        parser.exit(1, f"RPC failed ({error.code().name}): {error.details()}\n")
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")
