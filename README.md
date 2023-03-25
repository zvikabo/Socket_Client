# Socket_Client
Python Socket_Client using RPC RabbitMQ


RPC server - listening to RabbitMQ queue and when an event/request enter the queue- 
tha application open a socket to legacy server to implemnt win socket protocol and close the socket and reture the protocol reply to another queue.
The application runs as a deamon 
