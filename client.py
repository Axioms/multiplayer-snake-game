import tkinter, time, random, sys, math, asyncio, json, threading, nest_asyncio
import websockets as wss
from tkinter.colorchooser import askcolor
from websocket_client import WebSocketClient

nest_asyncio.apply()

window = tkinter.Tk()
new_url = tkinter.StringVar()
new_port = tkinter.StringVar()
join_status = tkinter.StringVar()

uuid = ""
room_code = tkinter.StringVar()
room_id = ""

uri = "ws://localhost:55555"
url = "localhost"
port = "55555"

ws_running = True
snake_alive = True

# create window and make it a fixed size
window_elements = set()
window_dimensions = [800, 800]
window.geometry(str(window_dimensions[0]) + "x" + str(window_dimensions[1]))
window.resizable(0, 0)
dead = set()

def _quit():
    global x
    global ws_running
    global client
    ws_running = False
    asyncio.get_event_loop().run_until_complete(ws_ping(client))
    x.join()
    sys.exit()


# set window title
window.title("Multiplayer Snake")

window.protocol("WM_DELETE_WINDOW", _quit)

fps = 12

game_screen = tkinter.Canvas(
    window, width=window_dimensions[0], height=window_dimensions[1], bd=0, highlightthickness=0
)


game_screen.pack()

game_scaling = 25

game_dim = [int(window_dimensions[0] / game_scaling),
            int(window_dimensions[1] / game_scaling)]

def gen_color():
    random_number = random.randint(0,16777215)
    hex_number = str("%06x" % random.randint(0, 0xFFFFFF))
    hex_number ='#'+ hex_number
    return hex_number

players = []
hex_color = gen_color()
player = ["", [0,0], [], [0,1], hex_color]
fruit = []
max_fruit = 1
is_lobby_creater = False

velocity_changed_this_frame = False

def create_grid_item(coords, hexcolor):
    game_screen.create_rectangle(coords[0] * game_scaling, coords[1] * game_scaling, (coords[0] + 1) * game_scaling,
                                 (coords[1]+1) * game_scaling, fill=hexcolor[4], outline="#23272A", width=3)

def create_start_menu():
    delete_window_items()
    draw_grid()
    label1 = tkinter.Label(window, text="Multiplayer Snake", font=("Arial", 25), bg='#23272A')
    label1.place(x=window_dimensions[0]/2 - window_dimensions[0]/8, y=window_dimensions[1]/6)

    btn1 = tkinter.Button(window, text="Create Lobby",
                          command=create_lobby_menu, font=("Arial", 10))
    btn1.place(x=int(window_dimensions[0]/2-50), y=int(window_dimensions[1]/3))

    btn2 = tkinter.Button(window, text="Join Lobby",
                          command=join_lobby_menu, font=("Arial", 10))
    btn2.place(x=int(window_dimensions[0]/2-45),
               y=int(window_dimensions[1]/2.5))
    """ 
    btn3 = tkinter.Button(window, text="Settings", command=create_options_menu)
    btn3.place(x=int(window_dimensions[0]/2-40),
               y=int(window_dimensions[1]/2.15))
    """
    window_elements.add(label1)
    window_elements.add(btn1)
    window_elements.add(btn2)
    #window_elements.add(btn3)


def close_options():
    global new_url, new_port, port, url, uri, conn
    temp_url = new_url.get()
    temp_port = new_port.get()
    if (temp_url != ""):
        url = temp_url
    if (temp_port != ""):
        port = temp_port

    uri = "ws://" + url + ":" + port
    delete_window_items()
    create_start_menu()
    return


def create_options_menu():
    global new_port, new_url
    delete_window_items()

    label1 = tkinter.Label(
        window, text="Change Server IP. Current Server is \"" + url + "\": ")
    label1.place(x=100, y=50)

    new_url = tkinter.Entry(window, width=15, textvariable=new_url)
    new_url.place(x=100, y=70)

    label2 = tkinter.Label(
        window, text="Change Server Port. Current Port is \"" + port + "\": ")
    label2.place(x=100, y=100)

    new_port = tkinter.Entry(window, width=15, textvariable=new_port)
    new_port.place(x=100, y=120)

    btn = tkinter.Button(window, text="Save", command=close_options)
    btn.place(x=int(window_dimensions[0]/2-40),
              y=int(window_dimensions[1]/2.15))

    window_elements.add(label1)
    window_elements.add(label2)
    window_elements.add(new_url)
    window_elements.add(new_port)
    window_elements.add(btn)

def callback(label):
    global player
    result = askcolor(title = "Pick Snake Color")
    label.configure(fg = result[1])
    player[4] = result[1]
    asyncio.get_event_loop().run_until_complete(ws_send_update_player(client))

def create_lobby_menu():
    global room_code
    global player
    global is_lobby_creater
    delete_window_items()
    is_lobby_creater = True
    asyncio.get_event_loop().run_until_complete(ws_create_room(client))
    label1 = tkinter.Label(window, textvariable=room_code, font=("Arial", 25), bg='#23272A')
    label1.place(x=window_dimensions[0]/2 - window_dimensions[0]/5, y=window_dimensions[1]/6)
    
    label2 = tkinter.Label(window, text="This is the snakes current color", font=("Arial", 15), bg='#23272A')
    label2.place(x=window_dimensions[0]/1.9 - window_dimensions[0]/5, y=window_dimensions[1]/4)
    label2.config(fg=player[4])
    
    btn1 = tkinter.Button(window, text="pick snake color", command=lambda:callback(label2))
    btn1.place(x=window_dimensions[0]/2 - window_dimensions[0]/10, y=window_dimensions[1]/2.5)
    
    btn2 = tkinter.Button(window, text="start game", command=start_game)
    btn2.place(x=window_dimensions[0]/2 - window_dimensions[0]/12, y=window_dimensions[1]/2.1)
    
    btn3 = tkinter.Button(window, text="Back", command=create_start_menu)
    btn3.place(x=window_dimensions[0]/2 - window_dimensions[0]/15, y=window_dimensions[1]/1.8)
    
    window_elements.add(label1)
    window_elements.add(label2)
    window_elements.add(btn1)
    window_elements.add(btn2)
    window_elements.add(btn3)


def join_lobby_menu():
    global room_code
    global room_id
    global player
    delete_window_items()
    
    label1 = tkinter.Label(window, text="Join Game", font=("Arial", 25), bg='#23272A')
    label1.place(x=window_dimensions[0]/2 - window_dimensions[0]/10, y=window_dimensions[1]/6)
    
    label2 = tkinter.Label(window, text="This is the snakes current color", font=("Arial", 15), bg='#23272A')
    label2.place(x=window_dimensions[0]/1.9 - window_dimensions[0]/5, y=window_dimensions[1]/3)
    label2.config(fg=player[4])
    
    label3 = tkinter.Label(window, textvariable=join_status, font=("Arial", 15), bg='#23272A')
    label3.place(x=window_dimensions[0]/1.9 - window_dimensions[0]/8, y=window_dimensions[1]/4)
    
    label4 = tkinter.Label(window, text="Enter room Code: ", font=("Arial", 12), bg='#23272A')
    label4.place(x=window_dimensions[0]/1.9 - window_dimensions[0]/5, y=window_dimensions[1]/2.5)
    
    room = tkinter.Entry(window, width=15, textvariable=room_code)
    room.place(x=window_dimensions[0]/1.9 - window_dimensions[0]/5, y=window_dimensions[1]/2.3)
    
    btn1 = tkinter.Button(window, text="pick snake color", command=lambda:callback(label2))
    btn1.place(x=window_dimensions[0]/1.9 - window_dimensions[0]/5, y=window_dimensions[1]/2.1)
    
    btn2 = tkinter.Button(window, text="Join", command=join_room)
    btn2.place(x=window_dimensions[0]/1.9 - window_dimensions[0]/5, y=window_dimensions[1]/1.9)
    
    btn3 = tkinter.Button(window, text="Back", command=create_start_menu)
    btn3.place(x=window_dimensions[0]/1.9 - window_dimensions[0]/5, y=window_dimensions[1]/1.75)
    
    window_elements.add(label1)
    window_elements.add(label2)
    window_elements.add(label3)
    window_elements.add(label4)
    window_elements.add(room)
    window_elements.add(btn1)
    window_elements.add(btn2)
    window_elements.add(btn3)

def delete_window_items(remove_ws=True):
    global window_elements
    global is_lobby_creater
    for x in window_elements:
        x.destroy()
    window_elements.clear()
    
    if(room_id != "" and remove_ws):
        asyncio.get_event_loop().run_until_complete(ws_leave_room(client))
        is_lobby_creater = False

def draw_grid():
    velocity_changed_this_frame = False
    # draw background
    game_screen.create_rectangle(
        0, 0, window_dimensions[0], window_dimensions[1], fill="#23272A", outline="#23272A"
    )
    temp_itter = 0
    while (temp_itter <= window_dimensions[0]+game_dim[0]):
        game_screen.create_line(temp_itter, 0, temp_itter, window_dimensions[1], width=1, fill='#2C2F33')
        game_screen.create_line(0, temp_itter, window_dimensions[0], temp_itter, width=1, fill='#2C2F33')
        temp_itter += game_dim[0] * 0.78
    
    game_screen.create_line(
        window_dimensions[0], 0, window_dimensions[0], window_dimensions[1], width=2, fill='#2C2F33')
    game_screen.create_line(
        0, window_dimensions[1], window_dimensions[0], window_dimensions[1], width=2, fill='#2C2F33')

def game_drawer():
    global fps
    global velocity_changed_this_frame
    global game_screen
    global game_dim
    global window_dimensions
    global players
    global player
    global fruit
    global uuid
    global snake_alive
    global dead
    
    window.after(int(1000/fps), game_drawer)
    velocity_changed_this_frame = False
    game_screen.delete("all")
    # draw background
    game_screen.create_rectangle(
        0, 0, window_dimensions[0], window_dimensions[1], fill="#23272A", outline="#23272A"
    )

    # draw grid lines
    draw_grid()
    if (snake_alive):
        # append head to tail
        player[2].append([player[1][0], player[1][1]])
        
        player[1][0] += player[3][0]
        player[1][1] += player[3][1]
        
        if (player[1][0] == game_dim[0]):
            player[1][0] = 0
        elif (player[1][0] == -1):
            player[1][0] = game_dim[0] - 1
        elif (player[1][1] == game_dim[1]):
            player[1][1] = 0
        elif (player[1][1] == -1):
            player[1][1] = game_dim[1] - 1
            
    for x in fruit:
        create_grid_item(x, ("","","","","#ff0000"))
    
    for x in players:
        asyncio.get_event_loop().run_until_complete(ws_send_update_player(client))
        if (x[0] == uuid):
            x = player
        for i in x[2]:
            if (snake_alive):
                if (i[0] == player[1][0] and i[1] == player[1][1]):
                    player[1] = []
                    player[2] = []
                    player[3] = [0,0]
                    window.unbind("<KeyPress>")
                    snake_alive = False
                    asyncio.get_event_loop().run_until_complete(ws_died(client))
                
                if (len(list(filter(lambda uid: uid == x[0], dead))) < 1):
                    create_grid_item(i, x)
    ate = False
    if (snake_alive):
        for x in fruit:
            if(x[0] == player[1][0] and x[1] == player[1][1]):
                asyncio.get_event_loop().run_until_complete(remove_fruit(client, x))
                ate = True
                break
    if (not ate and snake_alive):
        player[2].pop(0)
            # send updated player to server

def gen_start_cords():
    global players
    global fruit
    
    generated_coords = [random.randint(
        0, (game_dim[0] - 1)), random.randint(0, (game_dim[1] - 1))]
    for player in players:
        if (player[1][0] == generated_coords[0] and player[1][1] == generated_coords[1]):
            return gen_start_cords()
    for x in fruit:
         if (x[0] == generated_coords[0] and x[1] == generated_coords[1]):
            return gen_start_cords()
        
    return generated_coords

def onKeyDown(e):
    # declare use of global variable(s)
    global player
    global velocity_changed_this_frame

    # only handle event if velocity has not been changed in current frame
    if(velocity_changed_this_frame == False):
        # set velocity changed variable to true
        velocity_changed_this_frame = True

        # bind arrow keys to specific player velocity directions
        if((e.keysym == "Left" or e.keysym == "a") and player[3][0] != 1):
            player[3] = [-1, 0]
        elif((e.keysym == "Right" or e.keysym == "d") and player[3][0] != -1):
            player[3] = [1, 0]
        elif((e.keysym == "Up" or e.keysym == "w") and player[3][1] != 1):
            player[3] = [0, -1]
        elif((e.keysym == "Down" or e.keysym == "s") and player[3][1] != -1):
            player[3] = [0, 1]
    
        else:
            # if player velocity indeed was not changed, then revert variable back to false
            velocity_changed_this_frame = False
        #asyncio.get_event_loop().run_until_complete(ws_send_update_player(client))

async def ws_create_room(client):
    global room_code
    global uuid
    await client.send({"resource": "create room", "user id": uuid})

async def ws_ping(client):
    await client.send({"resource": "ping"})
    
async def ws_close():
    return

async def ws_join_room(client):
    global room_code
    global room_id
    global uuid
    room_id = room_code.get()
    await client.send({"resource": "join room", "request":{"room code": room_id}, "user id": uuid})

def join_room():
    global room_code
    global room_id
    global client
    global player
    
    room_id = room_code.get()
    asyncio.get_event_loop().run_until_complete(ws_join_room(client))

async def ws_update_player(msg):
    global player
    global players
    uid = msg["response"]["user id"]
    for x in players:
        if x[0] == uid:
            players.remove(x)
            players.append(msg["response"]["player"])

async def ws_died(client):
    global room_id
    global uuid
    await client.send({"resource": "update dead", "request":{"room code": room_id, "user id": uuid}})
     
async def ws_send_update_player(client):
    global player
    global room_code
    global room_id
    global uuid
    global snake_alive
    if (snake_alive):
        await client.send({"resource": "update player", "request":{"room code": room_id, "player": player}, "user id": uuid})
    
async def ws_leave_room(client):
    global uuid
    global room_id
    await client.send({"resource":"leave room", "request":{"room code": room_id}, "user id": uuid})
    room_id = ""
    room_code.set("")

def start_game():
    global client
    asyncio.get_event_loop().run_until_complete(ws_start_game(client))

async def init_fruit(client):
    global max_fruit
    i = 0
    while (i < max_fruit):
        await add_fruit(client)
        i += 1
    return

def get_fruit_cords():
    global players
    global fruit
    
    generated_coords = [random.randint(
        0, (game_dim[0] - 1)), random.randint(0, (game_dim[1] - 1))]
    for player in players:
        for tail in player[2]:
            if (tail[0] == generated_coords[0] and player[1] == generated_coords[1]):
                return gen_start_cords()
    for x in fruit:
         if (x[0] == generated_coords[0] and x[1] == generated_coords[1]):
            return gen_start_cords()
        
    return generated_coords

async def add_fruit(client):
    global room_id
    cords = get_fruit_cords()
    await client.send({"resource":"add fruit", "request": {"room code": room_id, "fruit cords": cords}})

async def remove_fruit(client, cords):
    global room_id
    await client.send({"resource":"remove fruit", "request": {"room code": room_id, "fruit cords": cords}})
    await add_fruit(client)

async def ws_start_game(client):
    global room_id
    await client.send({"resource":"start game", "request":{"room code": room_id}})

async def ws_connect(client, conn):
    global uuid
    global room_code
    global room_id
    global player
    global join_status
    global fruit
    global max_fruit
    global dead
    global is_lobby_creater
    
    await client.send({"resource": "register player"})

    global ws_running, players
    while (ws_running == True):
        msg = await client.receive(conn)
        if (msg["resource"] == "settings update"):
            players = msg["response"][4]
            max_fruit = msg["response"][1]
            fruit = msg["response"][3]
        elif (msg["resource"] == "update player"):
            await ws_update_player(msg)
        elif (msg["resource"] == "update fruit"):
            fruit = msg["response"]
        elif (msg["resource"] == "create room"):
            room_code.set("The room code is " + msg["response"]["room code"])
            room_id = msg["response"]["room code"]
            player = msg["response"]["player"]
            player[4] = hex_color
            start_cords = gen_start_cords()
            player[1] = start_cords
            await ws_send_update_player(client)
            await init_fruit(client)
        elif (msg["resource"] == "join room"):
            if (msg["response"]["success"] == True):
                player = msg["response"]["player"]
                join_status.set("Joined room!!!")
                player[4] = hex_color
                start_cords = gen_start_cords()
                player[1] = start_cords
                await ws_send_update_player(client)
            else:
                join_status.set("Invalid room code")
        elif (msg["resource"] == "register player"):
            uuid = msg["response"]
        elif(msg["resource"] == "start game"):
            delete_window_items(False)
            game_drawer()
        elif(msg["resource"] == "update dead"):
            dead.add(msg["response"]["user id"])
        else:
            a = 1
            #print(msg)


client = WebSocketClient()
loop = asyncio.get_event_loop()
conn = loop.run_until_complete(client.connect(uri))

def ws_test(loop, client, conn):
    asyncio.set_event_loop(loop)
    asyncio.get_event_loop().run_until_complete(ws_connect(client, conn))


x = threading.Thread(target=ws_test, args=(loop, client, conn))

window.bind("<KeyPress>", onKeyDown)
x.start()



class DevNull:
    def write(self, msg):
        pass

sys.stderr = DevNull()

#game_drawer()
create_start_menu()

window.mainloop()
