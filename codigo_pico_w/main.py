import machine
import math
import time
import network
import socket

# ==========================================
# 1. CONFIGURACION SPI Y DAC
# ==========================================
spi = machine.SPI(0, baudrate=10000000, polarity=0, phase=0, sck=machine.Pin(18), mosi=machine.Pin(19))
cs = machine.Pin(16, machine.Pin.OUT)
cs.value(1)

def enviar_dac(valor):
    valor = int(valor) & 0x0FFF
    comando = 0x3000 | valor
    cs.value(0)
    spi.write(bytearray([(comando >> 8) & 0xFF, comando & 0xFF]))
    cs.value(1)

# ==========================================
# 2. PRECALCULAR TODAS LAS ONDAS (LUTs)
# ==========================================
puntos_seno = []
puntos_cuadrada = []
puntos_sierra = []

for i in range(100):
    # Onda Senoidal
    puntos_seno.append(int(2047 + 2047 * math.sin(2 * math.pi * i / 100)))
    
    # Onda Cuadrada (50% de ciclo util)
    if i < 50:
        puntos_cuadrada.append(4095)
    else:
        puntos_cuadrada.append(0)
        
    # Onda Diente de Sierra
    puntos_sierra.append(int((4095 / 99) * i))

# Variable maestra: define que onda se esta dibujando actualmente
onda_actual = puntos_seno 

# ==========================================
# 3. CONEXION WIFI
# ==========================================
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    print("Conectando a la red WiFi...")
    wlan.connect('Raspi_memo') # <-- PON TUS DATOS AQUI
    while not wlan.isconnected():
        time.sleep(0.5)
        print(".", end="")
print("\nConectado! IP de la Pico W:", wlan.ifconfig()[0])

# ==========================================
# 4. CONEXION AL SERVIDOR PI 5 (Socket TCP)
# ==========================================
cliente = socket.socket()
IP_PI_5 = '192.168.100.167.'  # <-- PON LA IP DE TU PI 5 AQUI
PUERTO = 8080

try:
    cliente.connect((socket.getaddrinfo(IP_PI_5, PUERTO)[0][-1]))
    cliente.setblocking(False) 
    print("Conectado al servidor maestro de la Pi 5")
except OSError:
    print("Error: No se encontro el servidor. Iniciando modo autonomo...")

# ==========================================
# 5. LA MAQUINA DE ESTADOS
# ==========================================
tiempo_anterior = time.ticks_us()
intervalo_onda = 500 
indice = 0

print("Generador AWG listo y esperando comandos...")

while True:
    tiempo_actual = time.ticks_us()
    
    # TAREA A: Dibujar la onda seleccionada
    if time.ticks_diff(tiempo_actual, tiempo_anterior) >= intervalo_onda:
        enviar_dac(onda_actual[indice])
        indice = (indice + 1) % 100
        tiempo_anterior = tiempo_actual
        
    # TAREA B: Escuchar al servidor
    try:
        mensaje = cliente.recv(1024)
        if mensaje:
            comando = mensaje.decode('utf-8').strip()
            print(">> Cambio detectado:", comando)
            
            # --- Logica de conmutacion ---
            if comando == "SENO":
                onda_actual = puntos_seno
            elif comando == "CUADRADA":
                onda_actual = puntos_cuadrada
            elif comando == "SIERRA":
                onda_actual = puntos_sierra
            elif comando == "MAS_RAPIDO":
                intervalo_onda = max(50, intervalo_onda - 100)
            elif comando == "MAS_LENTO":
                intervalo_onda = intervalo_onda + 100
                
    except OSError:
        pass