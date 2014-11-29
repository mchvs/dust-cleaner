#!/usr/bin/python

#
# dust-cleaner.py - p2pool dust cleaner
# groups small 'dust' transactions with zero or minimal fee
#

COIN_NAME = "myriadcoin"
COIN_CODE = "MYR"
COIN_RPC_PORT = "10889"
FREE_BLOCK_SIZE = 1000
FREE_PRIORITY_THRESHOLD = 0.576
FEE_PER_BLOCK = 0.0001
MAX_STANDARD_TX_SIZE = 100000

from operator import itemgetter
import argparse
import json
import os.path
import requests
import sys

def get_rpc_connection_url(args):
    if not args.rpc_url:
        args.rpc_url = "localhost:" + COIN_RPC_PORT

    if (not args.rpc_user) or (not args.rpc_password):
        args.rpc_user     = None
        args.rpc_password = None

        file_data = {}
        file = open(os.path.join(os.path.expanduser("~"), "." + COIN_NAME, COIN_NAME + ".conf"), "r")
        for line in file:
            data = line.split("=")
            file_data[data[0].strip()] = data[1].strip()
        file.close()

        if file_data["rpcuser"]:
            args.rpc_user = file_data["rpcuser"]

        if file_data["rpcpassword"]:
            args.rpc_password = file_data["rpcpassword"]

    if args.https:
        url_prefix = "https://"
    else:
        url_prefix = "http://"

    return url_prefix + args.rpc_user + ":" + args.rpc_password + "@" + args.rpc_url

def get_cheap_tx(ctx, ignore_list, max_fee = 0):
    accepted_tx = []
    rejected_tx = []

    work_ctx = []
    for i in range(len(ctx)):
        tx = ctx[i]
        if tx["address"] not in ignore_list:
            tx["priority"] = tx["amount"] * tx["confirmations"]
            work_ctx.append(tx)
    work_ctx = sorted(work_ctx, key=itemgetter("priority"))

    tx_size_bytes = 10 + 34
    tx_amount = 0
    tx_weight = 0
    tx_fee = 0

    while work_ctx:
      tx = work_ctx.pop()

      next_tx_size_bytes = tx_size_bytes + 180
      next_tx_amount     = tx_amount + tx["amount"]
      next_weight        = tx_weight + tx["priority"]

      if (next_tx_size_bytes < FREE_BLOCK_SIZE):
          next_fee = 0
      elif (next_weight / next_tx_size_bytes > FREE_PRIORITY_THRESHOLD):
          next_fee = int(next_tx_size_bytes / FREE_BLOCK_SIZE) * FEE_PER_BLOCK + FEE_PER_BLOCK

      if (next_fee > max_fee) or (next_tx_size_bytes > MAX_STANDARD_TX_SIZE):
          rejected_tx.append(tx)
      else:
          accepted_tx.append(tx)
          tx_fee        = next_fee
          tx_size_bytes = next_tx_size_bytes
          tx_amount     = next_tx_amount
          tx_weight     = next_weight

    return {"accepted_tx": accepted_tx, "tx_fee": tx_fee, "tx_amount": tx_amount, "tx_size_bytes": tx_size_bytes, "rejected_tx": rejected_tx}

def create_json_tx(tx_list, pay_to, tx_amount, fee):
    work_tx_list = list(tx_list)
    tx_out_list = []
    while work_tx_list:
      tx = work_tx_list.pop()
      tx_out_list.append({"txid": tx["txid"], "vout": tx["vout"]})
    return [tx_out_list, {pay_to: tx_amount - fee}]

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description = "Joins 'dust' received payments into a manageable new bigger payment to the given address, with minimal transaction fee.")
    parser.add_argument("address", help = "The MYR address to send the aggregated payments.")
    parser.add_argument("-f", "--max_fee", help = "The maximum transaction fee allowed. Creates transaction with no fees if omitted.", type = float)
    parser.add_argument("-i", "--ignore", help = "Address not to be included in the new transaction. \"address\" is always ignored. Can be called multiple times for more than one address.", action = "append")
    parser.add_argument("-o", "--rpc_url", help = "The wallet RPC URL. Default: localhost:" + COIN_RPC_PORT + ".")
    parser.add_argument("-u", "--rpc_user", help = "The RPC username. Reads from local config file if either -u or -p are omitted.")
    parser.add_argument("-p", "--rpc_password", help = "The RPC password. Reads from local config file if either -u or -p are omitted.")
    parser.add_argument("-s", "--https", help = "Use HTTPS instead of HTTP for the RPC calls.", action = "store_true")
    parser.add_argument("-g", "--go", help = "Attempts to send transaction to the network. Runs in test mode if omitted.", action = "store_true")
    args = parser.parse_args()

    if not args.max_fee:
        args.max_fee = 0

    if args.ignore:
        args.ignore.append(args.address)
    else:
        args.ignore = [args.address]

    url = get_rpc_connection_url(args)

    headers = {"content-type": "application/json"}
    payload = {
        "method": "listunspent",
        "params": [],
        "jsonrpc": "2.0",
        "id": 0,
    }

    try:
        response = requests.post(url, data = json.dumps(payload), headers = headers).json()
    except:
        sys.exit("Failed to retrieve the list of transactions from the wallet. Execution aborted.")

    best_match = get_cheap_tx(response["result"], args.ignore, args.max_fee)

    print
    print "Dust cleaning:"
    print "- Number of transactions:", len(best_match["accepted_tx"])
    print "- Transaction fee:", best_match["tx_fee"], COIN_CODE
    print "- Dust to collect:", best_match["tx_amount"] - best_match["tx_fee"], COIN_CODE
    print

    if not args.go:
        print "Test mode. Run with --go to actually collect the dust payments."
        print "Execution aborted."
    else:
        try:
            print "Preparing transaction."
            tz = create_json_tx(best_match["accepted_tx"], args.address, best_match["tx_amount"], best_match["tx_fee"], )
            payload = {
                "method": "validateaddress",
                "params": [args.address],
                "jsonrpc": "2.0",
                "id": 0,
            }
            response = requests.post(url, data = json.dumps(payload), headers = headers).json()

            if response["result"]["isvalid"] == "False":
                print "Invalid " + COIN_NAME + " address."
                exit()

            payload = {
                "method": "createrawtransaction",
                "params": tz,
                "jsonrpc": "2.0",
                "id": 0,
            }
            response = requests.post(url, data = json.dumps(payload), headers = headers).json()

            payload = {
                "method": "signrawtransaction",
                "params": [response["result"]],
                "jsonrpc": "2.0",
                "id": 0,
            }
            response = requests.post(url, data = json.dumps(payload), headers = headers).json()

            payload = {
                "method": "sendrawtransaction",
                "params": [response["result"]["hex"]],
                "jsonrpc": "2.0",
                "id": 0,
            }
            response = requests.post(url, data = json.dumps(payload), headers = headers).json()

            print "Dust collected."
        except:
            sys.exit("Failed to connect to the wallet and send the transaction. Execution aborted.")

# ~
