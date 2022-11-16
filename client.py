import socket
import threading
import queue
import ast
import sys
import time
import uuid
import json

NEEDED = 5


class Client:
    def __init__(self, port:int, neighbours:list) -> None:
        self.addr = ("127.0.0.1", port)
        self.port = port
        self.queue = queue.Queue(maxsize=100)
        self.is_ready = threading.Event()
        self.kill = threading.Event()
        self.thread = threading.Thread(target=self.start_tcp, args=(self.is_ready, self.queue, self.kill))
        self.thread.start()
        self.is_ready.wait()
        self.neighbours = {}
        self.agree = {}
        self.connected = self.get_connected(neighbours)
        self.main()


    def main(self):
        while True:
            if not self.queue.empty():
                self.message_received()
            if self.kill.is_set():
                break
            time.sleep(1)

    def message_received(self):
        while not self.queue.empty():
            (addr, message) = self.queue.get()
            addr = addr[0]
            print(message)
            message = json.loads(message.decode())
            if message == "stop\n":
                self.kill.set()
            elif message["type"] == "3":
                print(self.agree)
            elif message["type"] == "2":
                if message["id"] not in self.agree.keys():
                    self.question(message["message"], message["id"])
                else:
                    if self.is_accepted(list(self.agree.values()), message["agree"]):
                         for peer in message["agree"]:
                            if tuple(peer) not in self.agree[message["id"]]:
                                self.agree[message["id"]].append(tuple(peer))
                         self.broadcast(self.agreement, {"msg_id": message["id"], "message": message["message"]})
            elif message["type"] == "0":
                port = message["port"]
                addr = (addr, port)
                self.send_neighbours(addr, [self.addr])
                self.send_neighbours(addr, list(self.neighbours.keys()))
                self.add_neighbours([addr])
            elif message["type"] == "1":
                neighbours = message["neighbours"]
                a = []
                for i in neighbours:
                    a.append((i[0], int(i[1])))
                neighbours = a
                self.add_neighbours(neighbours)
                # if new_neighbours != []:
                #     self.broadcast(self.send_neighbours, {"neighbours": new_neighbours})
            
            else:
                message = message["message"]
                self.question(message)
    
    def is_accepted(self, me, you):
        for acceptance in me:
            if not (all(tuple(x) in acceptance for x in you)):
                return True
        return False
        
    def ping(self, addr):
        message = b"3"
        self.send_tcp(self, addr, message)

    def decision(self, message):
        return True

    def question(self, message, msg_id = uuid.uuid4().int):
        answer = self.decision(message)
        if answer:
            self.agree[msg_id] = [self.addr]
        self.broadcast(self.agreement, {"msg_id": msg_id, "message": message})
       
            

    def agreement(self, addr, msg_id, message):
        agree = False
        if self.addr in self.agree[msg_id]:
            agree = True
        message = {"type": "2", "message": message, "addr": self.addr, "agree": self.agree[msg_id], "id": msg_id}
        message = json.dumps(message).encode()
        self.send_tcp(addr, message)

    def broadcast(self, send_function, params):
        for peer in list(self.neighbours.keys()):
            send_function(peer, **params)

    def add_neighbours(self, addresses):
        new_neighbours = []
        for addr in addresses:
            if addr != self.addr:
                if addr in self.neighbours:
                    if self.neighbours[addr] + 60 < time.time():
                        new_neighbours.append(addr)
                if addr not in self.neighbours:
                    new_neighbours.append(addr)
                self.neighbours[addr] = time.time()
        if new_neighbours != []:
            self.broadcast(self.send_neighbours, {"neighbours": new_neighbours})

    def send_neighbours(self, addr, neighbours:list):
        if addr in neighbours:
            neighbours.remove(addr)
        if neighbours != []:
            message = {"type": "1", "neighbours": neighbours}
            message = json.dumps(message).encode()
            self.send_tcp(addr, message)
        
    def get_connected(self, neighbours):
        if neighbours:
            message = {"type": "0", "port": self.port}
            message = json.dumps(message).encode()
            self.send_tcp(neighbours[0], message)

    def send_tcp(self, server, message):
        if server == self.addr:
            return
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server[0], int(server[1])))
            s.sendall(message)
            s.close()

    def start_tcp(self, is_ready, msg_queue, die):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", self.port))
            s.listen(1)
            is_ready.set()
            while True:
                try:
                    conn, addr = s.accept()
                except Exception as e:
                    print(e)
                if die.is_set():
                    break
                with conn:
                    while True:
                        if not conn._closed:
                            print('Connected by', addr)
                            data = conn.recv(1024)
                            if not data: 
                                break
                            msg_queue.put((addr, data))
                            conn.close()
                        break
if len(sys.argv) == 3:
    Client(int(sys.argv[1]), [("127.0.0.1", int(sys.argv[2]))])
else:
    Client(8000, [])
