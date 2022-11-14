import socket
import threading
import queue
import ast


PORT = 8000

class Client:
    def __init__(self, neighbours:list) -> None:
        self.queue = queue.Queue(maxsize=100)
        self.is_ready = threading.Event()
        self.kill = threading.Event()
        self.thread = threading.Thread(target=self.start_tcp, args=(self.is_ready, self.queue, self.kill))
        self.thread.start()
        self.is_ready.wait()
        self.neighbours = neighbours
        self.connected = self.get_connected(self.neighbours)
        self.main()


    def main(self):
        while True:
            if not self.queue.empty():
                self.message_received()
            if self.kill.is_set():
                break

    def message_received(self):
        while not self.queue.empty():
            (addr, message) = self.queue.get()
            addr = addr[0]
            print(message)
            if message.decode() == "stop\n":
                self.kill.set()
            elif message[0] == 48:
                self.send_neighbours(addr, [addr])
                self.add_neighbours([addr])
            elif message[0] == 49:
                message = message.decode()[2:len(message)]
                neighbours = ast.literal_eval(message)
                neighbours = [n.strip() for n in neighbours]
                new_neighbours = self.add_neighbours(neighbours)
                self.broadcast(self.send_neighbours, new_neighbours)
                
    def broadcast(self, send_function, params):
        send_function(self.neighbours, **params)

    def add_neighbours(self, addresses):
        new_neighbours = []
        for addr in addresses:
            if addr not in self.neighbours:
                self.neighbours.append(addr)
                new_neighbours.append(addr)
        return new_neighbours

    def send_neighbours(self, addr, neighbours):
        message = f"1,{neighbours}".encode()
        self.send_tcp(addr, message)
        
    def get_connected(self, neighbours):
        self.send_tcp(neighbours[0], b"0")

    def send_tcp(self, server, message):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server, PORT))
            s.sendall(message)

    def start_tcp(self, is_ready, msg_queue, die):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", PORT))
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



Client(["127.0.0.1"])