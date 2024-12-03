import socket
import time
import argparse

# import logging
import json

# Constants
MSS = 1400
INITIAL_CWND = MSS  # Initial congestion window size
INITIAL_SSTHRESH = 16 * MSS  # Initial slow start threshold
TIMEOUT = 0.5
DUP_ACK_THRESHOLD = 3
FILE_PATH = "sending_file.txt"


class TCPRenoServer:
    def __init__(self):
        self.cwnd = INITIAL_CWND
        self.ssthresh = INITIAL_SSTHRESH
        self.duplicate_acks = {}
        self.in_fast_recovery = False
        self.last_ack = 0
        self.packets_sent_in_rtt = 0
        self.acks_received_in_rtt = 0
        # logging.info(f"Initial cwnd: {self.cwnd}, ssthresh: {self.ssthresh}")

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

    def handle_timeout(self):
        # logging.info(f"Timeout occurred. Old cwnd: {self.cwnd}, ssthresh: {self.ssthresh}")
        self.ssthresh = max(self.cwnd // 2, 2 * MSS)
        self.cwnd = MSS
        self.in_fast_recovery = False
        self.packets_sent_in_rtt = 0
        self.acks_received_in_rtt = 0
        self.duplicate_acks.clear()
        # logging.info(f"After timeout - cwnd: {self.cwnd}, ssthresh: {self.ssthresh}")

    def handle_duplicate_ack(self, seq_num):
        if seq_num not in self.duplicate_acks:
            self.duplicate_acks[seq_num] = 1
            # logging.info(f"First duplicate ACK for {seq_num}")
        else:
            self.duplicate_acks[seq_num] += 1
            # logging.info(f"Duplicate ACK count for {seq_num}: {self.duplicate_acks[seq_num]}")

        if (
            self.duplicate_acks[seq_num] == DUP_ACK_THRESHOLD
            and not self.in_fast_recovery
        ):
            # logging.info(f"Triple duplicate ACK detected. Old cwnd: {self.cwnd}")
            self.ssthresh = max(self.cwnd // 2, 2 * MSS)
            self.cwnd = self.ssthresh + 3 * MSS
            self.in_fast_recovery = True
            # logging.info(f"Entering fast recovery - cwnd: {self.cwnd}, ssthresh: {self.ssthresh}")
            return True
        return False

    def handle_new_ack(self, ack_seq_num):
        # # logging.info(
        #     f"Handling new ACK {ack_seq_num}. Current cwnd: {self.cwnd}, ssthresh: {self.ssthresh}"
        # )
        # # logging.info(
        #     f"Packets sent in RTT: {self.packets_sent_in_rtt}, ACKs received: {self.acks_received_in_rtt}"
        # )

        if ack_seq_num > self.last_ack:
            if self.in_fast_recovery:
                self.cwnd = self.ssthresh
                self.in_fast_recovery = False
                self.packets_sent_in_rtt = 0
                self.acks_received_in_rtt = 0
                # logging.info(f"Exiting fast recovery - cwnd: {self.cwnd}")
            else:
                self.acks_received_in_rtt += 1

                if self.cwnd < self.ssthresh:
                    # Slow start phase
                    old_cwnd = self.cwnd
                    self.cwnd += MSS  # Increase by MSS for each ACK in slow start
                    # # logging.info(
                    #     f"Slow start - increased cwnd from {old_cwnd} to {self.cwnd}"
                    # )
                else:
                    # Congestion avoidance phase
                    old_cwnd = self.cwnd
                    self.cwnd += MSS * (
                        MSS / self.cwnd
                    )  # Increase approximately 1 MSS per RTT
                    # # logging.info(
                    #     f"Congestion avoidance - increased cwnd from {old_cwnd} to {self.cwnd}"
                    # )

            self.last_ack = ack_seq_num
            self.duplicate_acks.clear()

    def send_file(self, server_ip, server_port):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((server_ip, server_port))
        # logging.info(f"Server listening on {server_ip}:{server_port}")

        ack_packet, client_address = server_socket.recvfrom(1024)
        # logging.info(f"Client Address: {client_address}")

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
            try:
                server_socket.settimeout(TIMEOUT)
                ack_packet, _ = server_socket.recvfrom(1024)
                ack_seq_num, end = self.get_seq_no_from_ack_pkt(ack_packet)
                # logging.info(f"Received ACK: {ack_seq_num}")

                if end:
                    # logging.info("File transfer complete")
                    return

                if ack_seq_num > base_seq:
                    self.handle_new_ack(ack_seq_num)
                    base_seq = ack_seq_num
                    next_seq = max(next_seq, base_seq)
                else:
                    if self.handle_duplicate_ack(ack_seq_num):
                        next_seq = base_seq

            except socket.timeout:
                # logging.info("Timeout detected")
                self.handle_timeout()
                next_seq = base_seq
                packet_times.clear()

            # Calculate window size in terms of packets
            current_window = max(int(self.cwnd / MSS), 1)  # Ensure at least 1 packet
            window_end = min(base_seq + current_window * MSS, max_seq + MSS)

            # # logging.info(
            #     f"Current window size: {current_window} packets, cwnd: {self.cwnd}, window_end: {window_end}"
            # )

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
                    self.packets_sent_in_rtt += 1
                    # # logging.info(
                    #     f"Sent packet {next_seq}, Window: {current_window}, CWND: {self.cwnd}"
                    # )
                    next_seq += MSS
        server_socket.close()


def main():
    parser = argparse.ArgumentParser(
        description="TCP Reno server for reliable file transfer over UDP."
    )
    parser.add_argument("server_ip", help="IP address of the server")
    parser.add_argument("server_port", type=int, help="Port number of the server")

    args = parser.parse_args()
    server = TCPRenoServer()
    server.send_file(args.server_ip, args.server_port)


if __name__ == "__main__":
    main()
