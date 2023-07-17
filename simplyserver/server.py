
# Created by TheBlackHole
# You can contact me on discord -> HORLOGE-TheBlackHole

import socket
import logging
from random import randint
from threading import Thread
from os.path import isdir
from time import strftime, localtime
from re import sub
from typing import Optional, Callable, AnyStr, List, Any, Iterable, ByteString, Union
from queue import Queue
from simplyserver._ressources import SimplyServerException, Addr, EventType


class SEvent:

    def __init__(self, server: 'Server', client: 'SClient'):

        self.server: Server = server
        self.client: SClient = client


class SReceiveEvent(SEvent):

    def __init__(self, server: 'Server', client: 'SClient', data: AnyStr):

        super().__init__(server, client)
        self.data: AnyStr = data


class SReceiveCommand(SEvent):

    def __init__(self, server: 'Server', client: 'SClient', args: Iterable):

        super().__init__(server, client)
        self.args: Iterable = args


class Server:

    def __init__(self, name: str, ip: Optional[str] = "localhost", port: Optional[int] = 5050, log_path: Optional[str] = ".", custom_file_logs: Optional[bool] = True, custom_console_logs: Optional[bool] = True, bufsize: Optional[int] = 128) -> None:

        self.__name = sub("\W", "_", name)
        self.__addr = Addr(ip, port)
        self.__log_path = log_path
        self.__file_logging = True
        self.__console_logging = True
        self.__logger = logging.getLogger(__name__)
        self.__logger.setLevel("DEBUG")
        self.log_path = self.__log_path
        self.__custom_file_logging = custom_file_logs
        self.__custom_console_logging = custom_console_logs
        self.__bufsize = bufsize
        self.__events = {EventType.ON_JOIN: None,
                         EventType.ON_QUIT: None, EventType.ON_RECEIVE: None}
        self.__commands = dict()
        self.__queue_event = Queue(0)
        self.__queue_command = Queue(0)
        self.__running = False
        self.__listening = False
        self.__processing = False
        self.__connected_clients = dict()

    def __repr__(self) -> str:

        return f"<server name={self.__name} ip={self.__addr.port} port={self.__addr.port} is_running={self.__running}>"

    def __listen(self) -> None:

        while self.__listening:

            try:
                conn, addr = self.__SOCKET.accept()
                self.log(
                    f"Client connects on port {addr[1]}...", log_formating=False)
            except Exception as e:
                self.stop()
                return

            new_client = SClient(self.__create_id(), self, conn, Addr(
                addr[0], addr[1]), self.__bufsize)
            self.__connected_clients[new_client.id] = new_client
            new_client.listen()
            self._enqueue_event(EventType.ON_JOIN, new_client)

    def __process_events(self) -> None:

        while self.__processing:

            event_name, client, *payload = self.__queue_event.get(block=True)
            if event_name == EventType.ON_RECEIVE:
                event = SReceiveEvent(self, client, payload[0])
            else:
                event = SEvent(self, client)
            if self.__events[event_name] != None:
                self.__events[event_name](event)
            self.__queue_event.task_done()

    def __process_commands(self) -> None:

        while self.__processing:

            command_name, client, *payload = self.__queue_command.get(block=True)
            command_event = SReceiveCommand(self, client, payload[0])
            if self.__commands[command_name] != None:
                self.__commands[command_name](command_event)
            self.__queue_command.task_done()

    def __create_id(self) -> int:
        
        new_id = randint(100000, 999999)
        while not self._check_valid_id(new_id):
            new_id = randint(100000, 999999)
        return new_id
    
    def _check_valid_id(self, id: int) -> bool:

        return True if len(str(id)) == 6 and id not in [client.id for client in self.__connected_clients.values()] else False

    def _enqueue_event(self, event: str, client: 'SClient', payload: Optional[Any] = None) -> None:

        self.__queue_event.put((event, client, payload))

    def _enqueue_command(self, command: str, client: 'SClient', payload: Optional[Any] = None) -> None:

        self.__queue_command.put((command, client, payload))

    def start(self) -> None:
        """Server.start()

        > Start the server if it is not already started, otherwise does nothing."""

        if self.__running:
            return

        self.__running = True
        if self.__custom_file_logging:
            self.__logger.debug("\n>> Server launch <<")

        self.__SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__SOCKET.bind(self.__addr.formated)
        self.__SOCKET.listen()

        listen_thread = Thread(target=self.__listen)
        self.__listening = True
        listen_thread.start()

        self.log(
            f"Server is listening on port {self.__addr.port}...", log_formating=False)

        self.__processing = True
        Thread(target=self.__process_events).start()
        Thread(target=self.__process_commands).start()

    def stop(self) -> None:
        """Server.stop()

        > Stop the server if it is not already stoped, otherwise does nothing."""

        if not self.__running:
            return

        self.__running = False

        if self.__listening:

            self.__listening = False
            self.__SOCKET.close()

        connected_clients = self.__connected_clients.copy()
        for client in connected_clients.values():
            client.close()

        self.__queue_event.join()
        self.__queue_command.join()
        self.__processing = False

    def broadcast(self, data: AnyStr, excluded_client: Optional['SClient' | Iterable['SClient']] = None) -> None:
        """Server.broadcast(data, excluded_client)

        > Send the 'data' to all connected clients except 'excluded_client'. \n
        > 'excluded_client' can be a single client or a list | tuple of clients."""

        if self.__running:

            if type(excluded_client) is SClient:
                excluded_client = [excluded_client]

            for client in self.__connected_clients.values():
                if excluded_client != None:
                    if client in excluded_client:
                        continue
                client.send(data)

    def log(self, *message: object, log_formating: Optional[bool] = True) -> None:
        """Server.log(message, log_formating=True)

        > Log the 'message' into the console if console_logging is True.\n
        > Log the 'message' into the log file if file_logging is True.\n
        > Add '[date] [time] [server name]' before 'message' if 'log_formating' is True."""

        if log_formating:
            log_message = f"{strftime('[%Y-%m-%d] [%H:%M:%S]', localtime())} [{self.__name.upper()}] {' '.join(message)}"
        else:
            log_message = ' '.join(message)
        if self.__console_logging:
            print(log_message)
        if self.__file_logging:
            self.__logger.debug(f"{log_message}")

    def add_event_listener(self, event_type: str):
        """@Server.add_event_listener(event_type)
         def function(event: Event | SReceiveEvent):
                pass

        > Register the function as an event listener.\n
        > 'event_type' must be a valid event ("on_join", "on_quit", "on_receive") 
        or (EventType.ON_JOIN, EventType.ON_QUIT, EventType.ON_RECEIVE)\n
        > If the 'event_type' is 'on_receive' the parameter 'event' is an instance of SReceiveEvent,
        otherwise the parameter 'event' is an instance of SEvent."""

        def decorator(listener: Callable):
            if event_type not in self.__events.keys():
                raise SimplyServerException(
                    f"The specified event name '{event_type}' is not a valid event")
            self.__events[event_type] = listener
            def wrapper(*args, **kwargs):
                return listener(*args, **kwargs)
            return wrapper
        return decorator
    
    def add_command_listener(self, command: str, prefix: str = ""):
        """@Server.add_command_listener(command)
         def function(event: SReceiveCommand):
                pass

        > Register the function as an command listener.\n
        > Whenever a client send data which start with the 'command' the function will be called.\n
        > 'event' is an instance of SReceiveCommand."""
        command = prefix + command
        def decorator(listener: Callable):
            self.__commands[command] = listener
            def wrapper(*args, **kwargs):
                return listener(*args, **kwargs)
            return wrapper
        return decorator

    def is_running(self) -> bool:
        """Server.is_running()

        > Return True or False if the server is started or not."""

        return self.__running

    def kick(self, client_to_kick: Union['SClient', int]):
        """Server.kick(client_to_kick)

        > Kick the 'client_to_kick' from the server."""

        if isinstance(client_to_kick, int):
            client_to_kick = self.connected_clients[client_to_kick]
        client_to_kick.close()

    @property
    def bufsize(self) -> int:
        """Server.bufsize -> int

        > Return the receive bufsize of the server."""

        return self.__bufsize

    @bufsize.setter
    def bufsize(self, bufsize: int) -> None:
        """Server.bufsize = bufsize

        > Set the receive bufsize to 'bufsize'."""

        self.__bufsize = bufsize

    @property
    def connected_clients(self) -> dict[int, 'SClient']:
        """Server.connected_clients -> dict(int, Client)

        > Return all the clients connected to the server maped with their ids."""

        return self.__connected_clients
    
    @property
    def registered_commands(self) -> Iterable:
        """Server.registered_commands -> dict(str, Callable)

        > Return all the registered commands."""

        return self.__commands.keys()

    @property
    def name(self) -> str:
        """Server.name -> str

        > Return the name of the server."""

        return self.__name

    @property
    def addr(self) -> Addr:
        """Server.addr -> Addr

        > Return the address of the server."""

        return self.__addr
    
    @property
    def log_path(self) -> str:
        """Server.log_path -> str

        > Return the log path of the server."""

    @log_path.setter
    def log_path(self, log_path: str) -> None:
        """Server.log_path = log_path

        > Set the file where the server is logging.\n
        > If 'log_path' is None, the server will not create and log into a file,
        file_logging and custom_file_logging are set to False.\n
        > Otherwise, if 'log_path' is not None, the server will create and log 
        into the specified file, but not set file_logging and 
        custom_file_logging to True."""

        if log_path is None:
            self.__log_path = None
            self.__file_logging = False
            self.__custom_file_logging = False
        else:
            if self.__logger.hasHandlers():
                self.__logger.removeHandler(self.__logger.handlers[0])
            if isdir(log_path):
                self.__logger.addHandler(logging.FileHandler(
                    log_path + f"/{self.__name}.log", mode="a+"))
            else:
                try:
                    self.__logger.addHandler(
                        logging.FileHandler(log_path, mode="a+"))
                except:
                    raise SimplyServerException(
                        f"'{log_path}' is not a valid path")
            self.__log_path = log_path

    @property
    def logging(self) -> tuple[bool, bool]:
        """Server.logging -> tuple(file_logging, console_logging)

        > Return the 'file_logging' state and the 'console_logging' state."""

        return (self.__file_logging, self.__console_logging)
    
    @logging.setter
    def logging(self, file_logging: bool, console_logging: bool) -> None:
        """Server.logging = file_logging, console_logging

        > Set the file_logging to 'file_logging' and the console_logging to 'console_logging'.\n
        > Raise an exception if 'file_logging' is set to True whereas the server is not
        logging."""

        if file_logging and self.__log_path is None:
            raise SimplyServerException(
                "You can't turn on file logging when the log path is not defined")
        self.__file_logging = file_logging
        self.__console_logging = console_logging

    @property
    def custom_logging(self) -> tuple[bool, bool]:
        """Server.custom_logging -> tuple(custom_file_logging, custom_console_logging)

        > Return the 'custom_file_logging' state and the 'custom_console_logging' state."""

        return (self.__custom_file_logging, self.__custom_console_logging)
    
    @custom_logging.setter
    def custom_logging(self, custom_file_logging: bool, custom_console_logging: bool) -> None:
        """Server.custom_logging = custom_file_logging, custom_console_logging

        > Set the custom_file_logging to 'custom_file_logging' and the custom_console_logging to 'custom_console_logging'.\n
        > Raise an exception if 'custom_file_logging' is set to True whereas the server is not logging."""

        if custom_file_logging and self.__log_path is None:
            raise SimplyServerException(
                "You can't turn on custom file logging when the log path is not defined")
        self.__custom_file_logging = custom_file_logging
        self.__custom_console_logging = custom_console_logging

    @property
    def is_running(self) -> bool:
        """Server.is_running -> bool

        > Return the running state of the server."""

        return self.__running


# --------------------- Client --------------------- #

class SClient:

    def __init__(self, id: int, server: 'Server', conn: socket.socket, addr: 'Addr', bufsize: int) -> None:

        self.__id = id
        self.__server = server
        self.__conn = conn
        self.__addr = addr
        self.__format = 'utf-8'
        self.__running = False
        self.__bufsize = bufsize
        self.__rest = b''

    def __repr__(self) -> str:

        return f"<client ip={self.__addr.ip} port={self.__addr.port} server={self.__server.name}>"

    def __listen(self) -> None:

        while self.__running:

            try:
                received_packets = self.__conn.recv(self.__bufsize)
                rest = self.__rest
                *packets, self.__rest = received_packets.split(b"\0")
                if len(packets) > 0:
                    packets[0] = rest + packets[0]
                    for packet in packets:
                        is_command = False
                        if packet.startswith(b"[STR-DATA]"): 
                            packet = packet.decode(self.__format).removeprefix("[STR-DATA]")
                            for command in self.__server.registered_commands:
                                if packet.startswith(command):
                                    is_command = True
                                    self.__server._enqueue_command(command, self, packet.split()[1:])
                                    break
                        if not is_command:
                            self.__server._enqueue_event(EventType.ON_RECEIVE, self, packet)
                else:
                    self.__rest = rest + self.__rest
            except UnicodeDecodeError as e:
                self.__rest = ''
            except Exception as e:
                if e.args[0] not in [10053, 10054, 10058, 10038]:
                    print(e)
                self.close()
                return

    def listen(self) -> None:
        """Client.listen()

        > Make the client listening if it is not already listening, otherwise does nothing."""

        if self.__running:
            return
        receive_thread = Thread(target=self.__listen)
        self.__running = True
        receive_thread.start()

    def close(self) -> None:
        """Client.close()

        > Close the client if it is not already closed, otherwise does nothing."""

        if not self.__running:
            return
        self.__server._enqueue_event(EventType.ON_QUIT, self)
        self.__running = False
        self.__server.connected_clients.pop(self.id)
        self.__conn.close()
        self.__server.log(
            f"Client disconnects on port {self.__addr.port}...", log_formating=False)

    def send(self, payload: AnyStr) -> None:
        """Client.send()

        > Send the payload to the connected client.\n
        > The payload must be a string or bytes."""

        if isinstance(payload, bytes):
            self.__conn.send(payload)
        else:
            payload = "[STR-DATA]" + payload
            self.__conn.send(payload.encode(self.__format))

    @property
    def id(self) -> int:
        """Client.id -> int

        > Return the id of the client."""

        return self.__id
    
    @id.setter
    def id(self, id: int) -> None:
        """Client.id = id

        > Set the id of the client.\n
        > 'id' must have 6 digits and not used by another client else this won't change the id."""

        if self.__server._check_valid_id(id):
            self.__id = id

    @property
    def bufsize(self) -> int:
        """Client.bufsize -> int

        > Return the receive bufsize of the client."""

        return self.__bufsize

    @bufsize.setter
    def bufsize(self, bufsize: int) -> None:
        """Client.bufsize = bufsize

        > Set the receive bufsize to 'bufsize'."""

        self.__bufsize = bufsize

    @property
    def addr(self) -> Addr:
        """Client.addr -> Addr

        > Return the addr of the client."""

        return self.__addr
