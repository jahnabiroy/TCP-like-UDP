import socket
import argparse
import logging
import json
from collections import defaultdict

# Constants
MSS = 1400
TIMEOUT = 2
OUTPUT_FILE = "received_file.txt"
BUFFER_SIZE = MSS + 200  # Allow room for headers

# logging.basicConfig(filename='client_2.log', level=logging.INFO, filemode='w', format='%(levelname)s - %(message)s')


class TCPRenoClient:
    def __init__(self):
        self.expected_seq_num = 0
        self.buffer = {}  # Buffer for out-of-order packets
        self.duplicate_ack_count = defaultdict(int)

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

    def parse_packet(self, packet):
        json_packet = json.loads(packet.decode("utf-8"))
        return json_packet["seq_num"], json_packet["data"], json_packet["end"]

    def send_ack(self, client_socket, server_address, seq_num):
        """Send cumulative acknowledgment"""
        if seq_num == -1:
            ack_packet = self.create_packet(-1, "", start=False, end=True)
        else:
            ack_packet = self.create_packet(seq_num, "")
        client_socket.sendto(ack_packet, server_address)
        # logging.info(f"Sent ACK for sequence number {seq_num}")

    def process_buffered_packets(self, file):
        """Process any buffered packets that are now in order"""
        while self.expected_seq_num in self.buffer:
            data = self.buffer.pop(self.expected_seq_num)
            file.write(data)
            # logging.info(f"Writing buffered packet {self.expected_seq_num} to file")
            self.expected_seq_num += MSS

    def receive_file(self, server_ip, server_port, output_file):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(TIMEOUT)
        server_address = (server_ip, server_port)
        # logging.info(f"Connecting to server at {server_address}")

        with open(output_file, "w") as file:
            # Send initial connection request
            packet = self.create_packet(0, "", True)
            client_socket.sendto(packet, server_address)
            # logging.info("Sent initial connection request")

            while True:
                try:
                    # Receive packet
                    packet, _ = client_socket.recvfrom(BUFFER_SIZE)
                    seq_num, data, end = self.parse_packet(packet)
                    # logging.info(f"Received packet with seq_num {seq_num}")

                    if end:
                        # Handle end of transmission
                        self.send_ack(client_socket, server_address, -1)
                        # logging.info("End of transmission received")
                        break

                    if seq_num == self.expected_seq_num:
                        # In-order packet received
                        file.write(data)
                        # logging.info(f"Writing packet {seq_num} to file")
                        self.expected_seq_num += MSS

                        # Process any buffered packets
                        self.process_buffered_packets(file)

                        # Send cumulative ACK
                        self.send_ack(
                            client_socket, server_address, self.expected_seq_num
                        )
                        self.duplicate_ack_count.clear()  # Reset duplicate ACK count

                    elif seq_num < self.expected_seq_num:
                        # Duplicate packet received
                        self.duplicate_ack_count[seq_num] += 1
                        # logging.info(f"Duplicate packet {seq_num} received ({self.duplicate_ack_count[seq_num]} times)")

                        # Send duplicate ACK
                        self.send_ack(
                            client_socket, server_address, self.expected_seq_num
                        )

                    else:
                        # Out-of-order packet received
                        # logging.info(f"Out-of-order packet received: got {seq_num}, expected {self.expected_seq_num}")
                        self.buffer[seq_num] = data

                        # Send duplicate ACK for the last in-order packet
                        self.send_ack(
                            client_socket, server_address, self.expected_seq_num
                        )

                except socket.timeout:
                    # logging.warning("Timeout occurred, resending ACK")
                    # Resend ACK for the last in-order packet received
                    self.send_ack(client_socket, server_address, self.expected_seq_num)

        client_socket.close()
        # logging.info("File transfer completed")


def main():
    parser = argparse.ArgumentParser(
        description="TCP Reno client for reliable file transfer over UDP."
    )
    parser.add_argument("server_ip", help="IP address of the server")
    parser.add_argument("server_port", type=int, help="Port number of the server")
    parser.add_argument(
        "--pref_outfile", help="Preferred output file", default="received_file.txt"
    )
    args = parser.parse_args()
    client = TCPRenoClient()
    client.receive_file(args.server_ip, args.server_port, args.pref_outfile)


if __name__ == "__main__":
    main()
