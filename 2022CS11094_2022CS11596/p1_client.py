import socket
import argparse
import logging
import json
import time

# Constants
MSS = 1400
OUTPUT_FILE = "received_file.txt"

logging.basicConfig(
    filename="client_1.log",
    level=logging.INFO,
    filemode="w",
    format="%(levelname)s - %(message)s",
)


class RTTManager:
    def __init__(self):
        # Initial values
        self.srtt = None  # Smoothed Round Trip Time
        self.rttvar = None  # Round Trip Time Variation
        self.rto = 1.0  # Initial RTO of 1 second

        # Constants for RTT calculation (as per RFC 6298)
        self.ALPHA = 0.125  # Smoothing factor for SRTT
        self.BETA = 0.25  # Smoothing factor for RTTVAR
        self.K = 4  # Factor for RTO calculation
        self.MIN_RTO = 0.2  # Minimum RTO value (200ms)
        self.MAX_RTO = 60  # Maximum RTO value (60 seconds)

    def update_rtt(self, measured_rtt):
        """Update SRTT, RTTVAR, and RTO based on new RTT measurement"""
        if self.srtt is None:
            # First RTT measurement
            self.srtt = measured_rtt
            self.rttvar = measured_rtt / 2
        else:
            # Update RTTVAR and SRTT as per Jacobson's algorithm
            self.rttvar = (1 - self.BETA) * self.rttvar + self.BETA * abs(
                self.srtt - measured_rtt
            )
            self.srtt = (1 - self.ALPHA) * self.srtt + self.ALPHA * measured_rtt

        # Calculate new RTO
        self.rto = self.srtt + max(self.K * self.rttvar, 0.2)

        # Bound RTO to reasonable values
        self.rto = max(self.MIN_RTO, min(self.MAX_RTO, self.rto))

        return self.rto

    def get_timeout(self):
        """Get current timeout value"""
        return self.rto

    def handle_timeout(self):
        """Double the RTO on timeout (exponential backoff)"""
        self.rto = min(self.MAX_RTO, self.rto * 2)
        return self.rto


def create_packet(seq_num, data, start=False, end=False):
    packet = {
        "seq_num": seq_num,
        "data_length": len(data),
        "data": data,
        "start": start,
        "end": end,
    }
    json_str = json.dumps(packet)
    return json_str.encode("utf-8")


def receive_file(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rtt_manager = RTTManager()  # Create RTT manager instance
    client_address = client_socket.getsockname()
    logging.info(f"Client socket is running on: {client_address}")
    server_address = (server_ip, server_port)
    logging.info(f"Server Address: {server_address}")
    expected_seq_num = 0
    output_file_path = OUTPUT_FILE
    packet_times = {}  # To store send times of packets

    with open(output_file_path, "w") as file:
        while True:
            current_timeout = rtt_manager.get_timeout()
            client_socket.settimeout(current_timeout)
            # logging.info(f"Current timeout: {current_timeout}")

            try:
                # Send initial connection request to server
                if expected_seq_num == 0:
                    packet = create_packet(0, "", True)
                    send_time = time.time()
                    packet_times[0] = send_time
                    client_socket.sendto(packet, server_address)

                # Receive the packet
                packet, _ = client_socket.recvfrom(MSS + 200)  # Allow room for headers
                receive_time = time.time()
                seq_num, data, end = parse_packet(packet)

                # Update RTT if this is a response to our packet
                if seq_num in packet_times:
                    measured_rtt = receive_time - packet_times[seq_num]
                    new_timeout = rtt_manager.update_rtt(measured_rtt)
                    logging.info(
                        f"Measured RTT: {measured_rtt}, New timeout: {new_timeout}"
                    )

                if end:
                    packet = create_packet(seq_num, "", start=False, end=True)
                    send_ack(client_socket, server_address, -1)
                    logging.info(
                        "Received END signal from server, file transfer complete"
                    )
                    break

                # If the packet is in order, write it to the file
                if seq_num == expected_seq_num:
                    file.write(data)
                    # logging.info(f"Received packet {seq_num}, writing to file: {data}")
                    expected_seq_num += MSS  # Update expected seq number
                    # Store send time of ACK for RTT measurement
                    packet_times[expected_seq_num] = time.time()
                    send_ack(
                        client_socket, server_address, expected_seq_num
                    )  # Send ACK for received packet
                elif seq_num < expected_seq_num:
                    # Duplicate or old packet, send ACK again
                    packet_times[seq_num + MSS] = time.time()
                    send_ack(client_socket, server_address, seq_num + MSS)
                else:
                    # Packet arrived out of order (not handled in this basic example)
                    logging.warning(
                        f"Received out-of-order packet {seq_num}, expected {expected_seq_num}"
                    )

            except socket.timeout:
                logging.warning("Timeout occurred, adjusting timeout value")
                new_timeout = rtt_manager.handle_timeout()
                logging.info(f"New timeout after timeout event: {new_timeout}")
                # Resend the last ACK in case it was lost
                if expected_seq_num > 0:
                    packet_times[expected_seq_num] = time.time()
                    send_ack(client_socket, server_address, expected_seq_num)


def parse_packet(packet):
    json_packet = json.loads(packet.decode("utf-8"))
    seq_num, data, end = json_packet["seq_num"], json_packet["data"], json_packet["end"]
    return seq_num, data, end


def send_ack(client_socket, server_address, seq_num):
    """Send a cumulative acknowledgment for the received packet."""
    if seq_num == -1:
        ack_packet = create_packet(-1, "", start=False, end=True)
    else:
        ack_packet = create_packet(seq_num, "")
    client_socket.sendto(ack_packet, server_address)
    logging.info(f"Sent cumulative ACK for packet {seq_num}")


# Parse command-line arguments
parser = argparse.ArgumentParser(description="Reliable file receiver over UDP.")
parser.add_argument("server_ip", help="IP address of the server")
parser.add_argument("server_port", type=int, help="Port number of the server")

args = parser.parse_args()

# Run the client
startinng = time.time()
receive_file(args.server_ip, args.server_port)
endinng = time.time()
print(endinng - startinng)
