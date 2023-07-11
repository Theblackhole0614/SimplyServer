
# Created by TheBlackHole
# You can contact me on discord -> HORLOGE-TheBlackHole

# If you are a beginner in py network I advise you to go see the links below
# https://docs.python.org/3/library/socket.html (English)
# https://python.doctor/page-reseaux-sockets-python-port (French)

# -------------------- Imports -------------------- #

import socket, logging
from threading import Thread
from os.path import isdir
from time import strftime, localtime
from re import sub
from typing import Optional, Callable, AnyStr, List, Any, Iterable, ByteString
from queue import Queue

# ------------------ Declarations ----------------- #

class SimplyServerException(Exception): ...
class Events: ...
class Server: ...
class Client: ...

# ------------------- Exception ------------------- #

class SimplyServerException(Exception):
	def __init__(self, error_message):
		super().__init__(error_message)

# --------------------- Events -------------------- #

class Addr:
	
    def __init__(self, ip: str, port: int) -> None:
        self.ip: str = ip
        self.port: int = port
        self.formated: tuple[str, int] = (ip, port)

class Events:

	ON_JOIN = "on_join"
	ON_QUIT = "on_quit"
	ON_RECEIVE = "on_receive"

class Event:

	def __init__(self, server: Server, client: Client):

		self.server: Server = server
		self.client: Client = client

class MessageEvent(Event):

	def __init__(self, server: Server, client: Client, message: AnyStr):

		super().__init__(server, client)
		self.message: AnyStr = message

# --------------------- Server -------------------- #

class Server:

	def __init__(self, name: str, ip: Optional[str]="localhost", port: Optional[int]=5050, log_path: Optional[str]=".", custom_file_logs: Optional[bool]=True, custom_console_logs: Optional[bool]=True, bufsize: Optional[int]=128) -> None:

		self.__name = sub("\W", "_", name)
		self.__ADDR = Addr(ip, port)
		self.__log_path = log_path
		self.__file_logging = True
		self.__console_logging = True
		self.__LOGGER = logging.getLogger(__name__)
		self.__LOGGER.setLevel("DEBUG")
		self.set_log_path(self.__log_path)
		self.__custom_file_logging = custom_file_logs
		self.__custom_console_logging = custom_console_logs
		self.__bufsize = bufsize
		self.__events = {Events.ON_JOIN: None, Events.ON_QUIT: None, Events.ON_RECEIVE: None}
		self.__QUEUE = Queue(0)
		self.__running = False 
		self.__listening = False
		self.__processing = False
		self.__connected_clients = []

	def __repr__(self) -> str:

		return f"<server name={self.__name} ip={self.__ADDR.port} port={self.__ADDR.port} is_running={self.__running}>"

	def __listen(self) -> None:

		while self.__listening:

			try:
				conn, addr = self.__SERVER.accept()
				self.log(f"Client connects on port {self.__ADDR.port}...", log_formating=False)
			except Exception as e:
				self.stop()
				return

			new_client = Client(self, conn, Addr(addr[0], addr[1]), self.__bufsize)
			self.__connected_clients.append(new_client)
			new_client.listen()
			self._enqueue_event(Events.ON_JOIN, new_client)

	def __process_events(self) -> None:

		while self.__processing:

			event_name, client, *payload = self.__QUEUE.get(block=True)
			if event_name == Events.ON_RECEIVE: 
				event = MessageEvent(self, client, payload[0])
			else:
				event = Event(self, client)
			if self.__events[event_name] != None: self.__events[event_name](event)
			self.__QUEUE.task_done()

	def _enqueue_event(self, event: int, client: Client, payload: Optional[Any]=None) -> None:

		self.__QUEUE.put((event, client, payload))

	def start(self) -> None:
		"""Server.start()

		> Start the server if it is not already started, otherwise does nothing."""

		if self.__running: return

		self.__running = True
		if self.__custom_file_logging: self.__LOGGER.debug("\n>> Server launch <<")

		self.__SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.__SERVER.bind(self.__ADDR.formated)
		self.__SERVER.listen()

		listen_thread = Thread(target=self.__listen)
		self.__listening = True
		listen_thread.start()

		self.log(f"Server is listening on port {self.__ADDR.port}...", log_formating=False)
		
		event_thread = Thread(target=self.__process_events)
		self.__processing = True
		event_thread.start()

	def stop(self) -> None:
		"""Server.stop()

		> Stop the server if it is not already stoped, otherwise does nothing."""

		if not self.__running: return

		self.__running = False

		if self.__listening:

			self.__listening = False
			self.__SERVER.close()

		connected_clients = self.__connected_clients.copy()
		for client in connected_clients: 
			client.close()

		self.__QUEUE.join()
		self.__processing = False

	def broadcast(self, message: AnyStr, excluded_client: Optional[Client | Iterable[Client]]=None) -> None:
		"""Server.broadcast(message, excluded_client)

		> Send the 'message' to all connected clients except 'excluded_client'. 
		> 'excluded_client' can be a single client or a list | tuple of clients."""

		if self.__running: 
			
			if type(excluded_client) is Client: excluded_client = [excluded_client]

			for client in self.__connected_clients:
					if excluded_client != None: 
						if client in excluded_client: continue
					client.send(message)
					
	def log(self, *message: object, log_formating: Optional[bool]=True) -> None:
		"""Server.log(message, log_formating=True)

		> Log the 'message' into the console if console_logging is True.
		> Log the 'message' into the log file if file_logging is True.
		> Add '[date] [time] [server name]' before 'message' if 'log_formating' is True."""

		if log_formating:
			log_message = f"{strftime('[%Y-%m-%d] [%H:%M:%S]', localtime())} [{self.__name.upper()}] {' '.join(message)}"
		else:
			log_message = ' '.join(message)
		if self.__console_logging: print(log_message)
		if self.__file_logging: self.__LOGGER.debug(f"{log_message}")

	def event_listener(self, listener: Callable):
		"""@Server.event_listener
		def event_name(event: Event | MessageEvent):
			pass

		> Register the function 'event_name' as an event.
		> 'event_name' must be a valid event ("on_join", "on_quit", "on_message"). 
		> If the 'event_name' is 'on_message' the 'event' is an instance of MessageEvent, 
		otherwise the 'event' is an instance of Event."""

		if listener.__name__ not in self.__events.keys():
			raise SimplyServerException(f"The specified event name '{listener.__name__}' is not a valid event")
		self.__events[listener.__name__] = listener

	def is_running(self) -> bool:
		"""Server.is_running()

		> Return True or False if the server is started or not."""

		return self.__running

	def set_log_path(self, log_path: str) -> None:
		"""Server.set_log_path(log_path)

		> Set the file where the server is logging.
		> If 'log_path' is None, the server will not create and log into a file,
		file_logging and custom_file_logging are set to False.
		> Otherwise, if 'log_path' is not None, the server will create and log 
		into the specified file, but not set file_logging and 
		custom_file_logging to True."""

		if log_path is None:
			self.__log_path = None
			self.__file_logging = False
			self.__custom_file_logging = False
		else:
			if self.__LOGGER.hasHandlers(): self.__LOGGER.removeHandler(self.__LOGGER.handlers[0])
			if isdir(log_path): 
					self.__LOGGER.addHandler(logging.FileHandler(log_path + f"/{self.__name}.log", mode="a+"))
			else:
				try:
					self.__LOGGER.addHandler(logging.FileHandler(log_path, mode="a+"))
				except:
					raise SimplyServerException(f"'{log_path}' is not a valid path")
			self.__log_path = log_path

	def set_logging(self, file_logging: bool, console_logging: bool) -> None:
		"""Server.set_logging(file_logging, console_logging)

		> Set the file_logging to 'file_logging' and the console_logging to 'console_logging'.
		> Raise an exception if 'file_logging' is set to True whereas the server is not
		logging."""

		if file_logging and self.__log_path is None: 
			raise SimplyServerException("You can't turn on file logging when the log path is not defined")
		self.__file_logging = file_logging
		self.__console_logging = console_logging

	def set_custom_logging(self, custom_file_logging: bool, custom_console_logging: bool) -> None:
		"""Server.set_custom_logging(custom_file_logging, custom_console_logging)

		> Set the custom_file_logging to 'custom_file_logging' and the custom_console_logging to 'custom_console_logging'.
		> Raise an exception if 'custom_file_logging' is set to True whereas the server is not logging."""

		if custom_file_logging and self.__log_path is None: 
			raise SimplyServerException("You can't turn on custom file logging when the log path is not defined")
		self.__custom_file_logging = custom_file_logging
		self.__custom_console_logging = custom_console_logging

	def set_bufsize(self, bufsize: int) -> None:
		"""Server.set_bufsize(bufsize)

		> Set the receive bufsize to 'bufsize'."""

		self.__bufsize = bufsize

	def get_conected_clients(self) -> list[Client]:
		"""Server.get_conected_clients() -> list(Client)

		> Return all the clients connected to the server."""

		return self.__connected_clients

	def get_name(self) -> str:
		"""Server.get_name() -> str

		> Return the name of the server."""

		return self.__name

	def get_addr(self) -> Addr:
		"""Server.get_addr() -> Addr

		> Return the address of the server."""

		return self.__ADDR

	def get_logging(self) -> tuple[bool, bool]:
		"""Server.get_logging() -> tuple(file_logging, console_logging)

		> Return the 'file_logging' state and the 'console_logging' state."""

		return (self.__file_logging, self.__console_logging)

	def get_custom_logging(self) -> tuple[bool, bool]:
		"""Server.get_custom_logging() -> tuple(custom_file_logging, custom_console_logging)

		> Return the 'custom_file_logging' state and the 'custom_console_logging' state."""

		return (self.__custom_file_logging, self.__custom_console_logging)

	def get_bufsize(self, bufsize: int) -> None:
		"""Server.get_bufsize() -> int

		> Return the receive bufsize of the server."""

		return self.__bufsize


# --------------------- Client --------------------- #

class Client:

	def __init__(self, server: Server, conn: socket.socket, addr: Addr, bufsize: int) -> None:

		self.__SERVER = server
		self.__CONN = conn
		self.__ADDR = addr
		self.__FORMAT = 'utf-8'
		self.__running = False
		self.__bufsize = bufsize
		self.__rest = ''

	def __repr__(self) -> str:

		return f"<client ip={self.__ADDR.ip} port={self.__ADDR.port} server={self.__SERVER.get_name()}>"

	def __listen(self) -> None:

		while self.__running:

			try:
				received_packets = self.__CONN.recv(self.__bufsize).decode(self.__FORMAT)
				rest = self.__rest
				*packets, self.__rest = received_packets.split("\0")
				if len(packets) > 0:
					packets[0] = rest + packets[0]
					for packet in packets:
						self.__SERVER._enqueue_event(Events.ON_MESSAGE_RECEIVE, self, packet)
				else:
					self.__rest = rest + self.__rest
			except UnicodeDecodeError as e:
				self.__rest = ''
			except Exception as e:
				if e.args[0] not in [10054, 10058, 10038]:
					print(e)
				self.close()
				return

	def listen(self) -> None:
		"""Client.listen()

		> Make the client listening if it is not already listening, otherwise does nothing."""

		if self.__running: return 
		receive_thread = Thread(target=self.__listen)
		self.__running = True
		receive_thread.start()

	def close(self) -> None:
		"""Client.close()

		> Close the client if it is not already closed, otherwise does nothing."""

		if not self.__running: return
		self.__SERVER._enqueue_event(Events.ON_QUIT, self)
		self.__running = False
		self.__SERVER.get_conected_clients().remove(self)
		self.__CONN.close()
		self.__SERVER.log(f"Client disconnects on port {self.__ADDR.port}...", log_formating=False)

	def send(self, payload: AnyStr) -> None:
		"""Client.send()

		> Send the payload to the connected client.
		> The payload must be a string or bytes."""

		if isinstance(payload, bytes):
			self.__CONN.send(payload)
		else:
			self.__CONN.send(payload.encode(self.__FORMAT))

	def set_bufsize(self, bufsize: int) -> None:
		"""Client.set_bufsize(bufsize)

		> Set the receive bufsize to 'bufsize'."""

		self.__bufsize = bufsize

	def get_bufsize(self) -> int:
		"""Client.get_bufsize() -> int

		> Return the receive bufsize of the client."""

		return self.__bufsize
	
	def get_addr(self) -> Addr:
		"""Client.get_addr() -> Addr

		> Return the addr of the client."""

		return self.__ADDR
		