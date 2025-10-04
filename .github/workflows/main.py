# main.py
# Car Race - Single file Kivy app (single player / local 2 players / simple network client)
# Requirements: kivy
# Run: python main.py

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, DictProperty
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
import socket, threading, json, time

KV = r'''
#:kivy 2.1.0

<RootWidget>:
    MenuScreen:
        name: "menu"
    GameScreen:
        name: "game"

<MenuScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: 24
        spacing: 18
        canvas.before:
            Color:
                rgba: 0.05,0.05,0.12,1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "🏎️ لعبة سباق - اختر وضع اللعب"
            font_size: "26sp"
            size_hint_y: 0.18
            halign: "center"
            valign: "middle"
        BoxLayout:
            orientation: "vertical"
            spacing: 12
            size_hint_y: 0.6
            Button:
                text: "لاعب واحد (Single Player)"
                size_hint_y: None
                height: "48dp"
                on_release:
                    app.root.current = "game"; app.root.get_screen("game").mode = "single"; app.root.get_screen("game").on_pre_enter()
            Button:
                text: "لعب محلي لشخصين (نفس الجهاز)"
                size_hint_y: None
                height: "48dp"
                on_release:
                    app.root.current = "game"; app.root.get_screen("game").mode = "local2"; app.root.get_screen("game").on_pre_enter()
            Button:
                text: "شبكي (Client) - اتصل بسيرفر"
                size_hint_y: None
                height: "48dp"
                on_release:
                    app.root.current = "game"; 
                    app.root.get_screen("game").mode = "network";
                    app.root.get_screen("game").on_pre_enter()
        Label:
            text: "ملاحظة: وضع الشبكة يحتاج سيرفر TCP يستقبل JSON على بورت 5001 (اختياري)."
            font_size: "12sp"
            size_hint_y: 0.22

<GameScreen>:
    mode: "single"
    BoxLayout:
        orientation: "vertical"
        canvas.before:
            Color:
                rgba: 0.06,0.12,0.06,1
            Rectangle:
                pos: self.pos
                size: self.size
        RelativeLayout:
            id: playfield
            canvas.before:
                Color:
                    rgba: 0.12,0.12,0.12,1
                Rectangle:
                    pos: self.x + root.width*0.15, self.y
                    size: root.width*0.7, root.height
            # Player 1 car (red)
            Widget:
                id: car1
                size: 60, 90
                pos: root.p1_x, root.p1_y
                canvas:
                    Color:
                        rgba: 1,0,0,1
                    Rectangle:
                        pos: self.pos
                        size: self.size
            # Player 2 car (blue)
            Widget:
                id: car2
                size: 60, 90
                pos: root.p2_x, root.p2_y
                canvas:
                    Color:
                        rgba: 0,0,1,1
                    Rectangle:
                        pos: self.pos
                        size: self.size

        BoxLayout:
            size_hint_y: 0.28
            spacing: 6
            padding: 6
            BoxLayout:
                orientation: "vertical"
                size_hint_x: 0.5
                spacing: 6
                Label:
                    text: "Player 1 Controls"
                    size_hint_y: 0.18
                GridLayout:
                    cols: 3
                    size_hint_y: 0.82
                    Button:
                        text: "←"
                        on_press: root.p1_move(-20,0)
                    Button:
                        text: "▲"
                        on_press: root.p1_move(0,20)
                    Button:
                        text: "→"
                        on_press: root.p1_move(20,0)
                    Widget:
                    Button:
                        text: "▼"
                        on_press: root.p1_move(0,-20)
                    Widget:
            BoxLayout:
                orientation: "vertical"
                size_hint_x: 0.5
                spacing: 6
                Label:
                    text: "Player 2 Controls"
                    size_hint_y: 0.18
                GridLayout:
                    cols: 3
                    size_hint_y: 0.82
                    Button:
                        text: "A"
                        on_press: root.p2_move(-20,0)
                    Button:
                        text: "W"
                        on_press: root.p2_move(0,20)
                    Button:
                        text: "D"
                        on_press: root.p2_move(20,0)
                    Widget:
                    Button:
                        text: "S"
                        on_press: root.p2_move(0,-20)
                    Widget:
        BoxLayout:
            size_hint_y: 0.06
            spacing: 6
            padding: 6
            Button:
                text: "رجوع"
                on_release:
                    root.on_leave(); app.root.current = "menu"
            Button:
                text: "Connect to Server (network)"
                on_release:
                    if root.mode == "network": root.show_connect_popup()
'''

# ---------- Simple TCP network client (optional) ----------
class NetClient:
    def __init__(self, server_ip, server_port=5001, name="Player"):
        self.server_ip = server_ip
        self.server_port = server_port
        self.name = name
        self.sock = None
        self.running = False
        self.recv_callback = None
        self.lock = threading.Lock()

    def start(self):
        def worker():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(6)
                s.connect((self.server_ip, self.server_port))
                s.settimeout(None)
                self.sock = s
                self.running = True
                # send join
                try:
                    s.sendall(json.dumps({"action":"join","name":self.name}).encode())
                except:
                    pass
                while self.running:
                    data = s.recv(4096)
                    if not data:
                        break
                    try:
                        msg = json.loads(data.decode())
                    except:
                        continue
                    if self.recv_callback:
                        self.recv_callback(msg)
            except Exception as e:
                # silent error (network optional)
                print("NetClient error:", e)
            finally:
                self.running = False
                try:
                    if self.sock:
                        self.sock.close()
                except:
                    pass
                self.sock = None
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def send_state(self, state:dict):
        try:
            if self.sock:
                with self.lock:
                    self.sock.sendall(json.dumps({"action":"state","name":self.name,"state":state}).encode())
        except Exception as e:
            pass

    def stop(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except:
            pass

# ---------- Kivy Screens ----------
class MenuScreen(Screen):
    pass

class GameScreen(Screen):
    mode = StringProperty("single")  # single, local2, network
    p1_x = NumericProperty(0)
    p1_y = NumericProperty(0)
    p2_x = NumericProperty(0)
    p2_y = NumericProperty(0)
    running = BooleanProperty(False)
    net_client = None
    others = DictProperty({})

    def on_pre_enter(self):
        # initialize positions relative to current size
        W = self.width if self.width > 0 else 800
        H = self.height if self.height > 0 else 600
        self.p1_x = W*0.5 - 30
        self.p1_y = 50
        self.p2_x = W*0.25 - 30
        self.p2_y = 50
        self.running = True
        Clock.schedule_interval(self.update, 1/60.)

    def on_leave(self):
        self.running = False
        Clock.unschedule(self.update)
        if self.net_client:
            self.net_client.stop()
            self.net_client = None
        self.others = {}

    def update(self, dt):
        # network: send state periodically
        if self.mode == "network" and self.net_client:
            state = {"x": self.p1_x, "y": self.p1_y}
            self.net_client.send_state(state)

    def p1_move(self, dx, dy):
        self.p1_x = max(0, min(self.width-60, self.p1_x + dx))
        self.p1_y = max(0, min(self.height-100, self.p1_y + dy))

    def p2_move(self, dx, dy):
        self.p2_x = max(0, min(self.width-60, self.p2_x + dx))
        self.p2_y = max(0, min(self.height-100, self.p2_y + dy))

    def show_connect_popup(self):
        box = BoxLayout(orientation='vertical', spacing=6, padding=6)
        ip_input = TextInput(text="127.0.0.1", multiline=False, hint_text="Server IP")
        name_input = TextInput(text="Player", multiline=False, hint_text="Name")
        btn = Button(text="Connect", size_hint_y=None, height=40)
        def do_connect(instance):
            ok, msg = self.start_network(ip_input.text.strip(), name_input.text.strip() or "Player")
            popup.dismiss()
            # show small popup with result
            res_box = BoxLayout(orientation='vertical', padding=6)
            res_box.add_widget(Button(text="Result: " + ("Connected" if ok else msg), size_hint_y=None, height=40))
            pr = Popup(title="Connection", content=res_box, size_hint=(0.7,0.3))
            pr.open()
        btn.bind(on_release=do_connect)
        box.add_widget(ip_input)
        box.add_widget(name_input)
        box.add_widget(btn)
        popup = Popup(title="Server IP and Name", content=box, size_hint=(0.8,0.5))
        popup.open()

    def start_network(self, server_ip, name="Player"):
        try:
            self.net_client = NetClient(server_ip, 5001, name)
            def on_recv(msg):
                if msg.get("action") == "state":
                    nm = msg.get("name")
                    st = msg.get("state", {})
                    self.others[nm] = st
            self.net_client.recv_callback = on_recv
            self.net_client.start()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

class RootWidget(ScreenManager):
    pass

class CarRaceApp(App):
    def build(self):
        self.title = "Car Race"
        return Builder.load_string(KV)

if __name__ == "__main__":
    CarRaceApp().run()
