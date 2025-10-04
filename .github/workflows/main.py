# main.py
import kivy
kivy.require("2.1.0")
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock
from kivy.core.window import Window
import random, time, threading, requests

# رابط Firebase (للأوضاع الجماعية فقط)
FIREBASE_DB_URL = "https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com"

Window.size = (360, 640)

KV = """
ScreenManager:
    MenuScreen:
    OfflineRaceScreen:
    LobbyScreen:
    OnlineRaceScreen:

<MenuScreen>:
    name: "menu"
    BoxLayout:
        orientation: 'vertical'
        spacing: 20
        padding: 40
        Button:
            text: "🏎 لعب فردي (بدون نت)"
            on_press: app.root.current = "offline"
        Button:
            text: "🌐 لعب جماعي (غرفة)"
            on_press: app.root.current = "lobby"

<OfflineRaceScreen>:
    name: "offline"
    BoxLayout:
        orientation: 'vertical'
        padding: 12
        spacing: 12
        Label:
            text: "وضع أوفلاين"
            size_hint_y: None
            height: 40
        Widget:
            id: track
            canvas:
                Color:
                    rgba: 0.8,0.8,0.8,1
                Rectangle:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: 0.1,0.6,0.1,1
                Rectangle:
                    pos: (root.player_x, self.center_y)
                    size: (50, 30)
        Button:
            text: "تحرك"
            size_hint_y: None
            height: 60
            on_press: root.accelerate()
        Button:
            text: "رجوع"
            size_hint_y: None
            height: 40
            on_press: app.root.current = "menu"

<LobbyScreen>:
    name: "lobby"
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 12
        Label:
            text: "اختيار وضع الغرفة"
            size_hint_y: None
            height: 40
        Button:
            text: "إنشاء غرفة"
            on_press: root.create_room()
        Button:
            text: "انضم إلى غرفة"
            on_press: root.join_room()
        Button:
            text: "رجوع"
            on_press: app.root.current = "menu"

<OnlineRaceScreen>:
    name: "online"
    BoxLayout:
        orientation: 'vertical'
        padding: 12
        spacing: 8
        Label:
            text: "🌐 وضع أونلاين"
            size_hint_y: None
            height: 40
        Widget:
            id: track
            canvas:
                Color:
                    rgba: 0.9,0.9,0.9,1
                Rectangle:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: 0.1,0.6,0.1,1
                Rectangle:
                    pos: (root.player_x, self.center_y - 40)
                    size: (50, 30)
                Color:
                    rgba: 0.6,0.1,0.1,1
                Rectangle:
                    pos: (root.other_x, self.center_y + 10)
                    size: (50, 30)
        Button:
            text: "تحرك"
            size_hint_y: None
            height: 60
            on_press: root.accelerate()
        Button:
            text: "رجوع"
            size_hint_y: None
            height: 40
            on_press: app.root.current = "menu"
"""

class OfflineRaceScreen(Screen):
    player_pos = NumericProperty(0)
    player_x = NumericProperty(20)

    def accelerate(self):
        self.player_pos += 5
        if self.player_pos > 100: self.player_pos = 100
        track_width = max(200, self.width - 80)
        self.player_x = 20 + (self.player_pos/100) * track_width

class LobbyScreen(Screen):
    def create_room(self):
        # هنا يستخدم Firebase بس لما يضغط الزر
        # مثال: إنشاء روم بكود 6 أرقام
        code = str(random.randint(100000, 999999))
        url = f"{FIREBASE_DB_URL}/rooms/{code}.json"
        data = {"positions":{"p1":0}}
        try:
            requests.put(url, json=data, timeout=6)
            self.manager.get_screen("online").start_room(code, "p1")
            self.manager.current = "online"
        except:
            print("⚠ لا يوجد اتصال إنترنت!")

    def join_room(self):
        # نفس الفكرة لكن ينضم لروم موجود
        code = "123456"  # ممكن تخليها يدخل الكود من TextInput
        url = f"{FIREBASE_DB_URL}/rooms/{code}.json"
        try:
            requests.patch(url, json={"positions/p2":0}, timeout=6)
            self.manager.get_screen("online").start_room(code, "p2")
            self.manager.current = "online"
        except:
            print("⚠ لا يوجد اتصال إنترنت!")

class OnlineRaceScreen(Screen):
    room_code = StringProperty("")
    player_id = StringProperty("")
    player_pos = NumericProperty(0)
    other_pos = NumericProperty(0)
    player_x = NumericProperty(20)
    other_x = NumericProperty(20)
    polling = BooleanProperty(False)

    def start_room(self, code, pid):
        self.room_code = code
        self.player_id = pid
        self.start_polling()

    def accelerate(self):
        self.player_pos += 5
        if self.player_pos > 100: self.player_pos = 100
        # حفظ في Firebase
        try:
            url = f"{FIREBASE_DB_URL}/rooms/{self.room_code}/positions/{self.player_id}.json"
            requests.put(url, json=self.player_pos, timeout=3)
        except:
            pass
        self.update_positions()

    def start_polling(self):
        self.polling = True
        def loop():
            while self.polling:
                try:
                    url = f"{FIREBASE_DB_URL}/rooms/{self.room_code}/positions.json"
                    r = requests.get(url, timeout=4)
                    if r.status_code==200:
                        pos = r.json() or {}
                        me = pos.get(self.player_id,0)
                        other_id = "p1" if self.player_id=="p2" else "p2"
                        other = pos.get(other_id,0)
                        Clock.schedule_once(lambda dt: self.apply(me,other))
                except:
                    pass
                time.sleep(0.5)
        threading.Thread(target=loop, daemon=True).start()

    def apply(self, me, other):
        self.player_pos = me
        self.other_pos = other
        self.update_positions()

    def update_positions(self):
        track_width = max(200, self.width-80)
        self.player_x = 20 + (self.player_pos/100)*track_width
        self.other_x = 20 + (self.other_pos/100)*track_width

class MenuScreen(Screen): pass

class RaceApp(App):
    def build(self):
        return Builder.load_string(KV)

if __name__ == "__main__":
    RaceApp().run()
