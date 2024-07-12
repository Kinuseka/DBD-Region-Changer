from PyQt5.QtWidgets import QMessageBox
from PyQt5 import QtCore
class ErrorBox(QMessageBox):
    def __init__(self, header, message, title="Error", ontop = True, parent = None):
        super().__init__()
        self.parent = parent
        self.title = title
        self.header = header
        self.message = message
        self.setIcon(QMessageBox.Critical)
        self.setText(f'<b>{header}</b>')
        self.setInformativeText(message)
        self.setWindowTitle(title)
        if ontop:
            self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)