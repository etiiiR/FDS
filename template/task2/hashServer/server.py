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


class HashService(hservice_pb2_grpc.HSServicer):
    def GetHash(self, request, context):
        data_address = f"{request.ip}:{request.port}"

        try:
            with grpc.insecure_channel(data_address) as channel:
                data_stub = dservice_pb2_grpc.DBStub(channel)
                response = data_stub.GetAuthData(
                    dservice_pb2.Passcode(code=request.passcode)
                )
        except grpc.RpcError as error:
            context.abort(grpc.StatusCode.UNAVAILABLE, str(error))

        digest = hashlib.sha256(response.msg.encode("utf-8")).hexdigest()
        return hservice_pb2.Response(hash=digest)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    hservice_pb2_grpc.add_HSServicer_to_server(HashService(), server)
    server.add_insecure_port("[::]:50052")
    server.start()
    print("Hash server listening on port 50052")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
