from win32event import CreateMutex
from win32api import CloseHandle, GetLastError
from winerror import ERROR_ALREADY_EXISTS
from typing import List, Union
from .essentials import remove_ansi_escape
import win32console
import io
import sys


class InstanceLimiter:
    def __init__(self):
        self.mutexname = "dcreg_{c60ca70d-59a9-43c6-bd96-44f755b45095}"
        self.mutex = CreateMutex(None, False, self.mutexname)
        self.lasterror = GetLastError()

    def is_running(self):
        return (self.lasterror == ERROR_ALREADY_EXISTS)

    def close(self):
        if not self.is_running and self.mutex:
            CloseHandle(self.mutex)

class ConsoleDetached(io.TextIOBase):
    def __init__(self, split=None):
        super().__init__()
        win32console.FreeConsole()
        win32console.AllocConsole()
        self.stdconsole = win32console.GetStdHandle(win32console.STD_OUTPUT_HANDLE)
        self.stdconsole.SetConsoleMode(7)

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