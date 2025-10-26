import os

NODE_PORT = int(os.getenv("NODE_PORT", 5001))

NODE_NAME = os.getenv("NODE_NAME", f"node{NODE_PORT - 5000}")

ALL_NODES = [
    "http://node1:5001",
    "http://node2:5002",
    "http://node3:5003",
    "http://node4:5004"
]
