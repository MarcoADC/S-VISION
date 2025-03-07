import numpy as np
import matplotlib.pyplot as plt
import control as ctrl  # Biblioteca de control

# Parámetros del sistema discreto
T_s = 0.1  # Tiempo de muestreo
a1 = -0.74  # Coeficiente del sistema (depende de zeta y wn)
a2 = -0.13   # Coeficiente del sistema (depende de zeta y wn)

# Sistema discreto con un cero en 0
numerator = [121.2, 0]  # Numerador: z
denominator = [1, a1, a2]  # Denominador: z^2 + a1*z + a2
plant = ctrl.TransferFunction(numerator, denominator, T_s)  # Sistema discreto
print("Planta discreta (G(z)):")
print(plant)

# Parámetros del controlador PID
Kp = 0.00005  # Ganancia proporcional
Ki = 0.0001  # Ganancia integral
Kd = 0  # Ganancia derivativa

# Controlador PID en tiempo discreto
pid_numerator = [Kd, Kp, Ki * T_s]  # Numerador
pid_denominator = [1, -1]           # Denominador para la parte integral
pid = ctrl.TransferFunction(pid_numerator, pid_denominator, T_s)
print("\nControlador PID discreto (C(z)):")
print(pid)

# Sistema en lazo cerrado
open_loop = pid * plant  # Lazo abierto: C(z) * G(z)
closed_loop = ctrl.feedback(open_loop, 1)  # Lazo cerrado: C(z) * G(z) / (1 + C(z) * G(z))

# Simulación de la respuesta escalón
time = np.arange(0, 20, T_s)  # Tiempo de simulación
time, response = ctrl.step_response(closed_loop, time)

# Graficar la respuesta
plt.figure(figsize=(10, 6))
plt.step(time, response, label="Respuesta con PID", where='post')
plt.title("Respuesta del Sistema Discreto en Lazo Cerrado con Controlador PID")
plt.xlabel("Tiempo (s)")
plt.ylabel("Salida")
plt.grid()
plt.legend()
plt.show()