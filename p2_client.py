import socket
import argparse
import logging
import json
# Constants
MSS = 1400
TIMEOUT = 2
OUTPUT_FILE = "received_file.txt"

logging.basicConfig(filename='client_2.log', level=logging.INFO, filemode='w',
                    format='%(levelname)s - %(message)s')

def create_packet(seq_num, data, start = False, end = False):
    packet = {
        "seq_num": seq_num,
        "data_length": len(data),
        "data": data,
        "start": start,
        "end": end
    }
    json_str = json.dumps(packet)
    return json_str.encode('utf-8')

def receive_file(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT)  # Set timeout for server response
    client_address = client_socket.getsockname()
    logging.info(f"Client socket is running on: {client_address}")
    server_address = (server_ip, server_port)
    logging.info(f"Server Address: {server_address}")
    expected_seq_num = 0
    output_file_path = OUTPUT_FILE

    with open(output_file_path, 'w') as file:
        while True:
            # Send initial connection request to server
            packet = create_packet(0,"",True)
            client_socket.sendto(packet, server_address)
            try:
                # Receive the packet
                packet, _ = client_socket.recvfrom(MSS + 200)  # Allow room for headers
                seq_num, data, end = parse_packet(packet)

                if end:
                    packet = create_packet(seq_num,"",start=False,end=True)
                    send_ack(client_socket,server_address,-1)
                    logging.info("Received END signal from server, file transfer complete")
                    break

                # If the packet is in order, write it to the file
                if seq_num == expected_seq_num:
                    file.write(data)
                    logging.info(f"Received packet {seq_num}, writing to file: {data}")
                    expected_seq_num += MSS  # Update expected seq number
                    send_ack(client_socket, server_address, seq_num + MSS)  # Send ACK for received packet
                elif seq_num < expected_seq_num:
                    # Duplicate or old packet, send ACK again
                    send_ack(client_socket, server_address, seq_num + MSS)
                else:
                    # Packet arrived out of order (not handled in this basic example)
                    logging.warning(f"Received out-of-order packet {seq_num}, expected {expected_seq_num}")

            except socket.timeout:
                logging.warning("Timeout waiting for data")

def parse_packet(packet):
    json_packet = json.loads(packet.decode('utf-8'))
    seq_num, data, end = json_packet['seq_num'],json_packet['data'],json_packet['end']
    return seq_num,data,end

def send_ack(client_socket, server_address, seq_num):
    """ Send a cumulative acknowledgment for the received packet. """
    if seq_num == -1:
        ack_packet = create_packet(-1,"",start=False,end=True)
    else:
        ack_packet = create_packet(seq_num,"")
    client_socket.sendto(ack_packet, server_address)
    logging.info(f"Sent cumulative ACK for packet {seq_num}")


# Parse command-line arguments
parser = argparse.ArgumentParser(description='Reliable file receiver over UDP.')
parser.add_argument('server_ip', help='IP address of the server')
parser.add_argument('server_port', type=int, help='Port number of the server')

args = parser.parse_args()

# Run the client
receive_file(args.server_ip, args.server_port)
