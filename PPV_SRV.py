#!/usr/bin/python3
"""
 RPC_PPV Server.
"""
import json
import amqpstorm, socket
from amqpstorm import Message
from time import sleep
import initialization
import daemon


def main_program():
    v_cfg_file = '/GCTI/RestRPC/PPV_SRV/ppv_srv.cfg'
    cfg_file = initialization.cfgFile(v_cfg_file)
    cfg_params = cfg_file.get_cfg_data()
    prv_logger = initialization.MyLogger(cfg_params.get('Log_File').get('log_file_name'),
                                         int(cfg_params.get('Log_File').get('maxbytes')),
                                         int(cfg_params.get('Log_File').get('backupcount')))
    my_logger = prv_logger.getLogger()
    my_logger.info('cfg_params :  ', cfg_params)

    # ============ configuration file params  ========== #

    # ------------ RabbitMQ params  -------------------- #
    v_primary_host = cfg_params.get('RabbitMQ').get('primary_host')
    v_backup_host = cfg_params.get('RabbitMQ').get('backup_host')
    v_vhost = cfg_params.get('RabbitMQ').get('vhost')
    v_username = cfg_params.get('RabbitMQ').get('username')
    v_password = cfg_params.get('RabbitMQ').get('password')
    v_rpc_queue = cfg_params.get('RabbitMQ').get('rpc_queue')
    v_max_retries = int(cfg_params.get('RabbitMQ').get('max_retries'))
    v_max_retries_per_server = int(cfg_params.get('RabbitMQ').get('max_retries_per_server'))
    v_message_ttl = int(cfg_params.get('RabbitMQ').get('message_ttl'))

    # -------      Wizard  params  --------- #
    v_wizard_host = cfg_params.get('WizardServer').get('wizard_host')
    v_wizard_port = int(cfg_params.get('WizardServer').get('wizard_port'))
    v_number_of_ports = int(cfg_params.get('WizardServer').get('end_port_number')) - int(
        cfg_params.get('WizardServer').get('start_port_number'))
    v_port_number_when_no_conn_id = int(cfg_params.get('WizardServer').get('port_number_when_no_coonnid'))
    v_wizard_max_retries = int(cfg_params.get('WizardServer').get('wizard_max_retries'))
    v_wizard_time_out_err_code = cfg_params.get('WizardServer').get('wizard_time_out_err_code')
    v_wizard_invalid_req_from_gvp_err_code = cfg_params.get('WizardServer').get('wizard_invalid_req_from_gvp_err_code')

    def convert2linenum(connid, number_of_ports=30):
        """ convert connid from Hex to Decimal and than create the line number using modulo withe the number of line number that the  wozard port support"""

        calculate_line_num = (int(connid, 16)) % number_of_ports + 1
        line_num = (str(calculate_line_num)).zfill(3)  # padding with 0  from right side
        my_logger.info(f'Wizard line number {line_num}')

        return line_num

    def msg_protocol(msg):
        """ Get the action to invoke from the GVP message """
        my_logger.info(f' GVP request : {msg}')
        try:

            if msg.__contains__('EN'):
                tmp_msg = 'EN' + msg.get('EN')
                msg2return = tmp_msg.ljust(22)  # padding with spaces

            elif msg.__contains__('EV'):
                tmp_msg = 'EV' + msg.get('EV')
                msg2return = tmp_msg.ljust(22)  # padding with spaces

            elif msg.__contains__('CONFIRM'):
                msg2return = 'UP'

            else:
                msg2return = 'EV00000000000000000000'

            return msg2return

        except Exception as e:
            my_logger.info(f' GVP request building error : {e}')
            return  'EV00000000000000000000'

    class SocketClient(object):
        def __init__(self, host, port, max_retries=None, msg_terminator='\r'):
            self.target_host = host
            self.target_port = port
            self.msg_terminator = str(msg_terminator)
            self.max_retries = max_retries
            self.connection = None
            self.create_connection()
            print('target_port is : ', self.target_host, self.target_port)

        def create_connection(self):
            
            attempts = 0
            while True:
                my_logger.info('attempts : ', attempts)
                attempts += 1
                try:
                    self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.connection.connect((self.target_host, self.target_port))
                    break
                except socket.error as e:
                    my_logger.error(f'socket error : {e}')
                    my_logger.info(f' Attempt Num :  {attempts} ')
                    if attempts > int(self.max_retries):
                        my_logger.error(f'Wizard timeout {1 * attempts} sec')

                    sleep(1)

                except KeyboardInterrupt:
                    break

        def send_msg(self, message):
            try:
                self.connection.send(bytes((message + self.msg_terminator).encode('utf-8')))
                my_logger.info(f' sending message to wizard : {message}')
            
            except socket.error as e:
                my_logger.info(f'socket error while sending a message to wizard {e}')
                self.close_socket()

        def receive_msg(self):
            while True:
                try:
                    chunk = self.connection.recv(1024)
                    my_logger.info(f'chunk{chunk}')
                    if chunk == b'':
                        raise RuntimeError("socket connection broken")
                    else:
                        response = chunk.decode('utf-8')
                        my_logger.info(f' response : {response}')
                        return response
                except socket.error as e:
                    my_logger.info(f'Create connection to wizard')
                    self.close_socket()

        def close_socket(self):
            if self.connection:
                self.connection.close()

    class RpcServer(object):

        def __init__(self, primary_host, backup_host, vhost, username, password, rpc_queue, max_retries=None):
            self.primary_host = primary_host
            self.backup_host = backup_host
            self.username = username
            self.password = password
            self.channel = None
            self.connection = None
            self.rpc_queue = rpc_queue
            self.max_retries = max_retries
            self.vhost = vhost
            self.create_connection()

        def create_connection(self):
            attempts = 0
            while True:
                my_logger.info(f'attempts{attempts}')
                attempts += 1
                try:
                    if attempts % 2 == 1:
                        self.connection = amqpstorm.Connection(self.primary_host, self.username, self.password,
                                                               virtual_host=self.vhost)
                    else:
                        self.connection = amqpstorm.Connection(self.backup_host, self.username, self.password,
                                                               virtual_host=self.vhost)

                    self.create_channel()
                    break

                except amqpstorm.AMQPConnectionError as e:
                    my_logger.exception(e)
                    if self.max_retries and attempts > self.max_retries:
                        break
                    sleep(min(attempts * 2, 30))
                except KeyboardInterrupt:
                    break

        def create_channel(self):
            attempts = 0
            while True:
                attempts += 1
                try:
                    self.channel = self.connection.channel()
                    self.channel.queue.declare(queue=self.rpc_queue, arguments={'x-message-ttl': v_message_ttl})
                    self.channel.basic.qos(prefetch_count=1)
                    self.channel.basic.consume(self.on_request, queue=self.rpc_queue)
                    my_logger.info(" [x] Awaiting RPC requests")
                    self.channel.start_consuming()

                except amqpstorm.AMQPChannelError as e:
                    my_logger.exception(e)
                    if self.max_retries and attempts > self.max_retries:
                        break
                    sleep(min(attempts * 2, 30))
                except KeyboardInterrupt:
                    break

        def on_request(self, message):
            msg_from_rpc_client = json.loads(message.body.replace("'", '"'))
            req2send = 'A' + convert2linenum(msg_from_rpc_client["connid"], v_number_of_ports) + msg_protocol(
                msg_from_rpc_client)

            try:
                wizard_client = SocketClient(v_wizard_host, v_wizard_port, v_wizard_max_retries)
                wizard_client.send_msg(req2send)
                my_logger.info(f'request to sent {req2send}')
                response = wizard_client.receive_msg()[4:]
                my_logger.info(f'wizard response : {response}')
                wizard_client.close_socket()
                my_logger.info(f'wizard close socket')

            except Exception as e:
                response = v_wizard_time_out_err_code
                my_logger.exception(f'wizard id down : {e}')

            properties = {'correlation_id': message.correlation_id}
            response = Message.create(message.channel, response, properties)
            my_logger.info(f'response   {response.body}')
            response.publish(message.reply_to)

            message.ack()

    while True:
        RpcServer(v_primary_host, v_backup_host, v_vhost, v_username, v_password, v_rpc_queue, v_max_retries)
        sleep(1)


with daemon.DaemonContext():
    main_program()