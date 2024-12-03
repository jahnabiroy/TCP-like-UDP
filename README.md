# TCP-Like UDP

This assignment was done as part of the COL334 course requirements. The objective of the assignment is to implement a simple file-transfer protocol using UDP Sockets. However, since UDP is unreliable and does not provide congestion control mechanisms, we piggyback on how TCP implements reliability and congestion control.

## P1 - Reliability

In this part, the server initiates the process by sequentially numbering packets and sending them to the client.
The client acknowledges receipt of each packet using cumulative acknowledgments (ACKs), which are
designed to inform the server of the next expected sequence number, thereby confirming the successful
delivery of previous packets. A timeout mechanism triggers retransmission if the server fails to receive
an ACK within the expected timeframe or detects three duplicate ACKs. When fast recovery is enabled,
the server responds to duplicate ACKs by quickly retransmitting lost packets, allowing the transfer to
continue without waiting for a full timeout. To dynamically adapt to network conditions, the timeout
duration is calculated based on observed round-trip times (RTTs) using Jacobson's algorithm.

To run the code, run the following commands in two terminals.

```
python3 p1_server.py 127.0.0.1 6555 0       # to disable fast recovery
or
python3 p1_server.py 127.0.0.1 6555 1       # to enable fast recovery
```

```
python3 p1_client.py 127.0.0.1 6555
```

## P2 - TCP Reno

In this part, the TCP Reno server implements a dynamic window size using the congestion window and slow start
threshold variables to adapt to network conditions. Initially set to a predefined size, the congestion
window increases during the slow start phase with each acknowledgment received, while transitioning to
a more conservative growth rate in the congestion avoidance phase. Upon detecting timeouts, the server
reduces the slow start threshold and resets the congestion window, effectively slowing down transmission
to mitigate congestion. Additionally, the server responds to duplicate ACKs, entering fast recovery mode
to adjust the window size.

To run the code, run the following commands in two terminals.

```
python3 p2_server.py 127.0.0.1 6555
```

```
python3 p2_client.py 127.0.0.1 6555
```

## P3 - TCP CUBIC

The TCP CUBIC algorithm introduces a cubic function to adjust the congestion window, optimizing performance on high-speed networks. TCP Cubic achieves greater RTT fairness because its congestion control algorithm depends primarily
on the time since the last congestion event, rather than the round-trip time (RTT) as in the case of Reno.

To run the code, run the following commands in two terminals.

```
python3 p3_server.py 127.0.0.1 6555
```

```
python3 p3_client.py 127.0.0.1 6555
```

## Experiments

Delay and Loss experiments have been employed to understand the performance of the mechanisms implemented and the same can be observed in the report as well. Fairness experiments have been performed for congestion control algorithms to figure out how different CCAs (RENO vs CUBIC).
