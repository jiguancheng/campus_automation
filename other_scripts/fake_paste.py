import time
import tomllib

import keyboard
import pyperclip

config = tomllib.loads(open("config.toml", encoding="utf-8").read())
key = config["fake_paste"]["fake_hotkey"]


def fake_paste():
    content = pyperclip.paste()
    time.sleep(.1)
    keyboard.write(content)


keyboard.add_hotkey(key, fake_paste)

while True:
    time.sleep(1)
