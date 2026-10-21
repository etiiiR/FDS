"""Hash server for Task 2.

The hash server receives a one-time passcode, asks the data server for the
delegated data, and returns the SHA-256 hash of that data.
"""

from concurrent import futures
import hashlib

import grpc

import dservice_pb2
import dservice_pb2_grpc
import hservice_pb2
import hservice_pb2_grpc

RPC_TIMEOUT = 5.0


class HashService(hservice_pb2_grpc.HSServicer):
    def GetHash(self, request, context):
        if not request.passcode or not request.ip or not 1 <= request.port <= 65535:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Provide a passcode, data-server IP, and port between 1 and 65535.",
            )
        data_address = f"{request.ip}:{request.port}"

        try:
            with grpc.insecure_channel(data_address) as channel:
                data_stub = dservice_pb2_grpc.DBStub(channel)
                response = data_stub.GetAuthData(
                    dservice_pb2.Passcode(code=request.passcode),
                    timeout=RPC_TIMEOUT,
                )
        except grpc.RpcError as error:
            context.abort(error.code(), error.details())

        digest = hashlib.sha256(response.msg.encode("utf-8")).hexdigest()
        return hservice_pb2.Response(hash=digest)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    hservice_pb2_grpc.add_HSServicer_to_server(HashService(), server)
    if server.add_insecure_port("127.0.0.1:50052") == 0:
        raise RuntimeError("Could not bind the hash server to port 50052.")
    server.start()
    print("Hash server listening on port 50052", flush=True)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop(grace=1).wait()


if __name__ == "__main__":
    serve()
