from models.window import ErrorBox
from tools.processes import InstanceLimiter, create_console, ConsoleFile, SplitIO
from tools.essentials import wait_awaitable
from version_handler import __version__
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton
from PyQt5.QtWidgets import QComboBox, QGroupBox, QMenu, QGraphicsDropShadowEffect
from PyQt5.QtWidgets import QGridLayout, QScrollArea, QLabel, QToolButton, QFileDialog
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QMessageBox, QStyle, QAction
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint, QSize
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPalette, QColor
import constants as cnts
import threading
from typing import Iterable
import sys, os, shutil
import time
from loguru import logger
from controller import (
    GameliftList, 
    HostHub, 
    dns_over_https, 
    handle_ping, 
    create_thread_pools
)
import webbrowser
import tempfile
import datetime
import argparse
IS_DEBUG = False
class GUI(QWidget):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        #Init static var
        self.colors = ["green", "orange", "red", "grey"]
        self._recent_ping = []
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
        log.info('Loaded title')
        combolayout = self.load_combo()
        log.info("Loaded gamelift layout")
        self.servergroup, self.serverlayout = self.load_current_server()
        pinglayout = self.load_ping()
        log.info('Loaded ping layout')
        self.__threaded_option(self.selected_ping)
        gridLayout.addWidget(logolayout, 0,0,1,1)
        gridLayout.addWidget(combolayout, 1,0,1,1)
        gridLayout.addWidget(self.servergroup, 2,0,1,1)
        gridLayout.addWidget(pinglayout, 3,0,1,1)
        #
        layout.addLayout(gridLayout)
        self.layout.addLayout(layout)
        self.setLayout(self.layout)
        log.info('GUI Initialized')
        self.DEBUG_MODE = IS_DEBUG
    
    def __threaded_option(self,func: object = None,args: Iterable = ()):
        thread = threading.Thread(target=func,args=args)
        thread.daemon = True
        thread.start()
    
    def _set_icon(self, object, path):
        object.setIcon(QIcon(path))
    
    def _open_browser(self, url):
        opened = webbrowser.open(url=url, new=2)
        if opened:
            log.info(f'Opened url: {url}')
        else:
            log.info(f'Failed to open url: {url}')
    
    def _dump_logs(self):
        dest_dir = QFileDialog.getExistingDirectory(self, "Select directory to dump logs to")
        if not dest_dir: 
            log.info('Cancelled log dump')
            return
        log.info(f'Logs dumped to: {dest_dir}') #Put this first so this log info will be logged upon dump
        src_dir = os.path.join(TEMP_DIR.name, LOG_FILENAME)
        try:
            shutil.copy(src_dir, dest_dir)
        except shutil.SameFileError:
            log.warning('Attemping to dump logs on the same directory as the source, aborting task')
            QMessageBox.warning(self,
                'Warning',
                'You cannot use the same directory as the source, task aborted')
    
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
        action_update.triggered.connect(lambda: self.__threaded_option(func=self._open_browser, args=(cnts.UPDATE_ENDPOINT,)))
        action_logs_dump = QAction("Dump logs",self)
        action_logs_dump.triggered.connect(self._dump_logs)
        menu.addAction(action_update)
        menu.addAction(action_logs_dump)
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
        github_button.clicked.connect(lambda: self.__threaded_option(func=self._open_browser, args=(cnts.GITHUB_ENDPOINT,)))
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
            sys.exit(1)
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
        self.plinear = QLabel()
        self.update_current_server()
        layout.addWidget(self.qlinear, 0, 0)
        layout.addWidget(self.plinear, 0, 1, alignment=Qt.AlignRight)
        group.setLayout(layout)
        return group, layout
    
    def current_server_ping(self):
        self.serverlayout

    def update_current_server(self):
        data = self.gamelift.current_host(self.host)
        if data['server_pretty'] == "No host":
            nearest = self._get_fastest_ping()
            server_pretty = "Automatic"
            server_name = nearest['server_name'] if nearest else "None"
        else:
            server_pretty = data['server_pretty']
            server_name = data['server_name']
        self.qlinear.setText(f"You are on: {server_pretty} ({server_name})")
    
    def load_ping(self):
        group = QGroupBox("Ping:")
        layout = QGridLayout()
        self.qline = QLabel()
        self.qline.setStyleSheet("background-color: black;")
        self.qline.setAlignment(QtCore.Qt.AlignTop)
        self.qline.setAutoFillBackground(True)
        self.scrollRecords = QScrollArea()
        self.scrollRecords.verticalScrollBar().rangeChanged.connect(self.scrollEvent)
        self.scrollRecords.setWidget(self.qline)
        self.scrollRecords.setWidgetResizable(True)
        self.timer_pingblock = QtCore.QTimer(self)
        self.timer_pingblock.timeout.connect(self._update_text_ping)
        self.timer_pingblock.start(1000)
        self.selected_ping_text = 'Ping:'
        self.timer_pingselected = QtCore.QTimer(self)
        self.timer_pingselected.timeout.connect(self._update_text_selected_ping)
        self.timer_pingselected.start(1000)
        # self.timer_pingselected = QtCore.QTimer(self)
        # self.timer_pingselected.timeout.connect()
        # self.timer_pingselected.start(1000)
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

    def selected_ping(self):
        while True:
            try:
                self._update_text_sel_ping()
            except Exception as e:
                log.exception('Unhandled unexpected error occured on selected_ping method')    
            time.sleep(1)

    def _get_ping_block(self, datas):
        result = []
        IPs = []
        futures = create_thread_pools([data['server_endpoint'] for data in datas], dns_over_https)
        for num, future in enumerate(futures):
            try:
                Resolved_IP = future.result()
                if Resolved_IP:
                    IPs.append(Resolved_IP)
                else:
                    log.error('Received no ip from DoH')
                    IPs.append(False)
            except Exception as e:
                log.exception(f"Detected error while trying to resolve: {datas[num]['server_endpoint']}")
                IPs.append(False)
        ping_responses = handle_ping(IPs)
        for (ping_data, data) in zip(ping_responses, datas):
            template_result = {
                "server_name": None,
                "ping": None,
                "loss": None
            }
            if ping_data:
                template_result['server_name'] = data['server_name']
                template_result['ping'] = ping_data.rtt_avg_ms
                template_result["loss"] = round(ping_data.packet_loss, 2)
                result.append(template_result)
            else:
                log.error(f"No data received for: {data['server_name']}")
                template_result['server_name'] = data['server_name']
                template_result['ping'] = -1
                template_result["loss"] = 1
                result.append(template_result)
        return result

    def ping_event_loop(self):
         # Grey is for error checking
        datas = self.gamelift.sort_data()
        while True:
            self._recent_ping = self._get_ping_block(datas)
            data_length = len(self._recent_ping)
            self._reset_text()
            for num, data in enumerate(self._recent_ping):
                ping = data['ping']
                loss = data['loss']
                color = self.colors[self._determine_ping_color(ping)]
                self._set_text(f"{data['server_name']} -- ping: {ping}ms -- loss {loss*100}%", color=color, last=(num==data_length-1))
            time.sleep(1)

    def _determine_ping_color(self, ping):
        # Ping color based on https://support.deadbydaylight.com/hc/en-us/articles/8947765757204-6-2-0-Resident-Evil-PROJECT-W
        # Wayback: https://web.archive.org/web/20230303091151/https://support.deadbydaylight.com/hc/en-us/articles/8947765757204-6-2-0-Resident-Evil-PROJECT-W
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

    def _reset_text(self):
        self.ping_text = ""

    def _set_text(self, text, color= "#000000", last=False):
        oldText = self.ping_text
        if last:
            newText = f'<font color="{color}">{text}</font>'
        else:
            newText = f'<font color="{color}">{text}</font><br>'
        self.ping_text = oldText + newText
    
    def _update_text_ping(self):
        self.qline.setText(self.ping_text)
    
    def _update_text_selected_ping(self):
        self.plinear.setText(self.selected_ping_text)
    
    def _get_fastest_ping(self):
        for i in range(10): #Timeout 10s
            if not self._recent_ping:
                time.sleep(1)
                continue
            fastest = min(self._recent_ping, key=lambda value: value['ping'])
            return fastest
        return
        
    def _update_text_sel_ping(self):
        selected = self.gamelift.current_host(self.host)
        self.update_current_server()
        if selected['server_pretty'] == "No host":
            selected = self._get_fastest_ping()
            log.debug(f'Calculated that: {selected} is the nearest server')
            if selected:
                selected = self.gamelift.get_data_fromservername(selected['server_name'])
        if not selected:
            self.selected_ping_text = f'Ping: <font color="{self.colors[3]}">-1ms</font>'
            return
        ping_res = self._get_ping_block([selected])
        if len(ping_res) == 0:
            return #Shutdown
        ping_res = ping_res[0]
        color = self.colors[self._determine_ping_color(ping_res["ping"])]
        self.selected_ping_text =  f'Ping: <font color="{color}">{ping_res["ping"]}ms</font>'
    
    def set_server_change(self, index):
        log.info(f"Index: {index}")
        data = self.sendComboBox.itemData(index)
        self.server_selected = data

    def _button_enable(self, enabled):
        self.comboButton.setEnabled(enabled)
        self.clearButton.setEnabled(enabled)
    
    def _call_error_window(self, title, message):
        box = ErrorBox(title, message, parent=self, ontop=False)
        box.exec_()

    def set_server(self):
        self._button_enable(False)
        try:
            self.gamelift.modify_host(server_host=self.server_selected, host=self.host)
            log.info(f"Selected: {self.server_selected}")
        except PermissionError as e:
            log.error("Cannot set server due to permission error")
            self._call_error_window(title='Permission Error!', message="You must ensure admin access and or add this app to the antivirus exception list")
        self.update_current_server()
        time.sleep(1)
        self._button_enable(True)
    
    def clear_server(self):
        self._button_enable(False)
        try:
            self.gamelift.remove_old_host(self.host)
            log.info("Cleared selected")
        except PermissionError as e:
            log.error("Cannot clear server due to permission error")
            self._call_error_window(title='Permission Error!', message="You must ensure admin access and or add this app to the antivirus exception list")
        self.update_current_server()
        time.sleep(1)
        self._button_enable(True)

class WindowBar(QWidget):
    clickPos = None
    #https://stackoverflow.com/questions/44241612/custom-titlebar-with-frame-in-pyqt5
    def __init__(self, parent):
        super().__init__(parent)
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

    def windowStateChanged(self, state: QtCore.Qt.WindowStates):
        log.info(f"WindowStateChanged {int(state)}")
        # self.normalButton.setVisible(state == Qt.WindowMaximized)
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
        self.titleBar = WindowBar(self)
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

if __name__ == "__main__":
    import qdarktheme
    parse_arguments = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parse_arguments.add_argument("-d", '--debug', action='store_true')
    try:
        cli_args, unknown = parse_arguments.parse_known_args()
    except (argparse.ArgumentError, SystemExit) as e:
        cli_args = argparse.Namespace(debug=False)
        if sys.stdout:
            print(f"argparse attempted to exit before log was initialized:", e)
    #Initializers
    TEMP_DIR = tempfile.TemporaryDirectory(prefix='dcreg_tmp_')
    LOG_FILENAME = f'[{str(datetime.datetime.today().replace(microsecond=0)).replace(":",".")}]LogFile_dcreg.log'
    logger.remove()
    log = logger.bind(name="DBDRegion-Debug")
    if cli_args.debug:
        IS_DEBUG = True
        _console = create_console()
        _console.write('Debug console opened\n')
        log.add(_console, colorize=True, format="[<blue>{name}</blue>][{level}]<green>{time}</green> <level>{message}</level>")
        log.add(open(os.path.join(TEMP_DIR.name, LOG_FILENAME), 'w'), colorize=False, format="[<blue>{name}</blue>][{level}]<green>{time}</green> <level>{message}</level>")
    elif sys.stdout:
        log.add(sys.stdout, colorize=True, format="[<blue>{name}</blue>][{level}]<green>{time}</green> <level>{message}</level>")
        log.add(open(os.path.join(TEMP_DIR.name, LOG_FILENAME), 'w'), colorize=False, format="[<blue>{name}</blue>][{level}]<green>{time}</green> <level>{message}</level>")
    else:
        log.add(open(os.path.join(TEMP_DIR.name, LOG_FILENAME), 'w'), colorize=False, format="[<blue>{name}</blue>][{level}]<green>{time}</green> <level>{message}</level>")
    log.info('Logger ready')
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
        theme="dark",
        custom_colors={
            "[dark]": {
                "primary": "#D0BCFF"
            }
        }
        )
    log.info('Theme patched')
    #Main process start here
    log.info('App has finished initializing')
    log.info(f'App version: {__version__}')
    log.info(f'Resource path is at: {resource_path("")}')
    log.info(f'Temp path is at: {TEMP_DIR.name}')
    instance_app = InstanceLimiter()
    try:
        if instance_app.is_running():
            log.info('Duplicate process detected')
            ErrorBox('Duplicate processes', 'Another process is running').exec_()
            sys.exit(1)
        MainWindow = Window()
        sys.exit(app.exec_())
    finally:
        log.info('Reached end of process, closing handle')
        wait_awaitable(log.complete())
        log.remove()
        # out_log.close()
        TEMP_DIR.cleanup()
        instance_app.close()
