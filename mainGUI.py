from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton
from PyQt5.QtWidgets import QComboBox, QGroupBox, QMenu, QGraphicsDropShadowEffect
from PyQt5.QtWidgets import QGridLayout, QScrollArea, QLabel, QToolButton
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QMessageBox, QStyle, QAction
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint, QSize
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPalette, QColor
import constants as cnts
import threading
from typing import Iterable
import sys, os
import time
from controller import GameliftList, HostHub, pinger, dns_over_https
from version_handler import __version__
import webbrowser

class GUI(QWidget):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        #Initialize layouts
        self.layout = QVBoxLayout(self)
        layout = QVBoxLayout()
        gridLayout = QGridLayout()
        #Initialize necessary tools
        self.gamelift = GameliftList()
        self.host = HostHub()
        #Initialize widgets
        self.ping_text = "Waiting..."
        logolayout = self.load_title()
        combolayout = self.load_combo()
        serverlayout = self.load_current_server()
        pinglayout = self.load_ping()
        gridLayout.addWidget(logolayout, 0,0,1,1)
        gridLayout.addWidget(combolayout, 1,0,1,1)
        gridLayout.addWidget(serverlayout, 2,0,1,1)
        gridLayout.addWidget(pinglayout, 3,0,1,1)
        #
        layout.addLayout(gridLayout)
        self.layout.addLayout(layout)
        self.setLayout(self.layout)
    
    def __threaded_option(self,func: object = None,args: Iterable = ()):
        thread = threading.Thread(target=func,args=args)
        thread.daemon = True
        thread.start()
    
    def _set_icon(self, object, path):
        object.setIcon(QIcon(path))
    
    def _check_updates(self):
        webbrowser.open(cnts.UPDATE_ENDPOINT, new=2)
    
    def load_title(self):
        group = QWidget()
        layout = QHBoxLayout()
        #
        ellipsis = QToolButton(self)
        ellipsis.setPopupMode(QToolButton.InstantPopup)
        ellipsis.setText("...")
        #
        menu = QMenu(self)
        action_update = QAction("Check for updates",self)
        action_update.triggered.connect(lambda: self.__threaded_option(func=self._check_updates))
        menu.addAction(action_update)
        ellipsis.setMenu(menu)
        ellipsis.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        #
        github_button = QPushButton()
        github_button.setStyleSheet("QPushButton:hover { background-color:none; }")
        github_button.setIcon(QIcon(resource_path(os.path.join('res','github-mark-white.png'))))
        github_button.setIconSize(QtCore.QSize(16,16))
        github_button.setMaximumWidth(16)
        github_button.enterEvent = (lambda event: self._set_icon(github_button,resource_path(os.path.join('res','github-mark.png'))))
        github_button.leaveEvent = (lambda event: self._set_icon(github_button,resource_path(os.path.join('res','github-mark-white.png'))))
        github_button.setToolTip('GitHub')
        github_button.setFlat(True)
        github_button.clicked.connect(lambda: webbrowser.open(cnts.GITHUB_ENDPOINT, new=2))
        #
        label = QLabel()
        label.setText(f'<font size="7"><b>DBD Region Changer</b></font> &nbsp;&nbsp;<font size="6" color="#2E313F">V{__version__}</font>')
        layout.addWidget(label)
        layout.addWidget(github_button)
        layout.addWidget(ellipsis)
        #
        group.setLayout(layout)
        return group

    def load_combo(self):
        group = QGroupBox("Select Server:")
        layout = QGridLayout()
        self.sendComboBox = QComboBox(self)
        self.comboButton = QPushButton("Set Server")
        self.clearButton = QPushButton("Set Default")
        self.clearButton.clicked.connect(lambda: self.__threaded_option(func=self.clear_server))
        self.comboButton.clicked.connect(lambda: self.__threaded_option(func=self.set_server))
        if not self.gamelift.load():
            self._call_error_window(title='No Internet', message="Cannot load server lists, please ensure a stable connection to proceed!")
            self.close()
        datas = self.gamelift.sort_data()
        for data in datas:
            self.sendComboBox.addItem(f"{data['server_pretty']} ({data['server_name']})")
            self.sendComboBox.setItemData(self.sendComboBox.count() - 1, data['server_endpoint'])
        self.server_selected = datas[0]['server_endpoint']
        self.sendComboBox.currentIndexChanged.connect(self.set_server_change)
        layout.addWidget(self.sendComboBox, 0, 0, 1, 2)
        layout.addWidget(self.comboButton, 1,0)
        layout.addWidget(self.clearButton, 1,1)
        group.setLayout(layout)
        return group
    
    def load_current_server(self):
        group = QGroupBox()
        layout = QGridLayout()
        self.qlinear = QLabel()
        self.update_current_server()
        layout.addWidget(self.qlinear)
        group.setLayout(layout)
        return group
    
    def update_current_server(self):
        data = self.gamelift.current_host(self.host)
        self.qlinear.setText(f"You are on: {data['server_pretty']} ({data['server_name']})")
    
    def load_ping(self):
        group = QGroupBox("Ping:")
        layout = QGridLayout()
        self.qline = QLabel()
        self.qline.setStyleSheet("background-color: black;")
        self.qline.setAlignment(QtCore.Qt.AlignTop)
        self.qline.setAutoFillBackground(True)
        self.scrollRecords = QScrollArea()
        self.scrollRecords.verticalScrollBar().rangeChanged.connect(
        self.scrollEvent,
        )
        self.scrollRecords.setWidget(self.qline)
        self.scrollRecords.setWidgetResizable(True)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_text)
        self.timer.start(1000)
        self.__threaded_option(func=self.ping_event_loop)
        layout.addWidget(self.scrollRecords,2,0,1,3)
        group.setLayout(layout)
        return group
    
    def scrollEvent (self, minVal=None, maxVal=None):
        # Additional params 'minVal' and 'maxVal' are declared because
        # rangeChanged signal sends them, but we set it to optional
        # because we may need to call it separately (if you need).
        self.scrollRecords.verticalScrollBar().setValue(
        self.scrollRecords.verticalScrollBar().minimum()
    )

    def _get_ping_block(self, datas):
        result = []
        for data in datas:
            template_result = {
                "server_name": None,
                "ping": None,
                "loss": None
            }
            try:
                IP = dns_over_https(data['server_endpoint'])
                Resolved_IP = IP['Answer'][0]['data']
                ping_data = pinger(Resolved_IP)
                template_result['server_name'] = data['server_name']
                template_result['ping'] = ping_data.rtt_avg_ms
                template_result["loss"] = ping_data.packet_loss
                result.append(template_result)
            except Exception as e:
                print(f"Detected error during ping of : {data['server_name']}", e)
                template_result['server_name'] = data['server_name']
                template_result['ping'] = -1
                template_result["loss"] = 1
                result.append(template_result)
        return result

    def ping_event_loop(self):
        colors = ["green", "orange", "red", "grey"] # Grey is for error checking
        datas = self.gamelift.sort_data()
        def color_coding(ping):
            # Ping color based on https://support.deadbydaylight.com/hc/en-us/articles/8947765757204-6-2-0-Resident-Evil-PROJECT-W
            try:
                ping = int(ping)
            except TypeError:
                ping = -1 #indicates error
            if ping <= 100 and ping != -1:
                return 0
            elif ping > 100 and ping <= 200:
                return 1
            elif ping > 200:
                return 2
            else:
                return 3
        while True:
            data_ping = self._get_ping_block(datas)
            data_length = len(data_ping)
            self._reset_text()
            for num, data in enumerate(data_ping):
                ping = data['ping']
                loss = data['loss']
                color = colors[color_coding(ping)]
                self._set_text(f"{data['server_name']} -- ping: {ping}ms -- loss {loss*100}%", color=color, last=(num==data_length-1))
            time.sleep(1)

    def _reset_text(self):
        self.ping_text = ""

    def _set_text(self, text, color= "#000000", last=False):
        oldText = self.ping_text
        if last:
            newText = f'<font color="{color}">{text}</font>'
        else:
            newText = f'<font color="{color}">{text}</font><br>'
        self.ping_text = oldText + newText
    
    def _update_text(self):
        self.qline.setText(self.ping_text)
    
    def set_server_change(self, index):
        print(index)
        data = self.sendComboBox.itemData(index)
        self.server_selected = data

    def _button_enable(self, enabled):
        self.comboButton.setEnabled(enabled)
        self.clearButton.setEnabled(enabled)
    
    def _call_error_window(self, title, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(f'<b>{title}</b>')
        msg.setInformativeText(message)
        msg.setWindowTitle("Error")
        msg.exec_()

    def set_server(self):
        print(self.server_selected)
        self._button_enable(False)
        try:
            self.gamelift.modify_host(server_host=self.server_selected, host=self.host)
        except PermissionError as e:
            self._call_error_window(title='Permission Error!', message="You must ensure admin access and or add this app to the antivirus exception list")
        self.update_current_server()
        time.sleep(1)
        self._button_enable(True)
    
    def clear_server(self):
        self._button_enable(False)
        try:
            self.gamelift.remove_old_host(self.host)
        except PermissionError as e:
            self._call_error_window(title='Permission Error!', message="You must ensure admin access and or add this app to the antivirus exception list")
        self.update_current_server()
        time.sleep(1)
        self._button_enable(True)

class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        self.width_usr = 640
        self.height_usr = 470
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
        self.setMaximumSize(self.width_usr,self.height_usr)
        self.setWindowTitle("DBD Region Changer")
        self.setWindowIcon(QIcon(resource_path(os.path.join("res", "image2.jpg"))))
        self.table_widget = GUI(self)
        #
        self.titleBar = MyBar(self)
        self.setContentsMargins(0, self.titleBar.height(), 0, 0)
        self.resize(self.width_usr, self.titleBar.height() + self.height_usr)
        self.setCentralWidget(self.table_widget)
        self.show()
    
    def changeEvent(self, event):
        if event.type() == event.WindowStateChange:
            self.titleBar.windowStateChanged(self.windowState())

    def resizeEvent(self, event):
        self.titleBar.resize(self.width(), self.titleBar.height())

    def closeEvent(self, event):
        close = QMessageBox()
        close.setWindowTitle("Close")
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        close = close.exec()
        if close == QMessageBox.Yes:
            self.table_widget.close()
            event.accept()
        else:
            event.ignore()

class MyBar(QWidget):
    clickPos = None
    #https://stackoverflow.com/questions/44241612/custom-titlebar-with-frame-in-pyqt5
    def __init__(self, parent):
        super(MyBar, self).__init__(parent)
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QPalette.Shadow)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addStretch()
        background = QWidget(self)
        background.setLayout(layout)
        background.setFixedWidth(parent.width())
        background.setStyleSheet("background-color: #080808; border-radius: 0;")
        self.title = QLabel(self, alignment=Qt.AlignCenter)
        self.title.setText(f'<font color="white">{parent.windowTitle()}</font>')

        style = self.style()
        ref_size = self.fontMetrics().height()
        ref_size += style.pixelMetric(style.PM_ButtonMargin) * 2
        self.setMaximumHeight(ref_size + 2)

        btn_size = QSize(ref_size, ref_size)
        # for target in ('min', 'normal', 'max', 'close'):
        for target in ('min', 'close'):
            btn = QToolButton(self, focusPolicy=Qt.NoFocus)
            layout.addWidget(btn)
            btn.setFixedSize(btn_size)

            iconType = getattr(style, 
                'SP_TitleBar{}Button'.format(target.capitalize()))
            btn.setIcon(style.standardIcon(iconType))

            if target == 'close':
                colorNormal = 'red'
                colorHover = 'orangered'
            else:
                colorNormal = 'palette(mid)'
                colorHover = 'palette(light)'
            btn.setStyleSheet('''
                QToolButton {{
                    background-color: {};
                }}
                QToolButton:hover {{
                    background-color: {}
                }}
            '''.format(colorNormal, colorHover))

            signal = getattr(self, target + 'Clicked')
            btn.clicked.connect(signal)

            setattr(self, target + 'Button', btn)

        # self.normalButton.hide()

        self.updateTitle(parent.windowTitle())
        parent.windowTitleChanged.connect(self.updateTitle)

    def updateTitle(self, title=None):
        if title is None:
            title = self.window().windowTitle()
        width = self.title.width()
        width -= self.style().pixelMetric(QStyle.PM_LayoutHorizontalSpacing) * 2
        self.title.setText(self.fontMetrics().elidedText(
            title, Qt.ElideRight, width))

    def windowStateChanged(self, state):
        print("WindowStateChanged ", state)
    #     self.normalButton.setVisible(state == Qt.WindowMaximized)
    #     self.maxButton.setVisible(state != Qt.WindowMaximized)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clickPos = event.windowPos().toPoint()

    def mouseMoveEvent(self, event):
        if self.clickPos is not None:
            self.window().move(event.globalPos() - self.clickPos)

    def mouseReleaseEvent(self, QMouseEvent):
        self.clickPos = None

    def closeClicked(self):
        self.window().close()

    def maxClicked(self):
        self.window().showMaximized()

    def normalClicked(self):
        self.window().showNormal()

    def minClicked(self):
        self.window().showMinimized()

    def resizeEvent(self, event):
        self.title.resize(self.minButton.x(), self.height())
        self.updateTitle()

if __name__ == "__main__":
    import qdarktheme
    def resource_path(relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    qdarktheme.enable_hi_dpi()
    app = QApplication(sys.argv)
    app.setStyleSheet('QMainWindow')
    qdarktheme.setup_theme(
        theme="auto",
        custom_colors={
            "[dark]": {
                "primary": "#D0BCFF"
            }
        }
        )
    GUI = Window()
    sys.exit(app.exec_())