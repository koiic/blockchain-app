import json
import time

import requests
from flask import Flask, request
# Initialize flask application
from blockchain import Block, BlockChain

api = Flask(__name__)

# initialize a blockchain object
new_blockchain = BlockChain()

# Node in the blockchain network that our application will communicate with
# to fetch and add data.
CONNECTED_NODE_ADDRESS = "http://127.0.0.1:8000"

posts = []


# Flask's way of declaring end-points
@api.route('/new_transaction', methods=['POST'])
def new_transaction():
    trans_data = request.get_json()
    required_field = ['authors', 'content']
    for field in required_field:
        if not trans_data.get(field):
            return json.dumps({'error': 'Invalid transaction data'}), 404

    trans_data['timestamp'] = time.time()
    new_blockchain.add_new_transaction(trans_data)
    return json.dumps({
        'status': 'success'
    }), 200


@api.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in new_blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({
        "length": len(chain_data),
        "chain": chain_data
    })


@api.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = new_blockchain.mine()
    if not result:
        return 'No transactions to mine'
    else:
        # Making sure we have the longest chain before announcing to the network
        chain_length = len(new_blockchain.chain)
        consensus()
        if chain_length == len(new_blockchain.chain):
            # announce the recently mined block to the network
            announce_new_block(new_blockchain.last_block)
    return f'Block #{new_blockchain.last_block.index} is mined.'


@api.route('/pending_tx')
def get_pending_transactions():
    return json.dumps(new_blockchain.unconfirmed_transactions)


# Establish consensus and decentralization

# Contains the host addresses of other participating members of the network
peers = set()


# Endpoint to add new peers to the network
@api.route('/register_node', methods=['POST'])
def register_new_peers():
    # The host address to the peer node
    node_address = request.get_json()['node_address']
    if not node_address:
        return "Invalid data", 400

    # Add node to peer list
    peers.add(node_address)

    # Return the blockchain to the newly registered node so that it can sync
    return get_chain()


def create_chain_from_dump(chain_dump):
    blockchain = BlockChain()
    for index, block_data in enumerate(chain_dump):
        block = Block(
            block_data["index"],
            block_data["transactions"],
            block_data["timestamp"],
            block_data["previous_hash"]
        )
        proof = block_data["hash"]
        if index > 0:
            added = blockchain.add_block(block, proof)
            if not added:
                raise Exception("The chain dump is tampered!!")
            else:  # the block is a genesis block, no verification needed
                blockchain.chain.append(block)
    return blockchain

    pass


@api.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Internally calls the `register_node` endpoint to
    register current node with the remote node specified in the
    request, and sync the blockchain as well with the remote node.
    """
    node_address = request.get_json()['node_address']
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # Make a request to register with remote node and obtain information
    response = requests.post(f'{node_address}/register_node', data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global new_blockchain
        global peers
        # update chain and peers
        chain_dump = response.json()['chain']
        new_blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code


# endpoint to add a block mined by someone else to
# the node's chain. The node first verifies the block
# and then adds it to the chain.
@api.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data['index'],
                  block_data['transaction'],
                  block_data['timestamp'],
                  block_data['previous_hash']
                  )
    proof = block_data['hash']
    added = new_blockchain.add_block(block, proof)

    if not added:
        return 'The block was discarded by the node', 400

    return 'Block added to the chain ', 201


def consensus():
    """
    Our simple consensus algorithm. If a longer valid chain is
    found, our chain is replaced with it.
    """
    global new_blockchain

    longest_chain = None
    current_len = len(new_blockchain.chain)

    for node in peers:
        response = requests.get('{}/chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and new_blockchain.check_chain_validation(chain):
            # Longer valid chan found!
            current_len = length
            longest_chain = chain

    if longest_chain:
        new_blockchain = longest_chain
        return True
    return False


def announce_new_block(block):
    """
       A function to announce to the network once a block has been mined.
       Other blocks can simply verify the proof of work and add it to their
       respective chains.
    """
    for peer in peers:
        url = f'{peer}/add_block'
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True))

