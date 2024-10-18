import socket
import time
import argparse

# Constants
MSS = 1400  # Maximum Segment Size for each packet
WINDOW_SIZE =  5 # Number of packets in flight
DUP_ACK_THRESHOLD = 3  # Threshold for duplicate ACKs to trigger fast recovery
FILE_PATH = "your_file.txt"
TIMEOUT = 1.0  # Initialize timeout to some value but update it as ACK packets arrive


def create_packet(seq_num, data):
    """Create a packet with a sequence number and data."""
    # Packet structure: seq_num (int) + data (bytes)
    return seq_num.to_bytes(4, 'big') + data
    

def get_seq_no_from_ack_pkt(ack_packet):
    """Extract the sequence number from an ACK packet."""
    # Assuming the sequence number is sent as the first 4 bytes of the ACK packet
    return int.from_bytes(ack_packet[:4], 'big')


def fast_recovery(server_socket, client_address, unacked_packets = None):
    """Handle fast retransmit and recovery."""
    # Retransmit the packet that was indicated by duplicate ACKs
    if unacked_packets:
        min_seq_num = min(unacked_packets.keys())
        packet, _ = unacked_packets[min_seq_num]
        print(f"Fast retransmitting packet {min_seq_num}")
        server_socket.sendto(packet, client_address)

def retransmit_unacked_packets(server_socket, client_address, unacked_packets):
    """Retransmit all unacknowledged packets after a timeout."""
    for seq_num, (packet, _) in unacked_packets.items():
        print(f"Retransmitting packet {seq_num} due to timeout")
        server_socket.sendto(packet, client_address)
    

def send_file(server_ip, server_port, enable_fast_recovery):
    """
    Send a predefined file to the client, ensuring reliability over UDP.
    """
    # Initialize UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))

    print(f"Server listening on {server_ip}:{server_port}")

    # Wait for client to initiate connection
    client_address = None
    file_path = FILE_PATH  # Predefined file name

    with open(file_path, 'rb') as file:
        seq_num = 0
        window_base = 0
        unacked_packets = {}
        duplicate_ack_count = 0
        last_ack_received = -1


        while True:
            while seq_num < window_base + WINDOW_SIZE:
                chunk = file.read(MSS)
                if not chunk:
                    # End of file, send an end-of-file signal to the client
                    packet = create_packet(seq_num, b'EOF')
                    if client_address:
                        server_socket.sendto(packet, client_address)
                    break

                # Create and send the packet
                packet = create_packet(seq_num, chunk)
                if client_address:
                    server_socket.sendto(packet, client_address)
                else:
                    print("Waiting for client connection...")
                    data, client_address = server_socket.recvfrom(1024)
                    print(f"Connection established with client {client_address}")
                

                unacked_packets[seq_num] = (packet, time.time())
                print(f"Sent packet {seq_num}")
                seq_num += 1

            # Wait for ACKs and retransmit if needed
            try:
            	## Handle ACKs, Timeout, Fast retransmit
                server_socket.settimeout(TIMEOUT)
                ack_packet, _ = server_socket.recvfrom(1024)
                ack_seq_num = get_seq_no_from_ack_pkt(ack_packet)

                if ack_seq_num > last_ack_received:
                    print(f"Received cumulative ACK for packet {ack_seq_num}")
                    last_ack_received = ack_seq_num
                    # Slide the window forward
                    window_base = ack_seq_num + 1
                    # Remove acknowledged packets from the buffer
                    for seq in list(unacked_packets.keys()):
                        if seq <= ack_seq_num:
                            del unacked_packets[seq]
                    duplicate_ack_count = 0
                    
                else:
                    # Duplicate ACK received
                    duplicate_ack_count += 1
                    print(f"Received duplicate ACK for packet {ack_seq_num}, count={duplicate_ack_count}")
                    if enable_fast_recovery and duplicate_ack_count >= DUP_ACK_THRESHOLD:
                        print("Entering fast recovery mode")
                        fast_recovery(server_socket, client_address, unacked_packets)

            except socket.timeout:
                # Timeout handling: retransmit all unacknowledged packets
                print("Timeout occurred, retransmitting unacknowledged packets")
                retransmit_unacked_packets(server_socket, client_address, unacked_packets)

            # Check if we are done sending the file
            if not chunk and len(unacked_packets) == 0:
                print("File transfer complete")
                break

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Reliable file transfer server over UDP.')
parser.add_argument('server_ip', help='IP address of the server')
parser.add_argument('server_port', type=int, help='Port number of the server')
parser.add_argument('fast_recovery', type=int, help='Enable fast recovery')

args = parser.parse_args()

# Run the server
send_file(args.server_ip, args.server_port, args.fast_recovery)
