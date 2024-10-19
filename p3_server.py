import socket
import time
import argparse
import logging
import json

# Constants
MSS = 1400
INITIAL_CWND = MSS  # Initial congestion window size
INITIAL_SSTHRESH = 16 * MSS  # Initial slow start threshold
TIMEOUT = 0.5
DUP_ACK_THRESHOLD = 3
FILE_PATH = 'sending_file.txt'

# logging.basicConfig(filename='server_2.log', level=logging.INFO, filemode='w', format='%(levelname)s - %(message)s')

class TCPRenoServer:
    def __init__(self):
        self.cwnd = INITIAL_CWND
        self.ssthresh = INITIAL_SSTHRESH
        self.duplicate_acks = {}
        self.in_fast_recovery = False
        self.last_ack = 0

    def create_packet(self, seq_num, data, start=False, end=False):
        packet = {
            "seq_num": seq_num,
            "data_length": len(data),
            "data": data,
            "start": start,
            "end": end
        }
        json_str = json.dumps(packet)
        return json_str.encode('utf-8')
    
    def get_seq_no_from_ack_pkt(self, ack_packet):
        json_packet = json.loads(ack_packet.decode('utf-8'))
        return json_packet['seq_num'], json_packet['end']

    def handle_timeout(self):
        """Handle timeout according to TCP Reno"""
        # logging.info(f"Timeout occurred. Old cwnd: {self.cwnd}")
        self.ssthresh = max(self.cwnd // 2, MSS)
        self.cwnd = MSS
        self.in_fast_recovery = False
        # logging.info(f"After timeout - cwnd: {self.cwnd}, ssthresh: {self.ssthresh}")

    def handle_duplicate_ack(self, seq_num):
        """Handle duplicate ACK according to TCP Reno"""
        if seq_num not in self.duplicate_acks:
            self.duplicate_acks[seq_num] = 1
        else:
            self.duplicate_acks[seq_num] += 1

        if self.duplicate_acks[seq_num] == DUP_ACK_THRESHOLD and not self.in_fast_recovery:
            # Enter fast recovery
            # logging.info(f"Entering fast recovery. Old cwnd: {self.cwnd}")
            self.ssthresh = max(self.cwnd // 2, MSS)
            self.cwnd = self.ssthresh + 3 * MSS
            self.in_fast_recovery = True
            # logging.info(f"Fast recovery - cwnd: {self.cwnd}, ssthresh: {self.ssthresh}")
            return True
        return False

    def handle_new_ack(self, ack_seq_num):
        """Handle new ACK according to TCP Reno"""
        if ack_seq_num > self.last_ack:
            if self.in_fast_recovery:
                # Exit fast recovery
                self.cwnd = self.ssthresh
                self.in_fast_recovery = False
                # logging.info(f"Exiting fast recovery - cwnd: {self.cwnd}")
            else:
                # Normal ACK processing
                if self.cwnd < self.ssthresh:
                    # Slow start phase
                    self.cwnd = min(self.cwnd * 2, self.ssthresh)
                    # logging.info(f"Slow start - increased cwnd to: {self.cwnd}")
                else:
                    # Congestion avoidance phase
                    self.cwnd += MSS * (MSS / self.cwnd)
                    # logging.info(f"Congestion avoidance - increased cwnd to: {self.cwnd}")
            
            self.last_ack = ack_seq_num
            self.duplicate_acks.clear()

    def send_file(self, server_ip, server_port):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((server_ip, server_port))
        # logging.info(f"Server listening on {server_ip}:{server_port}")

        # Wait for initial connection
        ack_packet, client_address = server_socket.recvfrom(1024)
        # logging.info(f"Client Address: {client_address}")

        # Read file into memory
        file_data = {}
        seq_num = 0
        max_seq = 0
        with open(FILE_PATH, 'r') as file:
            while True:
                chunk = file.read(MSS)
                if not chunk:
                    file_data[seq_num] = 'EOD'
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
                    if next_seq in packet_times and current_time - packet_times[next_seq] < TIMEOUT:
                        next_seq += MSS
                        continue

                    chunk = file_data[next_seq]
                    packet = self.create_packet(next_seq, chunk, end=(chunk == 'EOD'))
                    server_socket.sendto(packet, client_address)
                    packet_times[next_seq] = current_time
                    # logging.info(f"Sent packet {next_seq}, Window: {current_window}, CWND: {self.cwnd}")
                    next_seq += MSS

            # Wait for ACKs
            try:
                server_socket.settimeout(TIMEOUT)
                ack_packet, _ = server_socket.recvfrom(1024)
                ack_seq_num, end = self.get_seq_no_from_ack_pkt(ack_packet)
                
                if end:
                    # logging.info("File transfer complete")
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
    parser = argparse.ArgumentParser(description='TCP Reno server for reliable file transfer over UDP.')
    parser.add_argument('server_ip', help='IP address of the server')
    parser.add_argument('server_port', type=int, help='Port number of the server')
    
    args = parser.parse_args()
    server = TCPRenoServer()
    server.send_file(args.server_ip, args.server_port)

if __name__ == "__main__":
    main()