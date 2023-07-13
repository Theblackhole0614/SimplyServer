
class Addr:

    def __init__(self, ip: str, port: int) -> None:

        self.ip: str = ip
        self.port: int = port
        self.formated: tuple[str, int] = (ip, port)


class EventType:

    ON_JOIN = "on_join"
    ON_QUIT = "on_quit"
    ON_RECEIVE = "on_receive"


class SimplyServerException(Exception):

    def __init__(self, error_message):

        super().__init__(error_message)
