import win32event
import win32api
import winerror
import win32console
import win32gui
import win32con
from typing import List, Union
from .essentials import remove_ansi_escape
import io
import sys
import time
import traceback

class InstanceLimiter:
    def __init__(self):
        self.mutexname = "dcreg_{c60ca70d-59a9-43c6-bd96-44f755b45095}"
        self.mutex = win32event.CreateMutex(None, False, self.mutexname)
        self.lasterror = win32api.GetLastError()

    def is_running(self):
        return (self.lasterror == winerror.ERROR_ALREADY_EXISTS)

    def close(self):
        win32api.CloseHandle(self.mutex)
    
    def __del__(self):
        self.close()

class ConsoleDetached(io.TextIOBase):
    def __init__(self, split=None, title="Debug Console"):
        super().__init__()
        self.is_ready = False
        self.is_exe = bool(sys.stdout)
        try:
            win32console.FreeConsole()
            win32console.AllocConsole()
            self.stdconsole = win32console.GetStdHandle(win32console.STD_OUTPUT_HANDLE)
            self.stdconsole.SetConsoleMode(7)
            win32gui.EnableMenuItem(win32gui.GetSystemMenu(win32console.GetConsoleWindow(), False), win32con.SC_CLOSE, win32con.MF_BYCOMMAND | win32con.MF_GRAYED)
            win32console.SetConsoleTitle(title)
            self.is_ready = True
        except Exception as e:
            # self.stdconsole.Detach()
            self.last_exception = e
            if not self.is_exe:
                print(traceback.format_exc())
                time.sleep(10)
            else:
                raise e

    def write(self, data: str):
        self.stdconsole.WriteConsole(data)

    def close(self):
        self.stdconsole.Close()

class ConsoleFile(io.TextIOBase):
    def __init__(self, file: io.TextIOWrapper, console: ConsoleDetached) -> None:
        super().__init__()
        self.file_stream = file
        self.console = console

    def write(self, data):
        file_ready = remove_ansi_escape(data)
        self.file_stream.write(file_ready)
        self.console.write(data)

    def close(self):
        self.file_stream.close()
        self.console.close()
        
class SplitIO(io.TextIOBase):
    def __init__(self, *streams: Union[io.TextIOBase, io.RawIOBase, io.BufferedIOBase]) -> None:
        super().__init__()
        self.streams = streams

    def write(self, data):
        for each in self.streams:
            each.write(data)

    def close(self):
        for each in self.streams:
            each.close()

def create_console():
    console = ConsoleDetached()
    return console