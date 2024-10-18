import socket
import time
import argparse
import json

# Constants
MSS = 1400  # Maximum Segment Size for each packet
WINDOW_SIZE = 5  # Number of packets in flight
DUP_ACK_THRESHOLD = 3  # Threshold for duplicate ACKs to trigger fast recovery
FILE_PATH = "your_file.txt"  # Replace with your predefined file path
timeout = 1.0  # Initialize timeout to some value but update it as ACK packets arrive

def create_packet(seq_num, data):
    """
    Create a packet with the sequence number and data.
    """
    packet = {
        'seq_num': seq_num,
        'data': data.decode('utf-8')  # Assuming data is in bytes, decode for JSON serialization
    }
    return json.dumps(packet).encode('utf-8')  # Serialize the packet as JSON

def get_seq_no_from_ack_pkt(ack_pkt):
    """
    Extract the expected sequence number from the acknowledgment packet.
    """
    return int(ack_pkt.decode('utf-8'))  # Assuming the ack packet is a simple integer

def retransmit_unacked_packets(server_socket, client_address, unacked_packets):
    """
    Retransmit all unacknowledged packets.
    """
    for seq_num, (packet, _) in unacked_packets.items():
        server_socket.sendto(packet, client_address)
        print(f"Retransmitted packet {seq_num}")

def fast_recovery(server_socket, client_address, unacked_packets, seq_num):
    """
    Retransmit the earliest unacknowledged packet (fast recovery).
    """
    for seq_num in sorted(unacked_packets.keys()):
        server_socket.sendto(unacked_packets[seq_num][0], client_address)
        print(f"Fast recovery: Retransmitted packet {seq_num}")
        break  # Only retransmit the first unacknowledged packet

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
        chunk = None

        while True:
            # Use window-based sending
            while seq_num < window_base + WINDOW_SIZE:
                chunk = file.read(MSS)
                if not chunk:
                    # End of file
                    # Send end signal to the client 
                    break

                # Create and send the packet
                packet = create_packet(seq_num, chunk)
                if client_address:
                    server_socket.sendto(packet, client_address)
                else:
                    print("Waiting for client connection...")
                    data, client_address = server_socket.recvfrom(1024)
                    print(f"Connection established with client {client_address}")

                # Track sent packets
                unacked_packets[seq_num] = (packet, time.time())
                print(f"Sent packet {seq_num}")
                seq_num += 1

            # Wait for ACKs and retransmit if needed
            try:
                server_socket.settimeout(timeout)
                ack_packet, _ = server_socket.recvfrom(1024)
                ack_seq_num = get_seq_no_from_ack_pkt(ack_packet)

                if ack_seq_num > last_ack_received:
                    print(f"Received cumulative ACK for packet {ack_seq_num}")
                    last_ack_received = ack_seq_num
                    # Slide the window forward
                    # Remove acknowledged packets from the buffer
                    unacked_packets = {k: v for k, v in unacked_packets.items() if k > ack_seq_num}
                    window_base = ack_seq_num + 1
                    duplicate_ack_count = 0  # Reset on new ACK

                else:
                    # Duplicate ACK received
                    duplicate_ack_count += 1
                    print(f"Received duplicate ACK for packet {ack_seq_num}, count={duplicate_ack_count}")

                    if enable_fast_recovery and duplicate_ack_count >= DUP_ACK_THRESHOLD:
                        print("Entering fast recovery mode")
                        fast_recovery(server_socket, client_address, unacked_packets, seq_num)

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
