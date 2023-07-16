# SimplyServer

Create simple servers quickly in python!

Simple exemple : 
```python
import simplyserver

server = simplyserver.Server('example')
server.start()

@server.event_listener
def on_join(event: simplyserver.SEvent):
   server.broadcast(f'Client joined on port {event.client.get_addr().port}')
```