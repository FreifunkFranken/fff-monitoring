#!/usr/bin/python

import socket
import gzip
from struct import Struct
from random import randint
from enum import IntEnum

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
# (alfred_transaction_mgmt) tx
# (alfred_data) data[0]

class AlfredPacketType(IntEnum):
	ALFRED_PUSH_DATA = 0
	ALFRED_ANNOUNCE_MASTER = 1
	ALFRED_REQUEST = 2
	ALFRED_STATUS_TXEND = 3
	ALFRED_STATUS_ERROR = 4

ALFRED_VERSION = 0

def request_data(data_type):
	client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	client.connect("/var/run/alfred.sock")

	header = alfred_tlv.pack(AlfredPacketType.ALFRED_REQUEST, ALFRED_VERSION, alfred_request_v0.size - alfred_tlv.size)
	request_id = randint(0, 65535)
	request = alfred_request_v0.pack(header, data_type, request_id)

	client.send(request)

	response = {}

	last_seq_id = -1
	while True:
		tlv = client.recv(alfred_tlv.size)
		# exit loop on 2nd run without error when reaching end of data
		if last_seq_id > -1 and len(tlv) < alfred_tlv.size:
			break
		assert len(tlv) == alfred_tlv.size

		res_type, res_version, res_length = alfred_tlv.unpack(tlv)
		res_type = AlfredPacketType(res_type)
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

			data_type, data_version, data_length = alfred_tlv.unpack(data_tlv)

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
	if len(sys.argv) > 1:
		req_data_type = int(sys.argv[1])
		print(request_data(req_data_type))
	else:
		print("Usage: %s DATA_TYPE (eg. 64)" % sys.argv[0])
