import sys
import numpy as np
import serial
import serial.tools.list_ports

from Blocks import Block
from control_diagram_widget_03 import ControlDiagramWidget 
from console_widget import ConsoleWidget
from plot_widget import PlotWidget
from table_widget import TableViewDialog
from caracterizacion_v5 import Motor_model
from Data_container import DataContainer
from StateMachine_v2 import StateMachine
from trajectory_generation import DrawWindow

from queue import Queue
from datetime import datetime

from PyQt5.QtCore import Qt, QThread,QSize,QTimer
from PyQt5.QtGui import QColor ,QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,QLineEdit,QFileDialog,
    QPushButton, QCheckBox, QMenu, QAction, QTabWidget, QToolBar,
    QHBoxLayout, QLabel, QGridLayout,QDialog,QSlider,QMessageBox
)


# lista de sensores
sensors_list = [
    "velr_izq",
    "velr_der",
    "sensor_izq",
    "sensor_frontal_izq",
    "sensor_frontal_der",
    "sensor_der",
    "imu_acc_x",
    "imu_acc_y",
    "imu_w_x",
    "imu_w_y",
    "imu_m_x",
    "imu_m_y"
]

transiciones={
    'Idle': {'config': 'Configurar','caract':'Caract. Motores','test':'Testing','calib':'Calibracion','manual': 'Modo Manual'},
    'Configurar': {'save': 'Set parametros','stop': 'Idle'},
    'Set parametros': {'start': 'Modo operativo', 'stop': 'Idle'},
    'Modo operativo': {'stop': 'Idle'},
    'Caract. Motores': {'stop': 'Idle'},
    'Testing': {'stop': 'Idle'},
    'Calibracion': {'stop': 'Idle'},
    #'Waiting_logs': {'stop': 'Idle'},
    'Modo Manual': {'stop': 'Idle'},
    #'Shutdown': {}  # sin salida
}

state_text_mapping = {
            'Idle': 'Seleccione una accion para el robot. Es necesario "Configurar" antes de comenzar a correr!',
            'Configurar': 'Seleccione un modo de operacion y sus parametros',
            'Set parametros': 'Establezca los setpoints??????',
            'Modo operativo': 'En funcionamiento',
            'Caract. Motores':'Cuando todo este listo, presiona comenzar',
            'Testing':'Cuando todo este listo, presiona comenzar',
            # Add other states and their associated texts here
        }

state_extra_commands ={
    'Configurar': {'Modo 0':'m0','Modo 1':'m1','Modo 2':'m2','Modo 3':'m3','Parametros':'param'},
    'Pre_Run':    {'Setear':'s','Modo 1':'m1','Modo 2':'m2','Modo 3':'m3','Parametros':'param'}
}

mode_frame={1:'LR',
            2:'VW',
            3:'FLV'
}

COMMANDS = {
    'Idle': "*stop*",
    'Pre_Run': "*save*",
    'Config': "*config*",
    'Run_Mod_x':"*start*",
    'Caracterizacion':"*caract*",
    'calibracion':"*m0*",
    'test':'*m1*'
}

data_motores= 'data_motores.csv'
arrows_path= 'images/arrows.png'
csv_file_path = 'datos_sensores.csv'
image_path_mod1pid="images/Mode1_PID.png"
image_path_mod1onoff="images/Mode1_ONOFF.png"
image_path_mod2="images/Mode2.png"
image_path_mod3="images/Mode3.png"
start_time = datetime.now()


class MainWindow(QMainWindow):

    def __init__(self,transiciones_statemachine,starting_state='Idle'):
        
        super(MainWindow, self).__init__()

        self.transiciones=transiciones_statemachine
        self.current_state=starting_state

        self.timer_tramas = QTimer()
        self.timer_tramas.timeout.connect(self.on_timeout)

        self.data_container = DataContainer(len(sensors_list))
        self.state_machine  = StateMachine(self.transiciones)
        
        self.init_values_app()
        self.diagram_setup()
        self.init_config_serial()
        self.init_UI()
        self.init_toolbar()
        
        
        #INTERRUPCIONES 
        self.num_interrupt = 0
        self.eventcounter=0
        self.update_plot_factor=10
        self.timer = self.startTimer(10)  # Interrupción 
        
    def init_UI(self):

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        master_layout = QVBoxLayout()
        central_widget.setLayout(master_layout)
        self.setWindowTitle("S-Vision")
        # Layout 00 

        self.layout_superior=QHBoxLayout()
        self.layout_superior.addWidget(self.currentcontrolDiagram)
        
        button_hide = QPushButton(self)
        button_hide.setIcon(QIcon(arrows_path))  # Reemplaza con la ruta correcta
        button_hide.setIconSize(QSize(8, 400))  # Ajustar el tamaño del icono
        button_hide.setFixedSize(8, 400)
        button_hide.setCheckable(True)  # Hacer el botón seleccionable (toggle)
        button_hide.clicked.connect(lambda : self.toggle_diagram()) 

        self.layout_superior.addWidget(button_hide)


        self.plots=[
        PlotWidget(self.data_container, sensors_list,self.frecop, ["velr_izq"]),
        PlotWidget(self.data_container, sensors_list,self.frecop, ["velr_der"])
        ]
        layout_plots=QVBoxLayout()
        for plot in self.plots:
            layout_plots.addWidget(plot)

        self.layout_superior.addLayout(layout_plots)

        self.layout_inferior=QHBoxLayout()
        #Layout 20
        # Widget QTextEdit para la consola
        layout_20= QVBoxLayout()
        self.console=ConsoleWidget(self.send_serial)
        layout_20.addWidget(self.console)

        #Layout 22
        self.tabs=QTabWidget()
        self.commandTab = QWidget()
        self.commandTab.setLayout(self.CommandTabUI_update())
        self.tabs.addTab(self.commandTab, "Comandos")
        self.tabs.addTab(self.ParamPIDTabUI(self.currentblocks), "Parametros")
        self.tabs.addTab(self.GraphsTabUI(),  "Graficos")

        
        layout_22=QVBoxLayout()
        layout_22.addWidget(self.tabs)

        self.layout_inferior.addLayout(layout_20)
        self.layout_inferior.addLayout(layout_22)
        #self.layout_00.addLayout(layout_02)
        master_layout.addLayout(self.layout_superior)
        master_layout.addLayout(self.layout_inferior)

    def init_values_app(self):

        self.transformed_vectors = []
        self.transformed_vectors_polar =[]
        self.trajectory_vectors= []

        self.current_vector_index=1
        self.ack_vector_sequence =False
        self.selectedserialport=''

        self.caracterizando_motores = False
        self.caract_data=[]
        self.motordataset = None  # para carecterizar
        self.motors = [None, None]

        self.motor_izq_consts={
            'b1': 0.92, 'a1': -0.01, 'a2': -12.18}
        
        self.motor_der_consts={
            'b1': 0.92, 'a1': -0.01, 'a2': -12.18}
        
        self.state_to_layout = {  
            'Configurar':     self.layout_configurar,
            'Set parametros': self.layout_setparam,
            'Caract. Motores':self.layout_caracterizar,
            'Testing':        self.layout_testing,
            'Calibracion':    self.layout_calibracion,
            'Modo Manual':    self.layout_manual,
            'Modo operativo': self.layout_setparam
        }
        self.state_to_function = {
            'Configurar':     self.handle_configurar,
            'Set parametros': self.handle_set_parametros,
            'Modo operativo': self.handle_set_parametros        
        }

        self.debugmode=True
        self.enable_keyboard = False
        self.frecop=100 #Ms
       
    def init_config_serial(self):
        # Inicializar variables para comunicación serial
        self.serial_thread = None
        self.serial_port = None
        self.serial_reading = False
        self.eco_mode= False

    def init_toolbar(self):
        #TOOLBAR
        toolbar = QToolBar("My main toolbar")
        self.addToolBar(toolbar)
        
        #BOTON 1
        # Menú desplegable "Configuración"
        configuracion_menu = QMenu(self)
        guardar_action = QAction("Exp. sensores", self)
        cargar_action = QAction("Cargar", self)
        
        configuracion_menu.addAction(guardar_action)
        configuracion_menu.addAction(cargar_action)
        
        ##Acciones menu config
        guardar_action.triggered.connect(self.save_sensor_data)
        
        # Botón "Configuración" con menú desplegable
        configuracion_button = QAction("Configuración", self)
        configuracion_button.setMenu(configuracion_menu)
        
        #BOTON 2
        # Crear el menú para "Com Serial"
        com_serial_menu = QMenu(self)
        self.ports_menu = QMenu("Puertos", self)       
        connect_disconnect_button = QAction("Conectar/Desconectar", self)

        #boton "Com serial"
        com_serial_button = QAction("Com Serial", self)
        com_serial_button.setMenu(com_serial_menu)
        #boton "Puertos"
        puertos_button = QAction("Com Serial", self)
        puertos_button.setMenu(self.ports_menu)
        self.ports_menu.addAction(self.update_serial_ports())
    
        #agrego el menu "Pueros" a "Serial Com"
        com_serial_menu.addMenu(self.ports_menu)
        com_serial_menu.addAction(connect_disconnect_button)
        
        #Acciones
        #Accion conectar desconectar
        connect_disconnect_button.triggered.connect(self.toggle_serial_reading)
        self.ports_menu.aboutToShow.connect(self.update_serial_ports)

        # Agregar botones a la barra de herramientas
        toolbar.addAction(configuracion_button)
        toolbar.addAction(com_serial_button)
    
#INTERRUPCION 
    def timerEvent(self,event):
        self.eventcounter+=1
        
        if self.serial_reading:
            serial_data=self.serial_thread.get_serial_data()
            while serial_data != 0:
                self.interpret_serial_queue(serial_data)
                serial_data=self.serial_thread.get_serial_data()

        if self.eventcounter>=self.update_plot_factor: #agregar un enable_plot_udate general?
                self.eventcounter=0
                for plot in self.plots:
                    plot.update()

        #if self.ack_vector_sequence == True:
           # self.ack_vector_sequence = False
           # self.current_vector_index+=1
           # self.send_next_vector()

    def on_timeout(self):
        self.timer_tramas.stop()
        self.console.append("desborda el timer.")
        self.handle_serial_confirmation()

#COMUNICACION

    def update_serial_ports(self):
        # Limpiar el submenú de puertos
        self.ports_menu.clear()
        # Obtener la lista de puertos disponibles
        ports = serial.tools.list_ports.comports()
        # Añadir un botón para cada puerto disponible
        for port in ports:
            port_action = QAction(port.device, self)
            # Capturar el valor de `port.device` usando un argumento predeterminado en `lambda`
            port_action.triggered.connect(lambda checked, p=port.device: self.set_serial_port(p))
            self.ports_menu.addAction(port_action)

    def set_serial_port(self,port):
        self.selectedserialport=port
        self.console.append("puerto serial seteado :"+ str(port))
        print("puerto serial seteado :" + str(port))

    def send_serial(self, data = ""):
        #command = self.command_line.text()
        if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(data.encode('utf-8'))


        else:
            self.console.append("No hay conexión serial establecida")

        if self.debugmode:
            print(data)
            self.console.append(f"echo:       {data}")

    def toggle_serial_reading(self):
        if not self.serial_reading:
            # Comenzar la lectura serial
            try:
                if hasattr(self, 'selectedserialport') and self.selectedserialport:
                    baudrate=9600
                    self.serial_port = serial.Serial(self.selectedserialport, baudrate) 
                    self.serial_reading = True
                    self.serial_thread = SerialThread(self.serial_port, self.eco_mode)
                    self.serial_thread.start()
                else:
                    self.console.append("No se ha seleccionado un puerto serial.")
            except Exception as e:
                self.console.append(f"No se pudo conectar: {str(e)}")
        else:
            # Detener la lectura serial
            if self.serial_thread:
                self.serial_thread.stop()
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_reading = False
            
 ##           

    def diagram_setup(self):
            #LVL 1 
            c=10
            self.pid_l1_blocks = [
                Block("PID1", 130,  23, 60, 60, QColor(0, 255, 0, 50), {'KP1': 1, 'KI1': 2,'KD1': 0}),
                Block("PID2", 130,  133, 60, 60, QColor(0, 255, 0, 50), {'KP2': 1, 'KI2': 2,'KD2': 0})
            ]
            pid_l1_setpoints={'Vel_rueda_izq':0,'Vel_rueda_der':0}

            self.pid_l2_blocks = [
                Block("PID1", 130,  23+c, 60, 60, QColor(0, 255, 0, 50), {'KP1': 1, 'KI1': 2,'KD1': 0}),
                Block("PID2", 130,  133+c, 60, 60, QColor(0, 255, 0, 50), {'KP2': 1, 'KI2': 2,'KD2': 0})
            ]
            pid_l2_setpoints={'Vel_lineal':0,'Vel_angular':0}

            self.pid_l3_blocks = [
                Block("PID1", 130,  23+c, 60, 60, QColor(0, 255, 0, 50), {'KP1': 1, 'KI1': 2,'KD1': 0}),
                Block("PID2", 130,  133+c, 60, 60, QColor(0, 255, 0, 50), {'KP2': 1, 'KI2': 2,'KD2': 0})
            ]
            pid_l3_setpoints={'Orientacion':0,'Distancia':0,'Velociad':0}

            self.onoff_l1_blocks = [
                Block("ON/OFF", 130,  23, 60, 60, QColor(0, 255, 0, 50), {'p1': 1, 'p2': 2}),
                Block("ON/OFF", 130,  133, 60, 60, QColor(0, 255, 0, 50), {'p1': 1, 'p2': 2})
            ]
            onoff_l1_setpoints={'Vel_rueda_izq':0,'Vel_rueda_der':0}


            self.controlDiagram0=ControlDiagramWidget(image_path_mod1onoff,1,self.current_state,onoff_l1_setpoints)
            self.controlDiagram0.update_blocks(self.onoff_l1_blocks)

            self.controlDiagram1=ControlDiagramWidget(image_path_mod1pid,1,self.current_state,pid_l1_setpoints)
            self.controlDiagram1.update_blocks(self.pid_l1_blocks)

            self.controlDiagram2=ControlDiagramWidget(image_path_mod2,2,self.current_state,pid_l2_setpoints)
            self.controlDiagram2.update_blocks(self.pid_l2_blocks)

            self.controlDiagram3=ControlDiagramWidget(image_path_mod3,3,self.current_state,pid_l3_setpoints)
            self.controlDiagram3.update_blocks(self.pid_l3_blocks)

            self.controlModes = {   0:self.controlDiagram0,
                                    1:self.controlDiagram1,
                                    2:self.controlDiagram2, 
                                    3:self.controlDiagram3}

            self.currentcontrolDiagram = self.controlDiagram1
            self.current_controlmode=1
            self.currentblocks=self.currentcontrolDiagram.blocks
            self.currentcontrolDiagram.show()

    def interpret_serial_queue(self,dato):

            trama=(dato.split(','))
            
            #trama=[S,nm,Vi,Vd,Si,Sfi,Sfd,Sd,accx,accy,wx,wy,mx,my]
            if trama[0] =="S":
                    #tiempo=datetime.now()
                    #trama[0]=tiempo.strftime("%Y-%m-%d %H:%M:%S")

                    try:
                        datos_slice=[float(x) for x in trama[1:]]
                    except Exception as e:
                        print(e)
                        datos_slice=[0]*self.data_container.get_columns_number()
                    
                    self.data_container.add_data_row(datos_slice)
                    
                    return
            elif trama[0] =="I": #I de info:  caso de calibracion / testing
                    self.console.append(trama[1:])
                    #sensor_config=trama[1]
                    #self.sort_store_data(sensor_config,sample_time,trama[2:])
                    return
            elif trama[0] =="C":
                    if trama[1]=='F':# Fin de la caracterizacon
                        self.caracterizando_motores=False
                        csv_file_path='DATOS_CARACT_MOTORES'
                        np.savetxt(csv_file_path, self.caract_data, delimiter=',', fmt='%f')
                        print(f'Se guardaron {len(self.caract_data)} muestras')


                    else:
                        try:
                            datos_slice=[float(x) for x in trama[1:]]
                        except Exception as e:
                            print(e)
                            datos_slice=[0]*3 # 3 commponentes

                        self.caract_data.append(datos_slice)    
                    return
            elif trama[0] =="O":
                    self.ack_vector_sequence = True

            else:

                    print("Trama desconocida")
            return

    def toggle_debug_mode(self):
        self.debugmode = not self.debugmode
        self.console.append('debugmode'+ str(self.debugmode))

    def toggle_diagram(self):
        # Alternar la visibilidad del widget
        if self.currentcontrolDiagram.isVisible():
            self.currentcontrolDiagram.hide()  # Ocultar el widget del diagrama
            # Cambiar el tamaño del botón para ocupar el espacio del widget oculto
            #self.layout_00.setStretch(0, 0)
            #self.layout_00.setStretch(1, 1)  # Expande el botón
        else:
            self.currentcontrolDiagram.show()  # Mostrar el widget del diagrama nuevamente
            # Restaurar el tamaño original de los widgets
            #self.layout_00.setStretch(0, 1)  # Expande el widget
            #self.layout_00.setStretch(1, 0)

    def check_pre_run(self):
        print('implementar un check')

    def update_control_mode(self,modenumber):
        
        self.send_serial(f'*m{modenumber}*')

        if self.currentcontrolDiagram:
            self.currentcontrolDiagram.hide()
        

        self.currentcontrolDiagram = self.controlModes[modenumber]
        self.current_controlmode=modenumber
        self.currentblocks=self.currentcontrolDiagram.blocks
        self.update_diagram_overlay()
        self.updateParametrosTab()
        self.currentcontrolDiagram.show()
        self.layout_superior.insertWidget(0, self.currentcontrolDiagram)
        #self.layout_00.addWidget(self.currentcontrolDiagram)

    def updateParametrosTab(self):
        # Get the index of the "Parametros" tab
        index = self.tabs.indexOf(self.tabs.widget(1))
        
        # Remove the old tab
        self.tabs.removeTab(index)
        
        # Re-add the updated tab
        new_widget = self.ParamPIDTabUI(self.currentblocks)
        self.tabs.insertTab(index, new_widget, "Parametros")
        
    def GraphsTabUI(self):
        generalTab = QWidget()

        mainlayout=QHBoxLayout()

        for num_plot,plot in enumerate(self.plots):
            layout = QVBoxLayout()
            # Crear botón con imagen
            sublayout= QHBoxLayout()
            
            title_label = QLabel(f'Plot {num_plot+1} :')
            title_label.setAlignment(Qt.AlignCenter)  # Centrar el QLabel
            
            button_refresh = QPushButton(self)
            button_refresh.setIcon(QIcon(arrows_path))  # Reemplaza con la ruta correcta
            button_refresh.setIconSize(QSize(25, 25))  # Ajustar el tamaño del icono
            button_refresh.setFixedSize(25, 25)
            button_refresh.setCheckable(True)  # Hacer el botón seleccionable (toggle)
            button_refresh.clicked.connect(lambda _, p=plot: p.toggle_update()) 
            sublayout.addStretch(1)  # Añadir estiramiento antes del QLabel
            sublayout.addWidget(title_label)
            sublayout.addWidget(button_refresh)
            sublayout.addStretch(1)  # Añadir estiramiento después del QPushButton
            
            sublayout.setSpacing(2)  # Ajustar el espaciado entre widgets
            sublayout.setContentsMargins(10, 10, 10, 10)  # Ajustar los márgenes

            layout.addLayout(sublayout)

            checks_layout=QGridLayout()
            checkboxes=[]

            for i, sensor in enumerate(sensors_list):
                row = i // 2  # Dividir el índice entre 2 para obtener la fila
                col = i % 2   # Obtener el resto de la división entre 2 para obtener la columna
                checkbox = QCheckBox(sensor)
                checks_layout.addWidget(checkbox, row, col)
                # Guardar la referencia al QCheckBox
                checkboxes.append(checkbox)
                
                # Conectar la señal stateChanged a una función
                checkbox.stateChanged.connect(lambda state, n=num_plot,cbs=checkboxes[:]: self.update_plot_sensors(n,cbs))


            checks_layout.setContentsMargins(1,1,1,1)  # Ajustar los márgenes
            layout.addLayout(checks_layout)  
            mainlayout.addLayout(layout)
            mainlayout.setContentsMargins(1,1,1,1)

        generalTab.setLayout(mainlayout)
        return generalTab

    def update_state(self,command):

        if command:
            self.send_serial(f'*{command}*')

        self.current_state=self.state_machine.transition(command)
        if self.current_state=='Modo Manual': self.enable_keyboard = True
        else: self.enable_keyboard =False
        #print(f'keyboard{self.enable_keyboard}')
        self.update_command_tab()
        self.update_diagram_overlay()

    def ParamPIDTabUI(self,blocks,level=1):
        
        
        ParamTab = QWidget()
        layoutbase = QHBoxLayout()

        for block in blocks:
            layout = self.update_block_setup(block)
            layoutbase.addLayout(layout)

        sendparams_button = QPushButton("Enviar Parametros")
        sendparams_button.clicked.connect(lambda: self.state_logic()) 
        sendparams_button.clicked.connect(lambda: self.tabs.setCurrentIndex(0)) 
        # Slider para ajustar el valor
        self.slider = QSlider(Qt.Horizontal, self)
        self.value_label = QLabel('Frec. op :'+ str(self.frecop) + 'Khz' , self)
        self.slider.setMinimum(1)   # Valor mínimo del slider
        self.slider.setMaximum(100) # Valor máximo del slider
        self.slider.setValue(self.frecop)     # Valor inicial del slider
        self.slider.setTickPosition(QSlider.TicksBelow)  # Posición de las marcas de los valores
        self.slider.setTickInterval(10)  # Intervalo entre marcas

        # Conectar el cambio de valor del slider con una función
        self.slider.valueChanged.connect(self.on_value_changed_slider)

        # Disposición de los widgets
        layout3=QVBoxLayout()
        layout3.addWidget(sendparams_button)
        layout3.addWidget(self.value_label)
        layout3.addWidget(self.slider)
    
        layoutbase.addLayout(layout3)

        ParamTab.setLayout(layoutbase)

        

        return ParamTab
    
    def update_block_setup(self,block):
        
        layout = QGridLayout()
        i=0
        for param_name, param_value in block.parameters.items():
            
            param_label = QLabel(f'{param_name}:')
            param_label.setFixedSize(100,20)
            text_box = QLineEdit()
            text_box.setText(str(param_value))
            text_box.editingFinished.connect(lambda tb=text_box, pn=param_name, bn=block.name: self.update_parameter(pn, tb, bn))
            text_box.setFixedSize(100, 20)
            layout.addWidget(param_label, i, 0)
            layout.addWidget(text_box   , i, 1)
            i=i+1
  
        return layout
        
    def update_parameter(self, param_name, text_box,block_name):
        try:
            # Convert the text to the appropriate type, e.g., int or float
            new_value = int(text_box.text())  
            #print(new_value)
            self.currentcontrolDiagram.update_block_parameter(block_name, param_name, new_value)
        except ValueError:
            pass
        
    def on_value_changed_slider(self):
        # Actualiza la etiqueta con el valor actual del slider
        self.frecop = self.slider.value()
        self.value_label.setText('Frec. op :'+ str(self.frecop) + 'Khz' )
        
    def show_popup(self,title,text):
        # Crear el cuadro de mensaje
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.Information)

        # Añadir los botones
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # Ejecutar el cuadro de mensaje y capturar la respuesta del usuario
        response = msg_box.exec_()

        # Manejar la respuesta del usuario
        if response == QMessageBox.Yes:
            return True
        elif response == QMessageBox.No:
            return False
        
    def update_diagram_overlay(self):
        self.currentcontrolDiagram.update_robot_state(self.current_state)

    def update_plot_sensors(self,n,checkboxes):
        self.selected_sensors = [cb.text() for cb in checkboxes if cb.isChecked()]
        print(n,self.selected_sensors)
        self.plots[n].set_sensors_to_plot(self.selected_sensors)
        #self.request_sensor_data()
        ## tengo que unificar el pedido para los 2 sensores

    def request_sensor_data(self):
        binary_cod = "".join("1" if sensor in self.selected_sensors else "0" for sensor in sensors_list)
        self.send_serial(f'*GD{int(binary_cod,2)}*')



    def state_logic(self):
        # Verifica si el estado actual tiene una función asignada y la ejecuta
        handler = self.state_to_function.get(self.current_state)
        if handler:
            handler()

    def save_sensor_data(self):
        ret=self.show_popup("Confirmar guardado",f"Se almacenaron {self.data_container.get_rows_numer()} datos\n¿Desea guardar?")
        mi_header= 'tiempo,muestra'+','.join(sensors_list)
        if ret:
            datos=self.data_container.get_data()
            np.savetxt(csv_file_path, datos, delimiter=',', header=mi_header, comments='', fmt='%f')

    def open_csv(self):
        # Show the file dialog to select the CSV file
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        
        if file_path:
            # Create and show the table preview dialog
            dialog = TableViewDialog(file_path, self)
            if dialog.exec_() == QDialog.Accepted:  # Only save data if confirmed
                self.motordataset = dialog.get_data()  # Save the data in the main window
                print("Data imported successfully!")
                print(self.motordataset)
                # Further processing of the data can be done here.

    def open_draw_window(self):
        self.draw_window = DrawWindow(N=5)
        # Connect the signal from the drawing window to the slot in MainWindow
        try:
            self.draw_window.vectors_ready.connect(self.receive_vectors)
            self.draw_window.show()
        except Exception as e:
            print(e)

    def receive_vectors(self, vectors):
        # This function will be called when the vectors are ready
        print("Received vectors (in cm):", vectors)
        print("punto 1",vectors[0])
        self.current_vector_index =1
        self.trajectory_vectors=vectors
        self.transform_vectors()
        # Now you can use the vectors in your MainWindow logic    

    def send_next_vector(self):
 
        if self.current_vector_index >= len(self.transformed_vectors_polar):
            print("Todos los vectores enviados.")
            return

        vector = self.transformed_vectors_polar[self.current_vector_index]
        distance, angle = vector

        # Prepara los datos a enviar (modifica esto según tu protocolo)
        data_to_send = f"*FLV,{distance:.2f},{angle:.2f},100*"  # Enviando distancia y ángulo
        self.send_serial(data_to_send)
        print(f"Enviado vector: {data_to_send.strip()}")

        self.ack_vector_sequence = False

    def transform_vectors(self):
        
        if not self.trajectory_vectors or len(self.trajectory_vectors) < 2:
            print("Puntos insuficientes para trasnformar.")
            return

        
        #origin = self.trajectory_vectors[0]
        self.transformed_vectors.append((0, 0))
        self.transformed_vectors_polar.append((0, 0)) 
        # Diferencia relativa
        for i in range(1, len(self.trajectory_vectors)):
            current_point = self.trajectory_vectors[i]
            previous_point = self.trajectory_vectors[i - 1]
            
            
            delta_x = current_point[0] - previous_point[0]
            delta_y = current_point[1] - previous_point[1]
            
        
            self.transformed_vectors.append((delta_x, delta_y))
            # Calculate the polar coordinates: distance and angle
            distance = np.sqrt(delta_x**2 + delta_y**2)
            angle = np.degrees(np.arctan2(delta_y, delta_x))  # Angle in radians

            # Append the vector in polar coordinates
            self.transformed_vectors_polar.append((distance, angle))

        print("Vectores Transformados Cartesiano:", self.transformed_vectors)
        print("Vectores Transformados Polar:", self.transformed_vectors_polar)

    def CommandTabUI_update(self):
        mainlayout = QHBoxLayout()
        states_layout=QVBoxLayout()
        commands_layout = self.state_to_layout.get(self.current_state, QVBoxLayout)()
        
        
        mainlayout.addLayout(commands_layout)
        mainlayout.addLayout(states_layout)
        
        state_label= QLabel(f'Modos disponibles')
        state_label.setAlignment(Qt.AlignCenter)
        states_layout.addWidget(state_label)
        
    
        for command,next_state in self.transiciones[self.current_state].items():
            button= QPushButton(next_state)
            button.setMaximumSize(200, 50)
            button.clicked.connect(lambda _, cmd=command: self.update_state(cmd))
            states_layout.addWidget(button)
            

        
        return mainlayout
    
    def update_command_tab(self):
        if self.tabs.count() > 0:
            self.tabs.removeTab(0)  
            new_command_tab = QWidget()
            new_command_tab.setLayout(self.CommandTabUI_update())
            self.tabs.insertTab(0, new_command_tab, "Comandos")
            self.tabs.setCurrentIndex(0)          

    def update_setpoint(self,param,text_box):
        tb_text = text_box.text()
        if tb_text.isdigit():  # Check if the input is a number
            self.currentcontrolDiagram.set_setpoint(param, int(tb_text))
        else:
            print(f"Invalid input for {param}: {tb_text} is not a number")        

    def layout_manual(self):
        # Create a grid layout for arrow buttons
        grid_layout = QGridLayout()
        self.enable_keyboard = True
        # Create arrow buttons
        self.up_button = QPushButton("Up")
        self.down_button = QPushButton("Down")
        self.left_button = QPushButton("Left")
        self.right_button = QPushButton("Right")

        # Add buttons to grid layout
        grid_layout.addWidget(self.up_button, 0, 1)
        grid_layout.addWidget(self.left_button, 1, 0)
        grid_layout.addWidget(self.right_button, 1, 2)
        grid_layout.addWidget(self.down_button, 2, 1)

        # Connect button signals to slots
        self.up_button   .clicked.connect(lambda : self.send_serial('*up*'))
        self.down_button .clicked.connect(lambda key="Down" : self.send_serial(key))
        self.left_button .clicked.connect(lambda key="Left" : self.send_serial(key))
        self.right_button.clicked.connect(lambda key="Rigth": self.send_serial(key))

        return grid_layout
    
    def layout_caracterizar(self):
        master_layout = QHBoxLayout()
        layout1 = QVBoxLayout()

        generardatos_button = QPushButton("Generar Datos")
        generardatos_button.clicked.connect(self.handle_caracterizar)
        layout1.addWidget(generardatos_button)

        importar_button = QPushButton("Importar Datos")
        importar_button.clicked.connect(self.open_csv)
        layout1.addWidget(importar_button)

        calcular_button = QPushButton("Calcular modelo")
        calcular_button.clicked.connect(self.calculate_motors_models)
        layout1.addWidget(calcular_button)

        # Layout 2 for showing motor parameters
        layout2 = QVBoxLayout()
        title_label = QLabel('Motor izquierdo:')
        title_label.setAlignment(Qt.AlignCenter)
        layout2.addWidget(title_label)
        
        # Create QLabel to display the left motor equation
        self.left_motor_label = QLabel()
        self.left_motor_label.setAlignment(Qt.AlignCenter)
        layout2.addWidget(self.left_motor_label)

        title_label2 = QLabel('Motor derecho:')
        title_label2.setAlignment(Qt.AlignCenter)
        layout2.addWidget(title_label2)
        # Create QLabel to display the right motor equation
        self.right_motor_label = QLabel()
        self.right_motor_label.setAlignment(Qt.AlignCenter)
        layout2.addWidget(self.right_motor_label)

        self.update_motor_labels()
        master_layout.addLayout(layout1)
        master_layout.addLayout(layout2)

        return master_layout

    def layout_setparam(self):

        masterlayout=QVBoxLayout()
        layout=QGridLayout()

        params=self.currentcontrolDiagram.get_setpoints()
        text=state_text_mapping['Set parametros']
        label = QLabel(f'{text}')
        
        i=0
        for param,value in params.items():

            
            param_label = QLabel(f'{param}:')
            param_label.setFixedSize(100,20)
            
            text_box = QLineEdit()
            text_box.setText(str(value))
            text_box.editingFinished.connect(lambda tb=text_box, pn=param: self.update_setpoint(pn, tb))
            text_box.setFixedSize(100, 20)
            layout.addWidget(param_label, 0, i)
            layout.addWidget(text_box   , 1, i)
            i=i+1

        button= QPushButton('Setear Parametros')
        button.clicked.connect(lambda : self.state_logic())
        layout.addWidget(button)

        if self.current_controlmode==3:
            button_window= QPushButton('Dibujar Trayectoria')
            button_window.clicked.connect(lambda : self.open_draw_window())
            layout.addWidget(button_window)

            button_send= QPushButton('Enviar Trayectoria')
            button_send.clicked.connect(lambda : self.send_next_vector())
            layout.addWidget(button_send)

        masterlayout.addWidget(label)
        masterlayout.addLayout(layout)

        return masterlayout
    
    def layout_configurar(self):
        layout=QVBoxLayout()
        buttons_list={'Modo 0':0,'Modo 1':1,'Modo 2':2,'Modo 3':3}

        for name,command in buttons_list.items():
            button= QPushButton(name)
            button.clicked.connect(lambda _, cmd=command: self.update_control_mode(cmd))
            layout.addWidget(button)

        button= QPushButton('Parametros')
        button.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        layout.addWidget(button)

        return layout

    def layout_testing(self):
        layout=QHBoxLayout()

        start_button = QPushButton("Comenzar Testing")
        start_button.clicked.connect(lambda: self.handle_testing_calib())
        layout.addWidget(start_button) 

        return layout
    
    def layout_calibracion(self):
        layout=QHBoxLayout()

        start_button = QPushButton("Comenzar Calibracion")
        start_button.clicked.connect(lambda: self.handle_testing_calib())
        layout.addWidget(start_button) 

        return layout
    
    def update_eq_motor(self,b1_new,a1_new,a2_new):
        a1=a1_new
        a2=a2_new
        b1=b1_new
        try:
            equation_html = (
                r"<table style='font-size:16px; width:100%;' align='center'>"
                r"<tr>"
                r"<td style='vertical-align:middle; padding-right: 10px;'>"
                r"<span style='vertical-align: -0.5em;'>H(z) =</span>"
                r"</td>"
                r"<td>"
                r"<table>"
                r"<tr><td align='center'>{:+g} z^-1</td></tr>"
                r"<tr><td align='center'><hr style='border:1px solid black;'></td></tr>"
                r"<tr><td align='center'>1 {:+g}z^-1 {:+g}z^-2</td></tr>"
                r"</table>"
                r"</td>"
                r"</tr>"
                r"</table>"
            ).format(b1, a1 ,a2)
        except Exception as e:
            print(e)

        return equation_html

    def update_motor_labels(self):
        # Assuming params_izq and params_der are in the format [a1, a2, b1, b2]
        b1_izq, a1_izq, a2_izq = [round(value, 2) for value in self.motor_izq_consts.values()]
        b1_der, a1_der, a2_der = [round(value, 2) for value in self.motor_der_consts.values()]

        # Update left motor equation
        equation_izq = self.update_eq_motor(b1_izq, a1_izq, a2_izq)
        self.left_motor_label.setText(equation_izq)

        # Update right motor equation (you need to add another QLabel for the right motor)
        equation_der = self.update_eq_motor(b1_der, a1_der, a2_der)
        self.right_motor_label.setText(equation_der)

    def calculate_motors_models(self):
        if self.motordataset is not None:
            if self.motordataset.shape[1] >= 3:
                try:
                    # Motor Izquierdo
                    
                    if self.motors[0] is None:  
                        print(self.motordataset[:,0])
                        self.motors[0] = Motor_model(self.motordataset[:,0], self.motordataset[:,2],self.frecop)
                    else: 
                        self.motors[0].set_params(self.motordataset[:,0], self.motordataset[:,2])

                    self.motors[0].calc_parametros()
                    params=self.motors[0].get_params()
                    for i,key in enumerate(self.motor_izq_consts.keys()):
                        self.motor_izq_consts[key]=params[i]

                    
                    # Motor Derecho
                    if self.motors[1] is None:  
                        self.motors[1] = Motor_model(self.motordataset[:,0], self.motordataset[:,3],self.frecop)
                    else:  
                        self.motors[1].set_params(self.motordataset[:,0], self.motordataset[:,3])

                    self.motors[1].calc_parametros()
                    params=self.motors[1].get_params()
                    for i,key in enumerate(self.motor_der_consts.keys()):
                        self.motor_der_consts[key]=params[i]

                    # Update UI 
                    
                    self.update_motor_labels()
                    return
                
                except Exception as e:
                    print(f"Error calculando modelo de motores: {e}")
                
            else:
                print("Datos de motores no correctamente cargados")
            
        else:
            print("No hay data para calcular")

    def handle_configurar(self):
        data = self.currentcontrolDiagram.get_blocks_parameters()
        vector_str = ','.join(map(str, data))
        trama = f"*C{vector_str}*"
        self.send_serial(trama)

    def handle_set_parametros(self):
        data_list = self.currentcontrolDiagram.get_setpoints()
        #print('////')
        values_string = ','.join(str(value) for value in data_list.values())
        trama = f"*{mode_frame[self.current_controlmode]},{values_string}*"
        self.send_serial(trama)

    def handle_testing_calib(self):
        self.send_serial('*start*')
        self.timer_tramas.start(1000) #milliseconds 
        self.serial_confirmation=False
        print('timer on')
        
    def handle_serial_confirmation(self):
        # Method to handle serial confirmation when it is received
        if not(self.serial_confirmation):
            # Example: If confirmation is received, stop the timer
            self.console.append("No se recibio confirmacion.")
        else:
            self.console.append("Confirmacion recibida")   
        
    def handle_keyboard_press(self,key):
        self.send_serial(f'*{key}*')
        pass
    
    def handle_caracterizar(self):
        if not self.caracterizando_motores:
            ret=self.show_popup('¿Todo listo para comenzar?','Colocar el robot en una posición adecuada')
            if ret:
                print('y')
                self.send_serial('*start*')
                self.caracterizando_motores= True
        else:
            self.console.append('Aguarde por favor')
        
    def keyPressEvent(self, event):
        if self.enable_keyboard:
            if event.key() in [Qt.Key_W, Qt.Key_A, Qt.Key_S, Qt.Key_D]:
                self.handle_keyboard_press(event.key())
        else:
            super().keyPressEvent(event)
         
    def vector_length(p1, p2):
        # Calculate the squared differences for each dimension
        squared_diffs = [(p2[i] - p1[i]) ** 2 for i in range(len(p1))]
        
        # Sum the squared differences and take the square root
        return np.sqrt(sum(squared_diffs))

class SerialThread(QThread):
    def __init__(self, serial_port,eco_mode=False):
    #def __init__(self, serial_port, callback):
        super(SerialThread, self).__init__()
        self.serial_port = serial_port
        #self.callback = callback
        self.running = True
        self.serial_eco_mode=eco_mode
        self.serialQueue=Queue()
        print("Puerto serial Init")
        

    def run(self):
        while self.running:
            if self.serial_port.in_waiting:
                data = self.serial_port.readline().strip().decode('utf-8')
                sample_time = (datetime.now() - start_time).total_seconds()

                parts = data.split(',')
                data = ','.join(parts[:2] + [str(sample_time)] + parts[2:])
                self.serialQueue.put(data)
                if self.serial_eco_mode:
                    print(data)

    def stop(self):
        self.running = False
        self.wait()

    def get_serial_data(self):
        if not self.serialQueue.empty():
            data=self.serialQueue.get()
        else:
            data=0
        return data

app = QApplication(sys.argv)
window = MainWindow(transiciones)
window.show()
app.exec()

