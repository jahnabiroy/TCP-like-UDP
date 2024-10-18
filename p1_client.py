import socket
import argparse

# Constants
MSS = 1400  # Maximum Segment Size
END_SIGNAL = b"END"  # Signal to indicate end of transmission

def receive_file(server_ip, server_port):
    """
    Receive the file from the server with reliability, handling packet loss
    and reordering.
    """
    # Initialize UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(2)  # Set timeout for server response

    server_address = (server_ip, server_port)
    expected_seq_num = 0
    output_file_path = "received_file.txt" 
    received_data = {}
    with open(output_file_path, 'wb') as file:
        while True:
            try:
                # Send initial connection request to server
                client_socket.sendto(b"START", server_address)

                # Receive the packet
                packet, _ = client_socket.recvfrom(MSS + 100)  # Allow room for headers
                
                # Check if the packet is the end signal from server
                if END_SIGNAL in packet:
                    print("Received END signal from server, file transfer complete")
                    break
                
                seq_num, data = parse_packet(packet)

                # If the packet is in order, write it to the file
                if seq_num == expected_seq_num:
                    file.write(data)
                    print(f"Received packet {seq_num}, writing to file")
                    
                    # Update expected seq number and send cumulative ACK for the received packet
                    expected_seq_num += len(data)
                    send_ack(client_socket, server_address, seq_num)
                elif seq_num < expected_seq_num:
                    # Duplicate or old packet, send ACK again
                    print(f"Received duplicate or old packet {seq_num}, sending ACK again")
                    send_ack(client_socket, server_address, seq_num)
                else:
                    # Packet arrived out of order
                    print(f"Received out of order packet {seq_num}, expecting {expected_seq_num}")
                    received_data[seq_num] = data  # Store out-of-order packets

                    # Attempt to write any stored out-of-order packets
                    while expected_seq_num in received_data:
                        file.write(received_data.pop(expected_seq_num))
                        print(f"Writing stored packet {expected_seq_num} to file")
                        expected_seq_num += 1
                    # Send ACK for the last in-order packet
                    send_ack(client_socket, server_address, expected_seq_num - 1)
            except socket.timeout:
                print("Timeout waiting for data")
                send_ack(client_socket, server_address, expected_seq_num - 1)  # Resend last ACK

def parse_packet(packet):
    """
    Parse the packet to extract the sequence number (4 bytes) and data.
    """
    # Extract the first 4 bytes for the sequence number (big-endian) and the rest is data
    seq_num = int.from_bytes(packet[:4], 'big')  # Extract the sequence number from the first 4 bytes
    data = packet[4:]  # The rest is the data
    return seq_num, data


def send_ack(client_socket, server_address, seq_num):
    """
    Send a cumulative acknowledgment for the received packet.
    """
    ack_packet = f"{seq_num}|ACK".encode()
    client_socket.sendto(ack_packet, server_address)
    print(f"Sent cumulative ACK for packet {seq_num}")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Reliable file receiver over UDP.')
parser.add_argument('server_ip', help='IP address of the server')
parser.add_argument('server_port', type=int, help='Port number of the server')

args = parser.parse_args()

# Run the client
receive_file(args.server_ip, args.server_port)
