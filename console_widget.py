
#Blolque Consola

from PyQt5.QtWidgets import (
    QVBoxLayout, QLineEdit,QPushButton,QTextEdit, QHBoxLayout, QWidget
    )  

class ConsoleWidget(QWidget):
        def __init__(self,A_send_serial):
            super().__init__()
            
            self.layout0 = QVBoxLayout()
            self.text_console = QTextEdit()
            self.text_console.setReadOnly(True)  # Hacer el QTextEdit de solo lectura
            text_to_add = "Consola\n"
            self.text_console.append(text_to_add) 
            self.layout0.addWidget(self.text_console)

            # Agregar QLineEdit para entrada de comandos
            layout1 = QHBoxLayout()
            self.command_line = QLineEdit()
            layout1.addWidget(self.command_line)

            # Botón para enviar comandos
            send_button = QPushButton("Enviar")
            send_button.clicked.connect(lambda: A_send_serial(self.command_line.text()))
            layout1.addWidget(send_button)

            self.layout0.addLayout(layout1)
            self.setLayout(self.layout0)
            # Botón para cambiar al modo "Eco"
            #eco_button = QPushButton("Modo Eco")
            #eco_button.clicked.connect(self.toggle_eco_mode)
            #layout.addWidget(eco_button)

        def append(self,data):
            self.text_console.append(data) 

            