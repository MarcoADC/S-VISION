import numpy as np
import matplotlib.pyplot as plt
import control as ctrl
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import dlti, dlsim

# Define el modelo de segundo orden con el cero en z=0
def second_order_model(u, b1, a1, a2):
    num = [b1, 0]  # Fuerza el cero en z=0
    den = [1, a1, a2]
    system = dlti(num, den, dt=0.1)  # Especifica el tiempo de muestreo
    _, y = dlsim(system, u)
    return y.ravel()

# Carga y limpia los datos
#data_motores = 'DATOS_CARACT_MOTORES_2.csv'
#data = np.genfromtxt(data_motores, delimiter=',')
#data = data[~np.isnan(data).any(axis=1)]
#data = data[~np.isinf(data).any(axis=1)]

# Define los datos de entrada y salida
#vin = 3.38  # Voltaje de entrada constante
#u_data = np.full(len(data), vin)  # datos de entrada constantes
#y_data = data[:, 3]  # datos de salida

data = pd.read_csv('DATOSONOFF.csv')


#u_data = np.genfromtxt('PWM_full_V.csv', delimiter=',')
#y_data = np.genfromtxt('VRD_full.csv', delimiter=',')


u_data=data['REG']*7.4/65535
y_data=data['VRD']
y_data2=data['VRI']
# Ajuste del modelo
initial_guess = [1.0, 1.0, 1.0]  # Valores iniciales para b1, a1, a2
params, _ = curve_fit(second_order_model, u_data, y_data, p0=initial_guess)

# Parámetros ajustados
b1, a1, a2 = params
print("Parámetros ajustados:b0="," b1 =", b1, ", a1 =", a1, ", a2 =", a2)

# Crear el sistema usando los parámetros ajustados
num = [b1, 0]
den = [1, a1, a2]
system = dlti(num, den, dt=0.1)

# Calcular la respuesta del modelo con los datos de entrada
_, y_model = dlsim(system, u_data)

# Grafica los datos
fig, ax1 = plt.subplots()

# Plot y_data and y_data2 on the left y-axis
ax1.plot(y_data / 20, label='($\omega$) exprimental ', color='blue')
ax1.plot(y_model /20, label='($\omega$) modelo ', color='red')
#ax1.plot(y_data2 / 20, label='Motor Der rad/s', color='red')
ax1.set_ylabel('Rad/s ')
ax1.legend(loc='upper left')

# Create a second y-axis for u_data
ax2 = ax1.twinx()
ax2.plot(u_data, label='Vin', color='black', linestyle='--')
ax2.set_ylabel('Vin (V)')
ax2.legend(loc='upper right')

plt.title("Velocidad medida, respuesta del modelo y tensión de entrada")
plt.show()



dt = 0.1
system = ctrl.TransferFunction(num, den, dt=dt)

# Calculate poles and zeros
poles = ctrl.poles(system)
zeros = ctrl.zeros(system)

# Plot the root locus
plt.figure(figsize=(10, 6))
ctrl.root_locus(system, grid=True)

# Plot the zeros and poles
zero_plot = plt.scatter(zeros.real, zeros.imag, marker='o', color='blue', label='Zeros', s=100)
pole_plot = plt.scatter(poles.real, poles.imag, marker='x', color='red', label='Poles', s=100)


# Annotate the plot
for z in zeros:
    #plt.annotate(f'Zero: {z:.2f}', (z.real, z.imag), textcoords="offset points", xytext=(0,10), ha='center')
    pass
for p in poles:
    plt.annotate(f'Pole: {p:.2f}', (p.real, p.imag), textcoords="offset points", xytext=(0,10), ha='center')

# Set plot labels and title
plt.title("Root Locus of the Transfer Function with Zeros and Poles")
plt.xlabel("Real Axis")
plt.ylabel("Imaginary Axis")
plt.axhline(0, color='black', lw=0.5, ls='--')  # Horizontal line at y=0
plt.axvline(0, color='black', lw=0.5, ls='--')  # Vertical line at x=0
plt.legend(handles=[zero_plot, pole_plot])
plt.grid()
plt.show()


def plotsold():
    ######################
    dt = 0.01  # Tiempo de muestreo

    # Define la señal de entrada que aumenta de 0 a 7.5 V en incrementos de 0.5 V
    start_value = 0.0  # Valor inicial
    end_value = 7.5    # Valor final
    increment = 0.5    # Incremento
    u_data = np.arange(start_value, end_value + increment, increment)

    # Rellenar el resto con el último valor si es necesario
    u_data_full = np.concatenate([u_data, np.full(100 - len(u_data), u_data[-1])])  # Ajustar a longitud deseada

    # Crear la función de transferencia
    num = [b0, b1]  # Numerador
    den = [1, a1, a2]  # Denominador
    system = dlti(num, den, dt=dt)

    # Simular la respuesta del sistema
    t_out, y_response = dlsim(system, u_data_full)

    # Graficar la señal de entrada y la respuesta del sistema
    plt.figure(figsize=(12, 6))

    # Graficar la señal de entrada
    plt.subplot(2, 1, 1)
    plt.plot(u_data_full, label='Entrada (u)', color='blue')
    plt.title("Señal de Entrada")
    plt.xlabel("Muestras")
    plt.ylabel("Tensión (V)")
    plt.axhline(0, color='black', lw=0.5, ls='--')
    plt.grid()
    plt.legend()

    # Graficar la respuesta del sistema
    plt.subplot(2, 1, 2)
    plt.plot(t_out, y_response, label='Respuesta del Sistema (y)', color='green')
    plt.title("Respuesta del Sistema")
    plt.xlabel("Tiempo (s)")
    plt.ylabel("Salida (V)")
    plt.axhline(0, color='black', lw=0.5, ls='--')
    plt.grid()
    plt.legend()

    plt.tight_layout()
    plt.show()
