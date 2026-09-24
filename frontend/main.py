import sys
from PySide6.QtWidgets import QApplication
from frontend.login_window import LoginWindow
from frontend.admin_dashboard import AdminDashboard
from frontend.style import APP_STYLE

app = QApplication(sys.argv)
app.setStyleSheet(APP_STYLE)

dashboard = None

def open_dashboard():
    global dashboard
    dashboard = AdminDashboard()
    dashboard.show()
    login.close()

login = LoginWindow(on_success=open_dashboard)
login.show()

sys.exit(app.exec())