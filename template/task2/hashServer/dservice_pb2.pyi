from google.protobuf.message import Message


class Result(Message):
    success: bool

    def __init__(self, *, success: bool = ...) -> None: ...


class Data(Message):
    msg: str

    def __init__(self, *, msg: str = ...) -> None: ...


class StoreReq(Message):
    username: str
    password: str
    msg: str

    def __init__(
        self,
        *,
        username: str = ...,
        password: str = ...,
        msg: str = ...,
    ) -> None: ...


class Passcode(Message):
    code: str

    def __init__(self, *, code: str = ...) -> None: ...


class UserPass(Message):
    username: str
    password: str

    def __init__(
        self,
        *,
        username: str = ...,
        password: str = ...,
    ) -> None: ...
