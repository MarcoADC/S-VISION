import numpy as np
import matplotlib.pyplot as plt
#from scipy.linalg import lstsq
from scipy.optimize import curve_fit
from scipy.signal import dlti, dlsim


class Motor_model():
    def __init__(self,data_input,data_output,TS):
        self.input =data_input* (7.4 / 65535) #Tension bat/ registro
        self.output=data_output
        self.TS=TS
        


    def calc_parametros(self):
        N = len(self.input)
        if len(self.output) != N:
            raise ValueError("Las señales de self.input y self.output deben tener la misma longitud")

        def second_order_model(u,b1, a1, a2):
            num = [b1, 0]  # Fuerza el cero en z=0
            den = [1, a1, a2]
            system = dlti(num, den, dt=self.TS/1000)  # Especifica el tiempo de muestreo
            _, y = dlsim(system, u)
            return y.ravel()


        # Ajuste del modelo
        initial_guess = [1.0, 1.0, 1.0]  # Valores iniciales para b1, a1, a2
        self.params, _ = curve_fit(second_order_model, self.input, self.output, p0=initial_guess)
        print(f'params{self.params}')


    def get_params(self):
        return self.params

    
    def set_params(self,data_input,data_output):
        N = len(self.input)
        if len(self.output) != N:
            raise ValueError("Las señales de input y output deben tener la misma longitud")
        self.input =data_input*7,4/65535 #Tension bat/ registro
        self.output=data_output


    def plot_sistem(self):


        # Crear el sistema usando los parámetros ajustados
        
        num = [self.params[0], 0]
        den = [1, self.params[1], self.params[2]]
        system = dlti(num, den, dt=self.TS/1000)

        # Calcular la respuesta del modelo con los datos de entrada
        _, y_model = dlsim(system, self.input)
        # Graficar la señal original y la señal ajustada
        plt.figure()
        plt.plot(self.output, label=' Original')
        plt.plot(y_model, label='Sistema', linestyle='--')
        plt.xlabel('Tiempo')
        plt.ylabel('Respuesta')
        plt.legend()
        plt.title('Respuesta del sistema medida vs simulada')
        plt.show()

