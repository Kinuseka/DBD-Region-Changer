from PyQt5.QtWidgets import QMessageBox
class ErrorBox(QMessageBox):
    def __init__(self, header, message, title="Error"):
        super().__init__()
        self.title = title
        self.header = header
        self.message = message
        self.setIcon(QMessageBox.Critical)
        self.setText(f'<b>{header}</b>')
        self.setInformativeText(message)
        self.setWindowTitle(title)