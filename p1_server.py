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
FILE_PATH = 'sending_file.txt'
MAX_RETRANSMISSIONS = 10

logging.basicConfig(filename='server_1.log', level=logging.INFO, filemode='w',
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
    
def get_seq_no_from_ack_pkt(ack_packet):
    json_packet = json.loads(ack_packet.decode('utf-8'))
    return json_packet['seq_num'],json_packet['end']

def send_file(server_ip, server_port,fast_recovery):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))

    logging.info(f"Server listening on {server_ip}:{server_port}")
    client_address = None
    file_path = FILE_PATH  # Predefined file name

    ack_packet, client_address = server_socket.recvfrom(1024)
    logging.info(f"Client Address: {client_address}")

    file_data = {}
    seq_num = 0
    max_seq = 0
    ack_data = {}
    with open(file_path, 'r') as file:
        while True:
            chunk = file.read(MSS)
            if not chunk:
                file_data[seq_num]='EOD'
                max_seq = max(max_seq,seq_num)
                seq_num = 0
                break
            file_data[seq_num] = chunk
            max_seq = max(max_seq,seq_num)
            ack_data[seq_num] = {"seq_num":seq_num, "ack_rec": False, "ack_count": 0}
            seq_num += MSS

    # logging.info(file_data)
    # logging.info(ack_data)
    base_seq = 0
    packet_times = {}
    while base_seq <= max_seq:
        for seq_num in range(base_seq, min(max_seq+MSS,base_seq+WINDOW_SIZE*MSS+MSS), MSS):
            current_time = time.time()
            if (seq_num in packet_times and current_time - packet_times[seq_num] < TIMEOUT):
                continue

            packet_times[seq_num] = current_time
            chunk = file_data[seq_num]
            if chunk == "EOD":
                packet = create_packet(seq_num,chunk,start = False,end = True)
            else:
                packet = create_packet(seq_num, chunk, start = False)
            server_socket.sendto(packet, client_address)
            logging.info(f"Sent packet {seq_num} {chunk}")
            try:
                server_socket.settimeout(TIMEOUT)
                ack_packet, _ = server_socket.recvfrom(1024)
                ack_seq_num, end = get_seq_no_from_ack_pkt(ack_packet)
                logging.info(f"Recieved Ack for: {ack_seq_num}")
                if end:
                    logging.info(f"File Transfer Complete")
                    base_seq = max_seq +1
                    break
                if(ack_seq_num <= base_seq):
                    continue

                ack_data[ack_seq_num-MSS]["ack_rec"]=True
                ack_data[ack_seq_num-MSS]["ack_count"]+=1
                base_seq = max(base_seq,ack_seq_num)
                if ack_data[ack_seq_num-MSS]["ack_count"] >= DUP_ACK_THRESHOLD and fast_recovery:
                    seq = ack_seq_num
                    chunk = file_data[seq]
                    ack_data[seq]["ack_count"] = 0
                    packet_times[seq] = time.time()
                    packet = create_packet(seq, chunk, start = False)
                    logging.info(f"Sending Fast Recovery packet {seq_num} {chunk}")


            except socket.timeout:
                logging.warning("Timeout occurred, resending packet.")
    
parser = argparse.ArgumentParser(description='Reliable file transfer server over UDP.')
parser.add_argument('server_ip', help='IP address of the server')
parser.add_argument('server_port', type=int, help='Port number of the server')
parser.add_argument('fast_recovery', type=int, help='Enable fast recovery')

args = parser.parse_args()

# Run the server
send_file(args.server_ip, args.server_port, args.fast_recovery)
