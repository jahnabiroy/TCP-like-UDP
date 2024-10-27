import socket
import time
import argparse
import logging
import json
import time

MSS = 1400
WINDOW_SIZE = 6
TIMEOUT = 0.0465
DUP_ACK_THRESHOLD = 3
FILE_PATH = "sending_file.txt"
MAX_RETRANSMISSIONS = 10

logging.basicConfig(
    filename="server_1.log",
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


def get_seq_no_from_ack_pkt(ack_packet):
    json_packet = json.loads(ack_packet.decode("utf-8"))
    return json_packet["seq_num"], json_packet["end"]


def send_file(server_ip, server_port, fast_recovery):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))

    rtt_manager = RTTManager()  # Create RTT manager instance

    logging.info(f"Server listening on {server_ip}:{server_port}")
    client_address = None
    file_path = FILE_PATH

    ack_packet, client_address = server_socket.recvfrom(1024)
    logging.info(f"Client Address: {client_address}")

    file_data = {}
    seq_num = 0
    max_seq = 0
    ack_data = {}
    with open(file_path, "r") as file:
        while True:
            chunk = file.read(MSS)
            if not chunk:
                file_data[seq_num] = "EOD"
                max_seq = max(max_seq, seq_num)
                seq_num = 0
                break
            file_data[seq_num] = chunk
            max_seq = max(max_seq, seq_num)
            ack_data[seq_num] = {"seq_num": seq_num, "ack_rec": False, "ack_count": 0}
            seq_num += MSS

    base_seq = 0
    packet_times = {}
    while base_seq <= max_seq:
        current_timeout = rtt_manager.get_timeout()
        logging.info(f"Current timeout: {current_timeout}")

        for seq_num in range(
            base_seq, min(max_seq + MSS, base_seq + WINDOW_SIZE * MSS + MSS), MSS
        ):
            current_time = time.time()
            if (
                seq_num in packet_times
                and current_time - packet_times[seq_num] < current_timeout
            ):
                continue

            packet_times[seq_num] = current_time
            chunk = file_data[seq_num]
            if chunk == "EOD":
                packet = create_packet(seq_num, chunk, start=False, end=True)
            else:
                packet = create_packet(seq_num, chunk, start=False)
            server_socket.sendto(packet, client_address)
            logging.info(f"Sent packet {seq_num} {chunk}")

            try:
                server_socket.settimeout(current_timeout)
                ack_packet, _ = server_socket.recvfrom(1024)
                receive_time = time.time()
                ack_seq_num, end = get_seq_no_from_ack_pkt(ack_packet)

                # Calculate RTT and update timeout if this is an ACK for a packet we sent
                if ack_seq_num - MSS in packet_times:
                    measured_rtt = receive_time - packet_times[ack_seq_num - MSS]
                    new_timeout = rtt_manager.update_rtt(measured_rtt)
                    logging.info(
                        f"Measured RTT: {measured_rtt}, New timeout: {new_timeout}"
                    )

                logging.info(f"Received Ack for: {ack_seq_num}")
                if end:
                    logging.info(f"File Transfer Complete")
                    base_seq = max_seq + 1
                    break
                if ack_seq_num <= base_seq:
                    continue

                ack_data[ack_seq_num - MSS]["ack_rec"] = True
                ack_data[ack_seq_num - MSS]["ack_count"] += 1
                base_seq = max(base_seq, ack_seq_num)
                if (
                    ack_data[ack_seq_num - MSS]["ack_count"] >= DUP_ACK_THRESHOLD
                    and fast_recovery
                ):
                    seq = ack_seq_num
                    chunk = file_data[seq]
                    ack_data[seq]["ack_count"] = 0
                    packet_times[seq] = time.time()
                    packet = create_packet(seq, chunk, start=False)
                    logging.info(f"Sending Fast Recovery packet {seq_num} {chunk}")

            except socket.timeout:
                logging.warning("Timeout occurred, adjusting timeout value")
                new_timeout = rtt_manager.handle_timeout()
                logging.info(f"New timeout after timeout event: {new_timeout}")


# def send_file(server_ip, server_port, fast_recovery):
#     server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     server_socket.bind((server_ip, server_port))

#     logging.info(f"Server listening on {server_ip}:{server_port}")
#     client_address = None
#     file_path = FILE_PATH  # Predefined file name

#     ack_packet, client_address = server_socket.recvfrom(1024)
#     logging.info(f"Client Address: {client_address}")

#     file_data = {}
#     seq_num = 0
#     max_seq = 0
#     ack_data = {}
#     with open(file_path, "r") as file:
#         while True:
#             chunk = file.read(MSS)
#             if not chunk:
#                 file_data[seq_num] = "EOD"
#                 max_seq = max(max_seq, seq_num)
#                 seq_num = 0
#                 break
#             file_data[seq_num] = chunk
#             max_seq = max(max_seq, seq_num)
#             ack_data[seq_num] = {"seq_num": seq_num, "ack_rec": False, "ack_count": 0}
#             seq_num += MSS

#     # logging.info(file_data)
#     # logging.info(ack_data)
#     base_seq = 0
#     packet_times = {}
#     while base_seq <= max_seq:
#         print(packet_times)
#         for seq_num in range(
#             base_seq, min(max_seq + MSS, base_seq + WINDOW_SIZE * MSS + MSS), MSS
#         ):
#             current_time = time.time()
#             if (
#                 seq_num in packet_times
#                 and current_time - packet_times[seq_num] < TIMEOUT
#             ):
#                 continue

#             packet_times[seq_num] = current_time
#             chunk = file_data[seq_num]
#             if chunk == "EOD":
#                 packet = create_packet(seq_num, chunk, start=False, end=True)
#             else:
#                 packet = create_packet(seq_num, chunk, start=False)
#             server_socket.sendto(packet, client_address)
#             logging.info(f"Sent packet {seq_num} {chunk}")
#             try:
#                 server_socket.settimeout(TIMEOUT)
#                 ack_packet, _ = server_socket.recvfrom(1024)
#                 ack_seq_num, end = get_seq_no_from_ack_pkt(ack_packet)
#                 logging.info(f"Recieved Ack for: {ack_seq_num}")
#                 if end:
#                     logging.info(f"File Transfer Complete")
#                     base_seq = max_seq + 1
#                     break
#                 if ack_seq_num <= base_seq:
#                     continue

#                 ack_data[ack_seq_num - MSS]["ack_rec"] = True
#                 ack_data[ack_seq_num - MSS]["ack_count"] += 1
#                 base_seq = max(base_seq, ack_seq_num)
#                 if (
#                     ack_data[ack_seq_num - MSS]["ack_count"] >= DUP_ACK_THRESHOLD
#                     and fast_recovery
#                 ):
#                     seq = ack_seq_num
#                     chunk = file_data[seq]
#                     ack_data[seq]["ack_count"] = 0
#                     packet_times[seq] = time.time()
#                     packet = create_packet(seq, chunk, start=False)
#                     logging.info(f"Sending Fast Recovery packet {seq_num} {chunk}")

#             except socket.timeout:
#                 logging.warning("Timeout occurred, resending packet.")


parser = argparse.ArgumentParser(description="Reliable file transfer server over UDP.")
parser.add_argument("server_ip", help="IP address of the server")
parser.add_argument("server_port", type=int, help="Port number of the server")
parser.add_argument("fast_recovery", type=int, help="Enable fast recovery")

args = parser.parse_args()

# Run the server
send_file(args.server_ip, args.server_port, args.fast_recovery)
