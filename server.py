import socketserver
import time
import struct
import sys
import json
import datetime


def to_unsigned_long_long(number):
    return int(number * 2 ** 32)


def from_unsigned_long_long(number):
    return float(number) / 2 ** 32

timestamp_delta = 0


def calculate_timestamp_delta(shift):
    global timestamp_delta

    sys_gmtime = time.gmtime(0)
    sys_epoch = datetime.date(sys_gmtime.tm_year,
        sys_gmtime.tm_mon, sys_gmtime.tm_mday)
    ntp_epoch = datetime.date(1900, 1, 1)
    timestamp_delta = (sys_epoch - ntp_epoch).total_seconds() + shift


def get_timestamp():
    return time.time() + timestamp_delta


class Packet:

    def __init__(self, version=4, mode=4):
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
        self.stratum = 0
        self.format = "!3Bbi2I4Q"

    def convert_to_bytes(self):
        try:
            bytes_packet = struct.pack(
                self.format,
                self.leap << 6 | self.version << 3 | self.mode,
                self.stratum,
                self.interval,
                self.precision,
                int(self.delay * 2 ** 16),
                int(self.dispersion * 2 ** 16),
                self.ref_id,
                to_unsigned_long_long(self.last_update),
                to_unsigned_long_long(self.start_time),
                to_unsigned_long_long(self.recv_time),
                to_unsigned_long_long(self.transmit_time)
            )
        except struct.error:
            raise ValueError('Invalid SNTP packet.')
        return bytes_packet

    @staticmethod
    def get_packet_from_bytes(bytes_packet):
        packet = Packet()
        unpacked = struct.unpack(
            packet.format, bytes_packet[:struct.calcsize(packet.format)]
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
        return packet


class PacketHandler(socketserver.BaseRequestHandler):
    def handle(self):

        recv_timestamp = get_timestamp()

        print('Connected: {}'.format(self.client_address))

        data, socket = self.request

        recv_packet = Packet.get_packet_from_bytes(data)

        send_packet = Packet()
        send_packet.version = recv_packet.version
        send_packet.mode = 4
        send_packet.stratum = 2
        send_packet.start_time = recv_packet.transmit_time
        send_packet.recv_time = recv_timestamp
        send_packet.transmit_time = get_timestamp()
        print(111)
        socket.sendto(send_packet.convert_to_bytes(), self.client_address)


def main():
    if len(sys.argv[1:]) < 2:
        print("Usage: Ip Port")
        exit()
    # server_ip = sys.argv[1]
    # server_port = int(sys.argv[2])
    server_ip = "localhost"
    server_port = 123
    shift = json.load(open("config.conf"))["shift"]
    calculate_timestamp_delta(shift)
    socketserver.BaseServer.allow_reuse_address = True
    server = socketserver.UDPServer((server_ip, server_port), PacketHandler)
    server.serve_forever()

if __name__ == "__main__":
    main()