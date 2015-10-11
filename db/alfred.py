#!/usr/bin/python3

import socket
import gzip
from struct import Struct
from random import randint

CONFIG = {
	"api_url": "http://monitoring.freifunk-franken.de/api/alfred"
}

alfred_tlv = Struct("!BBH")
# type
# version
# length

alfred_request_v0 = Struct("!%isBH" % alfred_tlv.size)
# (alfred_tlv) header
# requested_type
# tx_id

alfred_transaction_mgmt = Struct("!HH")
# id
# seqno

ETH_ALEN = 6
mac_address = Struct("!%iB" % ETH_ALEN)

alfred_data = Struct("!%is%is" % (ETH_ALEN, alfred_tlv.size))
# (mac_address) source
# (alfred_tlv) header
# data[0]

alfred_push_data_v0 = Struct("!%is%is" % (alfred_tlv.size, alfred_transaction_mgmt.size))
# (alfred_tlv) header
# (alfred_transaction_mgmt) txm
# (alfred_data) data[0]

class AlfredPacketType(object):
	ALFRED_PUSH_DATA = 0
	ALFRED_ANNOUNCE_MASTER = 1
	ALFRED_REQUEST = 2
	ALFRED_STATUS_TXEND = 3
	ALFRED_STATUS_ERROR = 4

ALFRED_VERSION = 0


def get_alfred_socket():
	client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	client.connect("/var/run/alfred.sock")
	return client

def send_data(data_type, data):
	"""
	Args:
		data_type (int)
		data (string)
	"""
	client = get_alfred_socket()

	data = data.encode("UTF-8")
	data_tlv = alfred_tlv.pack(data_type, ALFRED_VERSION, len(data))
	# ALFRED server will fill this field
	source = mac_address.pack(*[0]*ETH_ALEN)
	pkt_data = alfred_data.pack(source, data_tlv) + data

	request_id = randint(0, 65535)
	seq_id = 0
	txm = alfred_transaction_mgmt.pack(request_id, seq_id)
	tlv = alfred_tlv.pack(AlfredPacketType.ALFRED_PUSH_DATA, ALFRED_VERSION, len(pkt_data) + len(txm))
	pkt_push_data = alfred_push_data_v0.pack(tlv, txm) + pkt_data

	client.send(pkt_push_data)
	client.close()

def request_data(data_type):
	"""
	Args:
		data_type (int)

	Returns:
		data (string)
	"""
	client = get_alfred_socket()

	header = alfred_tlv.pack(AlfredPacketType.ALFRED_REQUEST, ALFRED_VERSION, alfred_request_v0.size - alfred_tlv.size)
	request_id = randint(0, 65535)
	request = alfred_request_v0.pack(header, data_type, request_id)

	client.send(request)

	response = {}

	last_seq_id = -1
	while True:
		tlv = client.recv(alfred_tlv.size)
		if len(tlv) < alfred_tlv.size:
			# no (more) data available
			break
		assert len(tlv) == alfred_tlv.size

		res_type, res_version, res_length = alfred_tlv.unpack(tlv)
		assert res_type == AlfredPacketType.ALFRED_PUSH_DATA
		assert res_version == ALFRED_VERSION

		push = tlv + client.recv(alfred_push_data_v0.size - alfred_tlv.size)
		assert len(push) == alfred_push_data_v0.size
		res_length -= (alfred_push_data_v0.size - alfred_tlv.size)

		# check transaction_id and sequence_id
		tlv, txm = alfred_push_data_v0.unpack(push)
		trx_id, seq_id = alfred_transaction_mgmt.unpack(txm)
		assert seq_id > last_seq_id
		last_seq_id = seq_id
		assert trx_id == request_id

		while res_length > 0:
			data = client.recv(alfred_data.size)
			assert len(data) == alfred_data.size
			res_length -= alfred_data.size

			source, data_tlv = alfred_data.unpack(data)

			mac = ":".join(["%02x" % i for i in mac_address.unpack(source)])

			data_type_recv, data_version, data_length = alfred_tlv.unpack(data_tlv)
			assert data_type == data_type_recv

			payload = client.recv(data_length)
			assert len(payload) == data_length
			res_length -= data_length

			try:
				payload = gzip.decompress(payload)
			except:
				pass

			# decode string (expect unicode)
			payload = payload.decode("UTF-8", errors="replace")

			if mac in response:
				response[mac] += payload
			else:
				response[mac] = payload

	client.close()
	return response

if __name__ == "__main__":
	import sys
	import requests
	if len(sys.argv) > 1 and sys.argv[1] == "client":
		if len(sys.argv) > 3:
			push_data_type = int(sys.argv[2])
			data = sys.argv[3]
			send_data(push_data_type, data)
		elif len(sys.argv) > 2:
			req_data_type = int(sys.argv[2])
			data = request_data(req_data_type)
			print(data)
	elif len(sys.argv) > 1:
		# send all updated data to HTTP server and send response to ALFRED
		for i in sys.argv[1:]:
			req_data_type = int(i)
			data = {req_data_type: request_data(req_data_type)}
			response = requests.post(CONFIG["api_url"], json=data).json()
			for data_type, data in response.items():
				send_data(int(data_type), data)
	else:
		print("Get: %s client DATA_TYPE" % sys.argv[0])
		print("Set: %s client DATA_TYPE VALUE)" % sys.argv[0])
		print("Proxy: %s DATA_TYPE_1 [DATA_TYPE_N])" % sys.argv[0])
