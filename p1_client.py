import socket
import argparse
import logging

# Constants
MSS = 1400  # Maximum Segment Size
TIMEOUT = 2

# Set up logging
logging.basicConfig(filename='client.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def receive_file(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT)  # Set timeout for server response
    client_address = client_socket.getsockname()
    logging.info(f"Client socket is running on: {client_address}")
    server_address = (server_ip, server_port)
    logging.info(f"Server Address: {server_address}")
    expected_seq_num = 0
    output_file_path = "received_file.txt"  # Default file name

    with open(output_file_path, 'wb') as file:
        while True:
            # Send initial connection request to server
            client_socket.sendto(b"0|START", server_address)

            try:
                # Receive the packet
                packet, _ = client_socket.recvfrom(MSS + 100)  # Allow room for headers
                logging.info(f"Packet received: {packet}")
                seq_num, data = parse_packet(packet)

                if data == b'END':
                    logging.info("Received END signal from server, file transfer complete")
                    break

                # If the packet is in order, write it to the file
                if seq_num == expected_seq_num:
                    file.write(data)
                    logging.info(f"Received packet {seq_num}, writing to file")
                    expected_seq_num += 1  # Update expected seq number
                    send_ack(client_socket, server_address, seq_num)  # Send ACK for received packet
                elif seq_num < expected_seq_num:
                    # Duplicate or old packet, send ACK again
                    send_ack(client_socket, server_address, seq_num)
                else:
                    # Packet arrived out of order (not handled in this basic example)
                    logging.warning(f"Received out-of-order packet {seq_num}, expected {expected_seq_num}")

            except socket.timeout:
                logging.warning("Timeout waiting for data")

def parse_packet(packet):
    """ Parse the packet to extract the sequence number and data. """
    seq_num, data = packet.split(b'|', 1)
    return int(seq_num), data

def send_ack(client_socket, server_address, seq_num):
    """ Send a cumulative acknowledgment for the received packet. """
    ack_packet = f"{seq_num}|ACK".encode()
    client_socket.sendto(ack_packet, server_address)
    logging.info(f"Sent cumulative ACK for packet {seq_num}")


# Parse command-line arguments
parser = argparse.ArgumentParser(description='Reliable file receiver over UDP.')
parser.add_argument('server_ip', help='IP address of the server')
parser.add_argument('server_port', type=int, help='Port number of the server')

args = parser.parse_args()

# Run the client
receive_file(args.server_ip, args.server_port)
