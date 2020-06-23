import json
import time
from hashlib import sha256

import requests


class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce):
        """
        Constructor  for the `Block` class
        :param index: Unique ID for the block
        :param transactions: List of transactions
        :param timestamp: Time of generation of block
    `   :param previous_hash: Hash of the previous block in the chain which this block is part of.
        """
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self):
        """
        :return: hash of the block instance by first converting it into JSON string
        """
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


class BlockChain:
    # difficulty of PoW algorithm
    difficulty = 2

    def __init__(self):
        """
        Constructor for the `BlockChain` class.
        """
        self.unconfirmed_transactions = []
        self.chain = []
        self.create_genesis_block()

    def create_genesis_block(self):
        """
         A function to generate genesis block and appends it to
        the chain. The block has index 0, previous_hash as 0, and
        a valid hash.
        :return: None
        """
        genesis_block = Block(0, [], time.time(), '0', 0)
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        """
         A quick pythonic way to retrieve the most recent block in the chain. Note that
        the chain will always consist of at least one block (i.e., genesis block)
        :return: last block in blockchain
        """
        return self.chain[-1]

    def proof_of_work(self, block):
        """
        Function that tries different values of the nonce to get a hash
        that satisfies our difficulty criteria.
        :param block: the block to add nonce to
        :return:
        """
        block.nonce = 0
        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * BlockChain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return computed_hash

    def add_block(self, block, proof):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of a latest block
          in the chain match.
        :param block: the new block to add
        :param proof: the proof of work
        :return: boolean
        """
        previous_hash = self.last_block.hash
        if previous_hash != block.previous_hash:
            return False

        if not BlockChain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        :param block:
        :param block_hash:
        :return:
        """
        return (block_hash.startswith('0' * BlockChain.difficulty) and
                block_hash == block.compute_hash)

    def add_new_transaction(self, transaction):
        print(transaction)
        self.unconfirmed_transactions.append(transaction)
        print(self.unconfirmed_transactions, '____>>>>')

    def mine(self):
        """
        This function serves as an interface to add the pending
        transactions to the blockchain by adding them to the block
        and figuring out proof of work.
        :return:
        """
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block
        new_block = Block(
            index=last_block.index + 1,
            transactions=self.unconfirmed_transactions,
            timestamp=time.time(),
            previous_hash=last_block.hash,
            nonce=0
        )

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)
        self.unconfirmed_transactions = []
        return new_block.index

    @classmethod
    def check_chain_validation(cls, chain):
        """
        A helper method to check if the entire blockchain is valid.
        :param chain:
        :return:
        """
        result = True
        previous_hash = 0
        # Iterate through each block
        for block in chain:
            block_hash = block.hash
            # remove the hash field to compute the hash again
            # using `compute_hash` method
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block.hash) or previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, previous_hash
        return True
