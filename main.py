import sys
import imaplib
import smtplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (QDialog, QLineEdit, QFormLayout, QDialogButtonBox, QMessageBox, QListWidget, QTextEdit, 
                             QVBoxLayout, QPushButton, QWidget, QSplitter, QMainWindow)

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.email = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        layout = QFormLayout()
        layout.addRow("Email:", self.email)
        layout.addRow("Password:", self.password)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_credentials(self):
        return self.email.text(), self.password.text()


class EmailClientWindow(QMainWindow):
    def __init__(self, imap_connection, smtp_connection, email):
        super().__init__()
        self.imap_connection = imap_connection
        self.smtp_connection = smtp_connection
        self.email = email

        self.setWindowTitle("Email Client")
        self.setGeometry(100, 100, 800, 600)

        # Списки писем и область просмотра
        self.inbox_list = QListWidget()
        self.message_view = QTextEdit()
        self.message_view.setReadOnly(True)

        # Разделитель для списков и просмотра
        splitter = QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self.inbox_list)
        splitter.addWidget(self.message_view)

        # Кнопка для отправки нового письма
        self.compose_button = QPushButton("Compose New Email")
        self.compose_button.clicked.connect(self.compose_email)

        # Основной макет
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        layout.addWidget(self.compose_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Обработка события выбора письма
        self.inbox_list.itemClicked.connect(self.display_email)

        # Загружаем список писем
        self.load_inbox()

    def load_inbox(self):
        self.inbox_list.clear()  # Очищаем список перед загрузкой новых сообщений
        self.imap_connection.select("inbox")
        result, data = self.imap_connection.search(None, "ALL")

        if result == "OK":
            for num in data[0].split():
                result, msg_data = self.imap_connection.fetch(num, "(RFC822)")
                if result == "OK":
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Попробуем получить заголовок "Subject"
                    subject = msg.get("Subject")
                    if subject:
                        decoded_subject = email.header.decode_header(subject)[0][0]
                        if isinstance(decoded_subject, bytes):
                            decoded_subject = decoded_subject.decode()
                    else:
                        decoded_subject = "No Subject"

                    # Добавляем заголовок в список
                    self.inbox_list.addItem(decoded_subject)

    def display_email(self, item):
        email_index = self.inbox_list.row(item) + 1
        result, msg_data = self.imap_connection.fetch(str(email_index), "(RFC822)")
        if result == "OK":
            msg = email.message_from_bytes(msg_data[0][1])
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    self.message_view.setPlainText(part.get_payload(decode=True).decode())

    def compose_email(self):
        self.compose_window = ComposeEmailWindow(self.smtp_connection, self.email)
        self.compose_window.show()

    def closeEvent(self, event):
        if self.imap_connection:
            self.imap_connection.logout()
        if self.smtp_connection:
            self.smtp_connection.quit()
        event.accept()


class ComposeEmailWindow(QMainWindow):
    def __init__(self, smtp_connection, sender_email):
        super().__init__()
        self.smtp_connection = smtp_connection
        self.sender_email = sender_email

        self.setWindowTitle("Compose Email")
        self.setGeometry(200, 200, 600, 400)

        # Ввод получателя
        self.recipient_label = QtWidgets.QLabel("Recipient:")
        self.recipient_input = QLineEdit()

        # Ввод темы
        self.subject_label = QtWidgets.QLabel("Subject:")
        self.subject_input = QLineEdit()

        # Ввод текста письма
        self.message_label = QtWidgets.QLabel("Message:")
        self.message_input = QTextEdit()

        # Кнопка отправки
        self.send_button = QPushButton("Send Email")
        self.send_button.clicked.connect(self.send_email)

        # Макет
        layout = QVBoxLayout()
        layout.addWidget(self.recipient_label)
        layout.addWidget(self.recipient_input)
        layout.addWidget(self.subject_label)
        layout.addWidget(self.subject_input)
        layout.addWidget(self.message_label)
        layout.addWidget(self.message_input)
        layout.addWidget(self.send_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def send_email(self):
        recipient_email = self.recipient_input.text()
        subject = self.subject_input.text()
        message = self.message_input.toPlainText()

        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))

            self.smtp_connection.sendmail(self.sender_email, recipient_email, msg.as_string())
            QMessageBox.information(self, "Success", "Email sent successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Failed", f"Failed to send email: {e}")

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # Создаём окно авторизации
    login_dialog = LoginDialog()
    if login_dialog.exec() == QDialog.Accepted:
        email_address, password = login_dialog.get_credentials()

        try:
            print("Attempting to connect to IMAP and SMTP servers...")
            # Создание IMAP соединения
            imap_conn = imaplib.IMAP4_SSL("imap.yandex.ru", 993)
            imap_conn.login(email_address, password)
            
            # Создание SMTP соединения
            smtp_conn = smtplib.SMTP_SSL("smtp.yandex.ru", 465)
            smtp_conn.login(email_address, password)
            
            # Запуск основного окна приложения
            main_window = EmailClientWindow(imap_conn, smtp_conn, email_address)
            main_window.show()
            
            sys.exit(app.exec_())
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to connect: {e}")
            print(f"Error details: {e}")
            sys.exit(1)
    else:
        print("Login dialog was canceled.")
        sys.exit(0)

if __name__ == "__main__":
    main()
