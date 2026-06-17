import network
import socket
import rp2
import math
import time
from machine import Pin

# ==========================================
# 1. EL MÚSCULO: MÁQUINA DE ESTADOS (PIO)
# ==========================================
@rp2.asm_pio(out_init=(rp2.PIO.OUT_LOW,) * 8, out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def dac_r2r():
    wrap_target()
    pull()          # Espera a que Python mande el dato
    out(pins, 8)    # Lo saca por los 8 pines en 1 ciclo
    wrap()

# ==========================================
# 2. PRECALCULAR ONDAS (8 Bits para R2R))
# ==========================================
puntos_seno = []
puntos_cuadrada = []
puntos_sierra = []
N = 100 # Puntos por ciclo

print("Calculando geometría de las ondas...")
for i in range(N):
    # Onda Seno (0 a 255)
    puntos_seno.append(int(127.5 + 127.5 * math.sin(2 * math.pi * i / N)))
    
    # Onda Cuadrada (Mitad 255, Mitad 0)
    if i < (N / 2):
        puntos_cuadrada.append(255)
    else:
        puntos_cuadrada.append(0)
        
    # Onda Diente de Sierra (0 a 255)
    puntos_sierra.append(int((255 / (N - 1)) * i))

onda_actual = puntos_seno 

# ==========================================
# 3. CONEXIÓN WI-FI AL HOTSPOT DE LA PI 5
# ==========================================
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

if not wlan.isconnected():
    print("Conectando al Hotspot 'Raspi_memo'...")
    wlan.connect('Raspi_memo') 
    
    # Bucle de espera seguro para no colgar el sistema
    intentos = 0
    while not wlan.isconnected() and intentos < 20:
        time.sleep(1)
        print(".", end="")
        intentos += 1

if wlan.isconnected():
    print("\n¡Conectado exitosamente!")
    print("IP de la Pico W:", wlan.ifconfig()[0])
else:
    print("\nFallo al conectar al Wi-Fi. Revisa la red de la Pi 5.")

# ==========================================
# 4. CONEXIÓN AL SERVIDOR PI 5 (Socket TCP)
# ==========================================
cliente = socket.socket()
IP_PI_5 = '192.168.100.167'  # <-- IP MAESTRA DE TU PI 5
PUERTO = 8080

try:
    cliente.connect((socket.getaddrinfo(IP_PI_5, PUERTO)[0][-1]))
    cliente.setblocking(False) # CRÍTICO: Hace que recv() no pause el código
    print(f"Conectado al servidor TCP en {IP_PI_5}:{PUERTO}")
except OSError:
    print("Error: No se encontró el servidor Node.js. Iniciando modo autónomo...")

# ==========================================
# 5. INICIALIZACIÓN DEL HARDWARE PIO
# ==========================================
frecuencia_hz = 1000 # Arrancamos a 1 kHz por defecto
f_pio = frecuencia_hz * N * 2

sm = rp2.StateMachine(0, dac_r2r, freq=f_pio, out_base=Pin(0))
sm.active(1)

print("Generador R2R por Hardware listo y esperando comandos...")

# ==========================================
# 6. EL BUCLE PRINCIPAL ASÍNCRONO
# ==========================================
try:
    while True:
        # TAREA A: Escuchar al servidor Node.js
        try:
            datos_crudos = cliente.recv(1024)
            if datos_crudos:
                # SEPARAMOS POR EL SALTO DE LÍNEA Y PROCESAMOS UNO POR UNO
                paquetes = datos_crudos.decode('utf-8').split('\n')
                
                for comando in paquetes:
                    comando = comando.strip()
                    if not comando: 
                        continue # Ignorar líneas vacías
                        
                    print(">> Comando procesado:", comando)
                    
                    # --- Lógica de conmutación ---
                    if comando == "SENO":
                        onda_actual = puntos_seno
                    elif comando == "CUADRADA":
                        onda_actual = puntos_cuadrada
                    elif comando == "SIERRA":
                        onda_actual = puntos_sierra
                        
                    # --- Lógica de Frecuencia ---
                    elif comando.startswith("FREQ:"):
                        try:
                            nueva_freq_hz = int(comando.split(":")[1])
                            if nueva_freq_hz > 0:
                                frecuencia_hz = nueva_freq_hz
                                f_pio_nueva = frecuencia_hz * N * 2
                                
                                sm.active(0)
                                sm = rp2.StateMachine(0, dac_r2r, freq=f_pio_nueva, out_base=Pin(0))
                                sm.active(1)
                        except Exception as e:
                            print("Error al procesar la frecuencia:", e)
        
        except OSError:
            # Si no hay mensajes nuevos, el código simplemente pasa de largo
            pass 

        # TAREA B: Bombear datos a la Máquina de Estados
        # El CPU inyecta la tabla entera al FIFO a máxima velocidad.
        # El PIO se encarga de frenarlos y sacarlos al ritmo exacto del reloj.
        for valor in onda_actual:
            sm.put(valor)
            
except KeyboardInterrupt:
    sm.active(0)
    print("\nGenerador detenido de forma segura.")
