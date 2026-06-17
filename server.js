const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const net = require('net');

// 1. Configuracion del Servidor Web (Para tu telefono)
const app = express();
const serverHttp = http.createServer(app);
const io = new Server(serverHttp);

// Servir archivos estaticos de la carpeta 'public' (Aqui evitamos el internet!)
app.use(express.static('public'));

// 2. Configuraci�n del Servidor TCP (Para la Pico W)
let picoSocket = null; // Guardaremos la conexion de la Pico W aqui

const serverTCP = net.createServer((socket) => {
    console.log('Pico W conectada al hardware!');
    picoSocket = socket;

    socket.on('error', (err) => {
        console.log('Error en la Pico W:', err.message);
    });

    socket.on('close', () => {
        console.log('Pico W desconectada');
        picoSocket = null;
    });
});

// 3. El Puente de Comunicacion (Telefono <--> Servidor <--> Pico W)
io.on('connection', (clienteWeb) => {
    console.log('Telefono conectado a la interfaz web');

    // Cuando el telefono aprieta un boton en la pagina:
    clienteWeb.on('comando_generador', (instruccion) => {
        console.log('Orden desde el telefono:', instruccion);
        
               // Si la Pico W esta conectada, le rebotamos el mensaje inmediatamente
        if (picoSocket) {
            // Convertimos a String por seguridad y le pegamos el salto de l�nea
            picoSocket.write(String(instruccion) + '\n'); 
        } else {
            console.log('Aviso: La orden no se envi�, Pico W no conectada');
        }
    });
});

// 4. Encender los motores
serverTCP.listen(8080, () => {
    console.log('Servidor Hardware (Pico W) escuchando en puerto 8080');
});

serverHttp.listen(3000, () => {
    console.log('Servidor Web (Telefono) escuchando en puerto 3000');
});