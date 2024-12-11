
from PyQt5.QtWidgets import (QVBoxLayout, QWidget,QGraphicsView, 
                            QGraphicsScene,QGraphicsPixmapItem,QWidget, QLabel, QDialog,
                            QVBoxLayout, QLineEdit, QPushButton)
from PyQt5.QtGui import QPixmap,  QFont
from PyQt5.QtCore import  Qt
    
class ControlDiagramWidget(QWidget):
    def __init__(self,image_path,level,robot_state,setpoints):
        super().__init__()
        self.robot_state=robot_state
        self.image_path=image_path
        self.level = level
        self.blocks= []
        self.figs =[]
        self.setpoints=setpoints
        self.initUI()
        
    def initUI(self):
        # Crear la escena
        self.scene = QGraphicsScene(self)
        
        # Crear la vista y configurarla para usar la escena
        self.view = QGraphicsView(self.scene, self)
        
        # Deshabilitar las barras de desplazamiento
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Layout para incluir QGraphicsView
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)
        
      
        self.background = QPixmap(self.image_path)
        self.scale=0.8
        new_width = int(self.background.width() )
        new_height = int(self.background.height() )
        self.background = self.background.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Agregar la imagen como un item en la escena
        self.background_item = QGraphicsPixmapItem(self.background)
        self.background_item.setZValue(0)
        self.scene.addItem(self.background_item)
        
        # Configurar la escena del mismo tamaño que la imagen de fondo
        self.scene.setSceneRect(0,0, self.background.width(), self.background.height())
        
        # Ajustar el tamaño de la vista (QGraphicsView) al tamaño de la escena
        self.view.setFixedSize(self.background.width(), self.background.height()*2)
        self.view.setSceneRect(self.scene.sceneRect())  # Ajustar la vista a la escena
        
        # Overlay de información
        self.info_overlay = InfoOverlay(self.level, self.robot_state, parent=self)
        self.info_overlay.setGeometry(10, 10, 200, 100)

    def update_blocks(self,blocks):
        self.blocks=blocks
        for block in self.blocks:
            print(f'{block.name}')
            self.scene.addItem(block)

    

    def update_robot_state(self,state):
        self.robot_state=state
        self.info_overlay.update_info(self.robot_state)
        
    
    def update_block_parameter(self, block_name, param_name, new_value):
        block = next((b for b in self.blocks if b.name == block_name), None)
        if block:
            if param_name in block.parameters:
                block.parameters[param_name] = new_value
                #print(f"Updated block {block_name} parameter '{param_name}' to {new_value}")
            else:
                print(f"Parameter '{param_name}' not found in block {block_name}")
        else:
            print(f"Block named {block_name} not found")

    def get_blocks_parameters(self):
        parameters=[]
        for block in self.blocks:
            parameters.extend(block.get_param_values())
        
        return parameters
    

    def set_setpoint(self,param,value):
        print(f'{param}, {value}')
        self.setpoints[param]=value

    def get_setpoints(self):
        return self.setpoints
    
    def mousePressEvent(self, event):

        click_position_scene = self.view.mapToScene(event.pos())
        print(f'Click position {click_position_scene.x()}, {click_position_scene.y()}')

        
        for block in self.blocks:
            if block.contains(click_position_scene):
                print(f"Clic detectado en el bloque: {block.get_name()}")
                dialog = ParameterInputDialog(block.parameters)
                if dialog.exec_():
                    parameter_values = [input_field.text() for input_field in dialog.parameter_inputs]
                    new_parameters = dict(zip(block.parameters.keys(), parameter_values))
                    block.update_parameters(new_parameters)


class InfoOverlay(QWidget):
    def __init__(self, abstraction_level=1, robot_state='No definido', parent=None):
        super().__init__(parent)
        self.abstractionlevel = abstraction_level
        self.robot_state = robot_state
        self.initUI()

    def initUI(self):
        # Crear layout y etiquetas
        layout = QVBoxLayout()
        self.status_label = QLabel(f'Estado actual: {self.robot_state}', self)
        self.level_label = QLabel(f'Modo: {self.abstractionlevel}', self)
        self.status_label.setFont(QFont('Arial', 14, QFont.Bold))  # Cambiar el tamaño y formato de la letra
        self.status_label.setStyleSheet('color: green;')  # Cambiar el color de la letra

        self.level_label.setFont(QFont('Arial', 10, QFont.Bold))  # Cambiar el tamaño y formato de la letra
        self.level_label.setStyleSheet('color: red;')  # Cambiar el color de la letra
        # Configurar el diseño
        layout.addWidget(self.status_label)
        layout.addWidget(self.level_label)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setLayout(layout)

    def update_info(self, robot_state):
        self.robot_state = robot_state
        self.status_label.setText(f'{robot_state}')
        self.level_label.setText(f'{self.abstractionlevel}')


class ParameterInputDialog(QDialog):
    def __init__(self, parameters):
        super().__init__()
        self.setWindowTitle('Parametros')
        self.layout = QVBoxLayout()

        self.parameter_inputs = []
        for param_name, param_value in parameters.items():
            label = QLabel(f'{param_name}:', self)
            self.layout.addWidget(label)
            input_field = QLineEdit(self)
            input_field.setText(str(param_value))
            self.layout.addWidget(input_field)
            self.parameter_inputs.append(input_field)

        self.ok_button = QPushButton('OK', self)
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.ok_button)

        self.setLayout(self.layout)