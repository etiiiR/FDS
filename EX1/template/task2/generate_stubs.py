"""Generate Python gRPC modules from the two protobuf definitions."""

from pathlib import Path
from grpc_tools import protoc


ROOT = Path(__file__).parent

for directory in (ROOT / "client", ROOT / "hashServer"):
    result = protoc.main(
        [
            "grpc_tools.protoc",
            f"-I{directory}",
            f"--python_out={directory}",
            f"--grpc_python_out={directory}",
            str(directory / "dservice.proto"),
            str(directory / "hservice.proto"),
        ]
    )
    if result != 0:
        raise SystemExit(result)
