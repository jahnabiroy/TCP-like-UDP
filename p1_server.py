import socket
import time
import argparse
import logging

MSS = 1400  
WINDOW_SIZE = 5  
TIMEOUT = 1.0  
DUP_ACK_THRESHOLD = 3
FILE_PATH = 'sending_file.txt'

logging.basicConfig(filename='server.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def create_packet(seq_num, data):
    """ Create a packet with sequence number and data. """
    logging.info(f"Sending {seq_num}: {data}")
    return f"{seq_num}|{data.decode('utf-8')}".encode('utf-8')

def get_seq_no_from_ack_pkt(ack_packet):
    """ Extract sequence number from the acknowledgment packet. """
    logging.info(f"Ack Packet: {ack_packet}")
    ack_string = ack_packet.decode('utf-8')
    seq_num_str = ack_string.split('|')[0]  # Split and get the sequence number part
    return int(seq_num_str)  # Convert to an integer and return

def send_file(server_ip, server_port,fast_recovery):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))

    logging.info(f"Server listening on {server_ip}:{server_port}")
    client_address = None
    file_path = FILE_PATH  # Predefined file name

    ack_packet, client_address = server_socket.recvfrom(1024)
    logging.info(f"Client Address: {client_address}")


    # Handshake phase
    handshake_packet = create_packet(-1, b'START')
    logging.info("Sending handshake packet...")
    server_socket.sendto(handshake_packet, (server_ip, server_port))

    # Wait for acknowledgment of the handshake

    ack_seq_num = get_seq_no_from_ack_pkt(ack_packet)
    if ack_seq_num == 0:
        logging.info(f"Handshake successful with client {client_address}")

    with open(file_path, 'rb') as file:
        seq_num = 0
        while True:
            chunk = file.read(MSS)
            if not chunk:
                # Send end-of-file signal
                end_packet = create_packet(seq_num, b'END')
                server_socket.sendto(end_packet, client_address)
                logging.info("Sent END signal to client.")
                break
            
            # Create and send the packet
            packet = create_packet(seq_num, chunk)
            server_socket.sendto(packet, client_address)
            logging.info(f"Sent packet {seq_num}")
            
            # Wait for ACK
            try:
                server_socket.settimeout(TIMEOUT)
                ack_packet, _ = server_socket.recvfrom(1024)
                ack_seq_num = get_seq_no_from_ack_pkt(ack_packet)
                if ack_seq_num >= seq_num:
                    logging.info(f"Received ACK for packet {ack_seq_num}")
                    seq_num = ack_seq_num  # Move to the next sequence number
            except socket.timeout:
                logging.warning("Timeout occurred, resending packet.")


parser = argparse.ArgumentParser(description='Reliable file transfer server over UDP.')
parser.add_argument('server_ip', help='IP address of the server')
parser.add_argument('server_port', type=int, help='Port number of the server')
parser.add_argument('fast_recovery', type=int, help='Enable fast recovery')

args = parser.parse_args()

# Run the server
send_file(args.server_ip, args.server_port, args.fast_recovery)
