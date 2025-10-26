import hashlib
import json
from time import time, sleep
from urllib.parse import urlparse
import requests
from threading import Lock

class Blockchain:
    def __init__(self, delay_seconds=180):
        self.chain = []
        self.pending_votes = []
        self.nodes = set()
        self.delay_seconds = delay_seconds
        self.lock = Lock() 
        self.new_block(previous_hash='1', proof=100)

    def new_vote(self, voter_id, candidate):
        """Tambahkan vote baru jika voter_id belum pernah memilih"""
        with self.lock:
            if self.has_voted(voter_id):
                raise ValueError("Voter ini sudah pernah memilih!")

            vote = {
                'voter_id': voter_id,
                'candidate': candidate,
                'timestamp': time()
            }
            self.pending_votes.append(vote)
            return self.last_block['index'] + 1

    def has_voted(self, voter_id):
        """Cek voter_id di chain dan pending_votes"""
        for block in self.chain:
            for vote in block['votes']:
                if vote['voter_id'] == voter_id:
                    return True
        for vote in self.pending_votes:
            if vote['voter_id'] == voter_id:
                return True
        return False

    def new_block(self, proof, previous_hash=None):
        with self.lock:
            block = {
                'index': len(self.chain) + 1,
                'timestamp': time(),
                'votes': self.pending_votes,
                'proof': proof,
                'previous_hash': previous_hash or self.hash(self.chain[-1]),
            }
            self.pending_votes = []
            self.chain.append(block)
            return block

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        proof = 0
        while not self.valid_proof(last_proof, proof):
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        return hashlib.sha256(guess).hexdigest()[:4] == "0000"

    def mine_pending_votes(self, use_delay=True, source="AUTO"):
        """Menambang semua vote yang tertunda"""
        if not self.pending_votes:
            print(" Tidak ada vote tertunda untuk ditambang.")
            return None

        if use_delay:
            print(f" [{source}] Menunggu {self.delay_seconds/60:.0f} menit sebelum menambang...")
            sleep(self.delay_seconds)

        last_block = self.last_block
        last_proof = last_block['proof']
        proof = self.proof_of_work(last_proof)

        previous_hash = self.hash(last_block)
        block = self.new_block(proof, previous_hash)

        print(f" [{source}] Blok baru berhasil ditambang! Index: {block['index']}")
        return block

    def register_node(self, address):
        parsed_url = urlparse(address)
        node_address = f"http://{parsed_url.netloc or parsed_url.path}"
        self.nodes.add(node_address)
        print(f" Node terdaftar: {node_address}")

    def valid_chain(self, chain):
        last_block = chain[0]
        for i in range(1, len(chain)):
            block = chain[i]
            if block['previous_hash'] != self.hash(last_block):
                return False
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            last_block = block
        return True

    def resolve_conflicts(self):
        new_chain = None
        max_length = len(self.chain)
        for node in self.nodes:
            try:
                r = requests.get(f"{node}/chain", timeout=5)
                if r.status_code == 200:
                    length = r.json()['length']
                    chain = r.json()['chain']
                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
            except Exception:
                continue
        if new_chain:
            with self.lock:
                self.chain = new_chain
                self.pending_votes = []
            print(" Chain diganti dengan versi yang lebih panjang.")
            return True
        return False

    def broadcast_chain(self):
        for node in self.nodes:
            try:
                requests.get(f"{node}/nodes/resolve", timeout=5)
            except Exception:
                continue
