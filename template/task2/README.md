# Task 2: gRPC and Protocol Buffers

The exercise uses three local processes:

- data server: Node.js on port `50051`
- hash server: Python on port `50052`
- client: Python, which runs the complete scenario

## Install

```text
cd template/task2
python -m pip install -r requirements.txt
cd dataServer
npm install
cd ..
python generate_stubs.py
```

## Run

Open three terminals, all from `template/task2`:

```text
node dataServer/dataServer.js
python hashServer/server.py
python client/client.py --message "distributed systems"
```

The client prints the SHA-256 hash returned by the hash server. The passcode is
one-time use: the hash server consumes it when it calls `GetAuthData`.
