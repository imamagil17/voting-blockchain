from flask import Flask, jsonify, request
from flask_cors import CORS
from uuid import uuid4
import requests
from threading import Thread
import time
from blockchain import Blockchain
from config import NODE_PORT, NODE_NAME, ALL_NODES

app = Flask(__name__)
CORS(app)

node_identifier = str(uuid4()).replace("-", "")
blockchain = Blockchain(delay_seconds=180)

def auto_register_nodes():
    print(f"🔗 [Auto-Register] Node ini: {NODE_NAME}:{NODE_PORT}")
    for node in ALL_NODES:
        if f":{NODE_PORT}" in node:
            continue
        try:
            requests.post(f"{node}/nodes/register", json={"nodes": [f"http://{NODE_NAME}:{NODE_PORT}"]}, timeout=2)
            blockchain.register_node(node)
        except Exception:
            continue

Thread(target=auto_register_nodes, daemon=True).start()

def broadcast_vote(voter_id, candidate):
    for node in blockchain.nodes:
        try:
            requests.post(f"{node}/vote/receive", json={"voter_id": voter_id, "candidate": candidate}, timeout=2)
        except Exception:
            continue

def auto_mine():
    global is_mining
    if is_mining:
        print(" [AUTO-MINE] Sudah ada proses mining yang berjalan, lewati.")
        return
    is_mining = True

    print(" [AUTO-MINE] Menunggu 3 menit sebelum menambang...")
    time.sleep(blockchain.delay_seconds)
    if blockchain.pending_votes:
        print(" [AUTO-MINE] Menambang vote yang tertunda...")
        block = blockchain.mine_pending_votes(source="AUTO")
        if block:
            print(" [AUTO-MINE] Blok baru berhasil ditambang otomatis!")
            blockchain.broadcast_chain()
    else:
        print("⏹️ [AUTO-MINE] Tidak ada vote yang tertunda.")
    is_mining = False

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Blockchain Voting Node aktif",
        "node_id": node_identifier,
        "port": NODE_PORT,
        "nodes_terdaftar": list(blockchain.nodes)
    })

@app.route("/vote", methods=["POST"])
def new_vote():
    values = request.get_json()
    if not all(k in values for k in ["voter_id", "candidate"]):
        return jsonify({"message": "Data tidak lengkap"}), 400

    voter_id = values["voter_id"]
    candidate = values["candidate"]

    try:
        index = blockchain.new_vote(voter_id, candidate)
    except ValueError as e:
        return jsonify({"message": str(e)}), 400

    Thread(target=broadcast_vote, args=(voter_id, candidate), daemon=True).start()

    if len(blockchain.pending_votes) == 1:
        Thread(target=auto_mine, daemon=True).start()

    return jsonify({"message": f"Vote diterima dan akan dimasukkan ke blok {index} dalam 3 menit."}), 201

@app.route("/vote/receive", methods=["POST"])
def receive_vote():
    values = request.get_json()
    voter_id = values["voter_id"]
    candidate = values["candidate"]

    try:
        blockchain.new_vote(voter_id, candidate)
    except ValueError as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"message": "Vote diterima"}), 201

@app.route("/mine", methods=["GET"])
def mine():
    block = blockchain.mine_pending_votes(use_delay=False, source="MANUAL")
    if block:
        blockchain.broadcast_chain()
        return jsonify({
            "message": "Blok baru telah ditambang secara manual!",
            "index": block['index'],
            "votes": block['votes']
        }), 200
    return jsonify({"message": "Tidak ada vote untuk ditambang."}), 200


@app.route("/chain", methods=["GET"])
def full_chain():
    return jsonify({
        "node_name": NODE_NAME,
        "port": NODE_PORT,
        "chain": blockchain.chain,
        "length": len(blockchain.chain)
    }), 200

@app.route("/status", methods=["GET"])
def status():
    last_block = blockchain.last_block
    last_hash = blockchain.hash(last_block)
    all_synced = True
    for node in blockchain.nodes:
        try:
            r = requests.get(f"{node}/chain", timeout=2)
            if r.status_code == 200 and r.json()["length"] != len(blockchain.chain):
                all_synced = False
                break
        except Exception:
            all_synced = False
            break

    return jsonify({
        "node_port": NODE_PORT,
        "chain_length": len(blockchain.chain),
        "last_hash": last_hash,
        "connected_nodes": list(blockchain.nodes),
        "all_nodes_synced": all_synced
    }), 200

@app.route("/results", methods=["GET"])
def results():
    results = {}
    for block in blockchain.chain:
        for vote in block["votes"]:
            candidate = vote["candidate"]
            results[candidate] = results.get(candidate, 0) + 1

    return jsonify({
        "total_votes": sum(results.values()),
        "results": results
    }), 200

@app.route("/nodes/register", methods=["POST"])
def register_nodes():
    values = request.get_json()
    nodes = values.get("nodes")
    if nodes is None:
        return jsonify({"message": "Daftar node tidak valid"}), 400

    for node in nodes:
        blockchain.register_node(node)

    return jsonify({
        "message": "Node baru telah ditambahkan.",
        "total_nodes": list(blockchain.nodes)
    }), 201

@app.route("/nodes/resolve", methods=["GET"])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        return jsonify({
            "message": "Chain telah digantikan oleh versi yang lebih panjang.",
            "new_chain": blockchain.chain
        }), 200
    return jsonify({
        "message": "Chain sudah versi terbaru.",
        "chain": blockchain.chain
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=NODE_PORT)
