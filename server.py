import socketserver
import time
import struct
import json

SHIFT = 0
DELTA1970_1900 = 2208988800


def to_unsigned_long_long(number):
    return int(number * 2 ** 32)


def from_unsigned_long_long(number):
    return float(number) / 2 ** 32


class Packet:
    def __init__(self, version=4, mode=4, bytes_packet=None, stratum=0):
        self.li = 0
        self.version = version
        self.mode = mode
        self.poll = 0
        self.precision = 0
        self.delay = 0
        self.dispersion = 0
        self.ref_id = 0
        self.last_update = 0
        self.start_time = 0
        self.recv_time = 0
        self.transmit_time = 0
        self.stratum = stratum
        self.format = "!3Bbi2I4Q"
        if bytes_packet:
            self.get_packet_from_bytes(bytes_packet)

    def convert_to_bytes(self):
        bytes_packet = struct.pack(
            self.format,
            self.li << 6 | self.version << 3 | self.mode,
            self.stratum,
            self.poll,
            # self.interval,
            self.precision,
            int(self.delay * 2 ** 16),
            int(self.dispersion * 2 ** 16),
            self.ref_id,
            to_unsigned_long_long(self.last_update),
            to_unsigned_long_long(self.start_time),
            to_unsigned_long_long(self.recv_time),
            to_unsigned_long_long(self.transmit_time)
        )
        return bytes_packet

    def get_packet_from_bytes(self, bytes_packet):
        packet = Packet()
        unpacked = struct.unpack(
            packet.format,
            bytes_packet[:struct.calcsize(packet.format)]
        )
        packet.li = unpacked[0] >> 6 & 3
        packet.version = unpacked[0] >> 3 & 7
        packet.mode = unpacked[0] & 7
        packet.stratum = unpacked[1]
        packet.poll = unpacked[2]
        packet.precision = unpacked[3]
        packet.delay = float(unpacked[4]) / 2 ** 16
        packet.dispersion = float(unpacked[5]) / 2 ** 16
        packet.ref_id = unpacked[6]
        packet.last_update = from_unsigned_long_long(unpacked[7])
        packet.start_time = from_unsigned_long_long(unpacked[8])
        packet.recv_time = from_unsigned_long_long(unpacked[9])
        packet.transmit_time = from_unsigned_long_long(unpacked[10])


class Server(socketserver.BaseRequestHandler):
    def handle(self):
        recv_time = time.time() + SHIFT + DELTA1970_1900
        bytes_packet, socket = self.request
        recv_packet = Packet(bytes_packet=bytes_packet)

        send_packet = Packet(stratum=2)
        send_packet.start_time = recv_packet.transmit_time
        send_packet.recv_time = recv_time
        send_packet.transmit_time = time.time() + SHIFT + DELTA1970_1900
        socket.sendto(send_packet.convert_to_bytes(), self.client_address)


def main():
    global SHIFT
    server_ip = "127.0.0.1"
    server_port = 5000
    SHIFT = json.load(open("config.conf"))["shift"]
    socketserver.BaseServer.allow_reuse_address = True
    server = socketserver.UDPServer((server_ip, server_port), Server)
    server.serve_forever()

if __name__ == "__main__":
    main()
