# SimplyServer

Create simple servers quickly in python!

Simple exemple : 
```python
from simplyserver import *

server = Server('example')
server.start()

@server.add_event_listener(EventType.ON_JOIN)
def on_join(event: SEvent):
   server.broadcast(f'SERVER : Client has connected on port {event.client.addr.port}')
    
@server.add_event_listener(EventType.ON_RECEIVE)
def on_receive(event: SReceiveEvent):
   server.broadcast(f'CLIENT({event.client.id}) : {event.data}', event.client)

@server.add_command_listener('kick', '/')
def kick(command: SReceiveCommand):
   server.kick(int(command.args[0]))
```