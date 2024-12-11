import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class PlotWidget(QWidget):

    

    def __init__(self, data_container, sensors_list, frec,sensors=[], N=100):
        super().__init__()
        self.data_container = data_container
        self.current_plot_sensors = sensors
        
        self.sensors_list = sensors_list

        self.enable_update = True
        self.N = N
        self.period=10
        self.frec=frec
        self.mode=1

        # Conectar la señal de cambio de sensores
        #self.sensors_changed.connect(self.set_sensors_to_plot)

        self.figure, self.ax = plt.subplots()
        self.figure.tight_layout()
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.plot_data = {sensor: [[], []] for sensor in sensors}  # Diccionario para datos de cada sensor
        self.plot()
        self.canvas.mpl_connect('scroll_event', self.zoom)
        


    def plot(self):
        self.ax.plot([], [])  # Crear un gráfico vacío
        self.ax.set_xlabel('Tiempo')
        self.ax.set_ylabel('Sensor')
        self.ax.set_title( 'Plot')
        self.canvas.draw()
        

    def set_sensors_to_plot(self, sensors):
        self.current_plot_sensors = sensors
        self.plot_data = {sensor: [[], []] for sensor in sensors}

    def toggle_update(self):
        self.enable_update = not(self.enable_update)   

    def update(self):
        if len(self.current_plot_sensors) > 0 and self.enable_update == True:
            datos = self.data_container.get_data()
            if datos.shape[0] > 2:  # Asegurarse de que hay suficientes datos
                for sensor in self.current_plot_sensors:

                    try:
                        pos = self.sensors_list.index(sensor)  # Encuentra el índice del sensor
                    except ValueError:
                        pos = None

                    if pos is not None:
                        new_datax = datos[2:, 0] * self.frec / 1000  # Usar datos de la columna 0 para X
                        new_datay = datos[2:, pos + 2]  # Usar datos de la columna correspondiente para Y
                        new_datay[0] = None
                        # Actualizar los datos de la gráfica
                        self.plot_data[sensor][0].extend(new_datax)
                        self.plot_data[sensor][1].extend(new_datay)

                        # Modo 0 (ventana móvil de N muestras)
                        if self.mode == 0:
                            try:
                                if len(self.plot_data[sensor][0]) > self.N:
                                    self.plot_data[sensor][0] = self.plot_data[sensor][0][-self.N:]
                                    self.plot_data[sensor][1] = self.plot_data[sensor][1][-self.N:]
                            except Exception as e:
                                print(f"error: {str(e)}")

                        # Modo 1 (fijar el eje X hasta el límite)
                        if self.mode == 1:
                            # Obtener el tiempo máximo de los datos actuales
                            max_time = self.plot_data[sensor][0][-1] if len(self.plot_data[sensor][0]) > 0 else 0

                            # Determinar en qué "ciclo" estamos
                            cycle = int(max_time // self.period)  # Dividir el tiempo por el período para obtener el ciclo actual

                            # Si hemos superado el ciclo actual, reiniciar los datos y empezar el siguiente ciclo
                            if max_time >= (cycle + 1) * self.period:
                                # Limpiar los datos para este ciclo
                                self.plot_data[sensor][0] = [max_time % self.period]  # Reiniciar desde el comienzo del nuevo ciclo
                                self.plot_data[sensor][1] = [new_datay[-1]]  # Iniciar con el último valor de datos


                # Limpiar el gráfico antes de redibujar
                self.ax.clear()
                
                # Dibujar los datos actualizados para cada sensor
                for sensor, (datax, datay) in self.plot_data.items():
                    self.ax.plot(datax, datay, label=sensor, marker='o', linewidth=.5)

                self.ax.set_xlabel('tiempo')
                self.ax.set_ylabel('sensor')
                self.ax.set_title('Sample Plot')
                self.ax.legend()

                # Ajustar el rango del eje X si estamos en el modo 1
                if self.mode == 1:
                    if len(self.plot_data[self.current_plot_sensors[0]][0]) > 0:
                        # Asegurarse de que el eje X se mantiene dentro del rango de un ciclo (n*periodo a (n+1)*periodo)
                        self.ax.set_xlim(cycle * self.period, (cycle + 1) * self.period)

                # Redibujar el gráfico
                self.canvas.draw()

            
    def zoom(self, event):
        base_scale = 1.2
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()

        xdata = event.xdata  # Coordenadas X del puntero del ratón
        ydata = event.ydata  # Coordenadas Y del puntero del ratón

        if event.button == 'up':
            # Zoom in
            scale_factor = 1 / base_scale
        elif event.button == 'down':
            # Zoom out
            scale_factor = base_scale
        else:
            # No hacer nada si no se ha usado el scroll
            scale_factor = 1

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        self.ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * (relx)])
        self.ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * (rely)])

        self.canvas.draw_idle()
    

