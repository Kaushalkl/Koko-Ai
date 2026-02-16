import os, subprocess, pyautogui, ctypes

def shutdown():
    os.system("shutdown /s /t 10")

def restart():
    os.system("shutdown /r /t 5")

def lock():
    ctypes.windll.user32.LockWorkStation()

def open_app(name):
    apps = {
        "notepad": "notepad",
        "calculator": "calc",
        "chrome": "start chrome"
    }
    if name in apps:
        subprocess.Popen(apps[name], shell=True)

def volume_up():
    pyautogui.press("volumeup")

def volume_down():
    pyautogui.press("volumedown")
