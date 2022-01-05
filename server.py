import asyncio, json, uuid, string, random
import websockets as wss
import warnings

warnings.filterwarnings('ignore')


rooms = []
connected = set()
print("starting wss server")

network_interface = "localhost"
port = 55555

async def handler(ws, path):
    async for msg in ws:
        #print(msg)
        msg = json.loads(msg)
        resource = msg["resource"]
        if  (resource == "echo"):
            await echo(msg)
        elif (resource == "add"):
            await add(msg)
        elif (resource == "register player"):
            await register_player(msg)
        elif (resource == "create room"):
            await create_room(msg, ws)
        elif (resource == "join room"):
            await join_room(msg, ws)
        elif (resource == "leave room"):
            await leave_room(msg, ws)
        elif (resource == "set spawn"):
            await set_spawn(msg)
        elif (resource == "settings update"):
            await notify_settings_change(msg)
        elif (resource == "update player"):
            await update_player(msg)
        elif (resource == "start game"):
            await start_game(msg)
        elif (resource == "test"):
            await test(msg)
        elif (resource == "ping"):
            await ping(msg)
        elif (resource == "add fruit"):
            await add_fruit(msg, ws)
        elif (resource == "remove fruit"):
            await remove_fruit(msg, ws)
        elif (resource == "update dead"):
            await update_dead(msg, ws)
        else:
            msg["response"] = "ERROR"
        if (resource != "update player" and resource != "start game" and resource != "update dead"):
            msg["request"] = None
            await ws.send(json.dumps(msg))

async def echo(msg):
    msg["response"] = msg["request"]

async def add(msg):
        msg["response"] = msg["request"][0] + msg["request"][1]
        return msg
    
async def register_player(msg):
    msg["response"] = str(uuid.uuid1())


async def create_room(msg, ws):
    hex_color = await gen_color()
    code_size = 4
    player = (msg["user id"], [0,0], [], [0,1], hex_color)
    allowed_chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    room_code = ''.join(random.choice(allowed_chars) for x in range(code_size))
    # room code, # of apples, apples left, apple locations, users (uuid, localtion, tail, valocity, color)
    rooms.append([room_code, 5, 0, [], [player], ])
    connected.add((room_code, ws))
    msg["response"] = {"room code": room_code, "player": player}
    await notify_settings_change({"request": {"room code": room_code}})
    return msg

async def join_room(msg, ws):
    hex_color = await gen_color()
    player = (msg["user id"], [0,0], [], [1,0], hex_color)
    for x in rooms:
        if x[0] == msg["request"]["room code"]:
            x[4].append(player)
            connected.add((msg["request"]["room code"], ws))
            msg["response"] = {"success": True,"player": player}
            await notify_settings_change(msg)
            return
    msg["response"] = {"success": False,"player": player}
                
async def leave_room(msg, ws):
    for x in rooms:
        if x[0] == msg["request"]["room code"]:
            if (len(x[3]) == 1):
                rooms.remove(x)
                connected.discard((msg["request"]["room code"], ws))
                #print(rooms)
                msg["response"] = True
                return
            else:
                i = 0
                while i < len(x[3]):
                    #print(x[3][i][0] == msg["user id"])
                    if(x[3][i][0] == msg["user id"]):
                        x[3].remove(x[3][i])
                        connected.discard((msg["request"]["room code"], ws))
                        msg["response"] = True
                        return
                    i+=1
    msg["response"] = False
    
async def set_spawn(msg):
    for x in rooms:
        if x[0] == msg["request"]["room code"]:
            i = 4
            while i < len(x):
                if (x[i][0] == msg["user id"]):
                    x[i][1] == msg["request"]["spawn location"]
            
                elif (x[i][1] == msg["request"]["spawn location"]):
                    msg["response"] == False
                    return
                i+=1
    msg["response"] = True
   
async def set_color(msg):
    for x in rooms:
        if x[0] == msg["request"]["room code"]:
            i = 4
            while i < len(x):
                if (x[i][0] == msg["user id"]):
                    x[i][4] == msg["request"]["color"]
                i+=1
    msg["response"] = True

async def notify_settings_change(msg):
    for ws in connected:
        if (msg["request"]["room code"] in ws):
            await asyncio.wait([ws[1].send(json.dumps({"resource":"settings update", "response": list(filter(lambda a: msg["request"]["room code"] in a[0], rooms))[0]}))])

async def update_player(msg):
    uuid = msg["user id"]
    player = msg["request"]["player"]
    for x in rooms:
        if x[0] == msg["request"]["room code"]:
            i = 4
            while i < len(x):
                if (x[i][0] == msg["user id"]):
                    x[i] == msg["request"]["player"]
                    break
                i+=1
            for ws in connected:
                if (msg["request"]["room code"] in ws):
                            await asyncio.wait([ws[1].send(json.dumps({"resource":"update player", "response":{"user id": msg["user id"], "player": msg["request"]["player"]}}))])

    #msg["response"] = True

async def start_game(msg):
    for ws in connected:
        await notify_settings_change(msg)
        if (msg["request"]["room code"] in ws):
            await asyncio.wait([ws[1].send(json.dumps({"resource":"start game", "response": True}))])
            
async def test(msg):
    for ws in connected:
        await asyncio.wait([ws[1].send(json.dumps({"resource":"exit", "response": ""}))])
        
        #await asyncio.wait([ws[1].send(json.dumps({"resource":"test", "response": rooms}))])
    msg["response"] = rooms
    return msg

async def ping(msg):
    msg["response"] = "pong"
    
async def add_fruit(msg, ws):
    for room in rooms:
        if (room[0] == msg["request"]["room code"]):
            if (room[1] > room[2]):
                room[3].append(msg["request"]["fruit cords"])
                room[2] += 1
                msg["response"] = True
                await update_fruit(msg, ws)
                return
    msg["response"] = False

async def remove_fruit(msg, ws):
    for room in rooms:
        if (room[0] == msg["request"]["room code"]):
            if (room[2] > 0):
                for i in room[3]:
                    if (i[0] == msg["request"]["fruit cords"][0] and i[1] == msg["request"]["fruit cords"][1]):
                        room[3].remove(i)
                room[2] -= 1
                msg["response"] = True
                await update_fruit(msg, ws)
                return
    msg["response"] = False
    return

async def update_fruit(msg, ws):
    global rooms
    for ws in connected:
        if (msg["request"]["room code"] in ws):
            #print("updating fruit")
            await asyncio.wait([ws[1].send(json.dumps({"resource":"update fruit", "response": list(filter(lambda a: msg["request"]["room code"] in a[0], rooms))[0][3]}))])
    return

async def update_dead(msg, ws):
    for ws in connected:
        if (msg["request"]["room code"] in ws):
            await asyncio.wait([ws[1].send(json.dumps({"resource":"update dead", "response":{"user id": msg["request"]["user id"]}}))])

async def gen_color():
    random_number = random.randint(0,16777215)
    hex_number = str("%06x" % random.randint(0, 0xFFFFFF))
    hex_number ='#'+ hex_number
    return hex_number

import sys

class DevNull:
    def write(self, msg):
        pass

sys.stderr = DevNull()

asyncio.get_event_loop().run_until_complete(
    wss.serve(handler, network_interface, port))
asyncio.get_event_loop().run_forever()