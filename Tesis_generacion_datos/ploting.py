import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the CSV data
#data1 = pd.read_csv('datos_sensoresR_LIMITTESTING.csv')

#data1 = pd.read_csv('datos_sensoresONOFF.csv')
data1 = pd.read_csv('datos_sensoresONOFF.csv')
#data2 = pd.read_csv('datos_sensoresR_multitest.csv')
#data3 = pd.read_csv('datos_sensoresR_40_20_0.csv')

# Parámetros para la señal escalón
TS=0.1 #segs
t_inicio = 176.4  # Tiempo en el que comienza el escalón
v = 400        # Amplitud del escalón

t1=t_inicio-TS
t2=178
print(t2-t1)
# Crear señal escalón
step_signal = np.where(data1['Muestra']*TS >= t_inicio, v, 0)


# Inspect the data to understand its structure
#print(data.head())  # Shows the first few rows to identify column names

# Apply moving average smoothing
window_size = 3  # Adjust the window size as needed
#data['muestra_smoothed'] = data['muestra'].rolling(window=window_size).mean()
data1['velr_izq_smoothed'] = data1['VRI'].rolling(window=window_size).mean()

# Puntos de tiempo para las líneas verticales



plt.figure(figsize=(10, 15))

# First subplot
#plt.subplot(3, 1, 1)  # (rows, columns, index)
plt.plot(data1['Muestra']*TS, data1['VRI'], label='Vel Rizq', color='black',linestyle='--')

#plt.plot(data1['Muestra']*TS, data1['velr_izq_smoothed'] , label=f'Vel', color='purple', linestyle='--')
#plt.plot(data1['tiempo']*TS, data1['velr_izq_smoothed'], label='prom 3m', color='blue')

# Agregar líneas horizontales para los SetPoints
plt.axhline(y=200, color='green', linestyle='-', linewidth=1, label='SetPoint His. (-)')
plt.axhline(y=300, color='orange', linestyle='-', linewidth=1, label='SetPoint')
plt.axhline(y=400, color='red', linestyle='-', linewidth=1, label='SetPoint His. (+)')





plt.grid(True)
plt.legend()
plt.title('Velocidad rueda izquierda con control PI; Kp=5 Ki=5')
plt.xlabel('Tiempo (seg)')
plt.ylabel('Velocidad (mm/seg)')




plt.show()

