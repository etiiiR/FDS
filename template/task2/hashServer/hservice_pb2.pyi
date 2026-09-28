from google.protobuf.message import Message


class Response(Message):
    hash: str

    def __init__(self, *, hash: str = ...) -> None: ...


class Request(Message):
    passcode: str
    ip: str
    port: int

    def __init__(
        self,
        *,
        passcode: str = ...,
        ip: str = ...,
        port: int = ...,
    ) -> None: ...
