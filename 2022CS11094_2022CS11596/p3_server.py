import socket
import time
import argparse
import logging
import json
import math

# Constants
MSS = 1400
INITIAL_CWND = MSS  # Initial congestion window size
INITIAL_SSTHRESH = 16 * MSS  # Initial slow start threshold
TIMEOUT = 0.5
DUP_ACK_THRESHOLD = 3
FILE_PATH = "sending_file.txt"
CUBIC_C = 0.4
CUBIC_BETA = 0.5


class TCPCubicServer:
    def __init__(self):
        self.cwnd = INITIAL_CWND
        self.ssthresh = INITIAL_SSTHRESH
        self.duplicate_acks = {}
        self.in_fast_recovery = False
        self.last_ack = 0

        # CUBIC specific variables
        self.w_max = 0  # Maximum window size before last congestion event
        self.w_last_max = 0  # Last maximum window size
        self.k = 0  # Time period that the window size of CUBIC is zero
        self.t_start = 0  # Time when recovery starts
        self.epoch_start = 0  # Beginning of current epoch
        self.origin_point = 0  # Window size at the beginning of current epoch
        # self.tcp_friendliness = True  # Enable TCP friendliness feature

    def create_packet(self, seq_num, data, start=False, end=False):
        packet = {
            "seq_num": seq_num,
            "data_length": len(data),
            "data": data,
            "start": start,
            "end": end,
        }
        json_str = json.dumps(packet)
        return json_str.encode("utf-8")

    def get_seq_no_from_ack_pkt(self, ack_packet):
        json_packet = json.loads(ack_packet.decode("utf-8"))
        return json_packet["seq_num"], json_packet["end"]

    def cubic_reset(self):
        """Reset CUBIC state variables"""
        self.w_max = 0
        self.w_last_max = 0
        self.k = 0
        self.t_start = 0
        self.epoch_start = 0
        self.origin_point = 0

    def calculate_cubic_window(self, t):
        """Calculate the CUBIC window size using W(t) = C(t-K)³ + Wmax"""
        if self.epoch_start <= 0:
            self.epoch_start = t
            self.w_max = max(self.w_max, self.cwnd)
            self.k = math.pow((self.w_max * CUBIC_BETA) / CUBIC_C, 1 / 3)
            self.origin_point = self.cwnd

        t = t - self.epoch_start
        target = self.origin_point + CUBIC_C * math.pow(t - self.k, 3)

        if target < 0:
            target = 0

        return int(target)

    def handle_timeout(self):
        """Handle timeout according to TCP CUBIC"""
        self.ssthresh = max(self.cwnd * CUBIC_BETA, MSS)
        self.cwnd = MSS
        self.w_last_max = self.w_max
        self.cubic_reset()
        self.in_fast_recovery = False

    def handle_duplicate_ack(self, seq_num):
        """Handle duplicate ACK according to TCP CUBIC"""
        if seq_num not in self.duplicate_acks:
            self.duplicate_acks[seq_num] = 1
        else:
            self.duplicate_acks[seq_num] += 1

        if (
            self.duplicate_acks[seq_num] == DUP_ACK_THRESHOLD
            and not self.in_fast_recovery
        ):
            # Enter fast recovery
            self.ssthresh = max(self.cwnd * CUBIC_BETA, MSS)
            self.cwnd = self.ssthresh + 3 * MSS
            self.w_last_max = self.w_max
            self.epoch_start = 0  # Reset epoch
            self.in_fast_recovery = True
            return True
        return False

    def handle_new_ack(self, ack_seq_num):
        """Handle new ACK according to TCP CUBIC"""
        if ack_seq_num > self.last_ack:
            if self.in_fast_recovery:
                # Exit fast recovery
                self.cwnd = max(self.ssthresh, MSS)
                self.in_fast_recovery = False
            else:
                # Update window using CUBIC function
                t = time.time()
                if self.cwnd < self.ssthresh:
                    # Slow start phase
                    self.cwnd = min(self.cwnd + MSS, self.ssthresh)
                else:
                    # Congestion avoidance with CUBIC
                    cubic_target = self.calculate_cubic_window(t)
                    self.cwnd = cubic_target

            self.last_ack = ack_seq_num
            self.duplicate_acks.clear()

    def send_file(self, server_ip, server_port):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((server_ip, server_port))

        # Wait for initial connection
        ack_packet, client_address = server_socket.recvfrom(1024)

        # Read file into memory
        file_data = {}
        seq_num = 0
        max_seq = 0
        with open(FILE_PATH, "r") as file:
            while True:
                chunk = file.read(MSS)
                if not chunk:
                    file_data[seq_num] = "EOD"
                    max_seq = seq_num
                    break
                file_data[seq_num] = chunk
                max_seq = seq_num
                seq_num += MSS

        base_seq = 0
        next_seq = 0
        packet_times = {}

        while base_seq <= max_seq:
            # Calculate current window size based on cwnd
            current_window = int(self.cwnd / MSS)
            window_end = min(base_seq + current_window * MSS, max_seq + MSS)

            # Send packets within current window
            while next_seq < window_end:
                if next_seq in file_data:
                    current_time = time.time()
                    if (
                        next_seq in packet_times
                        and current_time - packet_times[next_seq] < TIMEOUT
                    ):
                        next_seq += MSS
                        continue

                    chunk = file_data[next_seq]
                    packet = self.create_packet(next_seq, chunk, end=(chunk == "EOD"))
                    server_socket.sendto(packet, client_address)
                    packet_times[next_seq] = current_time
                    next_seq += MSS

            # Wait for ACKs
            try:
                server_socket.settimeout(TIMEOUT)
                ack_packet, _ = server_socket.recvfrom(1024)
                ack_seq_num, end = self.get_seq_no_from_ack_pkt(ack_packet)

                if end:
                    break

                if ack_seq_num > base_seq:
                    # New ACK
                    self.handle_new_ack(ack_seq_num)
                    base_seq = ack_seq_num
                    next_seq = max(next_seq, base_seq)
                else:
                    # Duplicate ACK
                    if self.handle_duplicate_ack(ack_seq_num):
                        # Fast recovery triggered - resend from base_seq
                        next_seq = base_seq

            except socket.timeout:
                self.handle_timeout()
                next_seq = base_seq  # Resend from base_seq
                packet_times.clear()

        server_socket.close()


def main():
    parser = argparse.ArgumentParser(
        description="TCP CUBIC server for reliable file transfer over UDP."
    )
    parser.add_argument("server_ip", help="IP address of the server")
    parser.add_argument("server_port", type=int, help="Port number of the server")

    args = parser.parse_args()
    server = TCPCubicServer()
    server.send_file(args.server_ip, args.server_port)


if __name__ == "__main__":
    main()
