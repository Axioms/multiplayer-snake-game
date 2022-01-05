import asyncio
import websockets
import json


class WebSocketClient():

    def __init__(self):
        pass

    async def connect(self, uri):
        self.conn = await websockets.client.connect(uri)
        if self.conn.open:
            print('Connection stablished. Client correcly connected')
            return self.conn

    async def send(self, msg):
        await self.conn.send(json.dumps(msg))

    async def receive(self, conn):
        try:
            msg = await conn.recv()
            msg = json.loads(msg)
            return msg
        except websockets.exceptions.ConnectionClosed:
            print('Connection with server closed')

    async def receive_once(self, conn):
        try:
            msg = await conn.recv()
            msg = json.loads(msg)
            return msg
        except websockets.exceptions.ConnectionClosed:
            print("Connection with server closed")