const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const net = require('net');

const app = express();
const serverHttp = http.createServer(app);
const io = new Server(serverHttp);

app.use(express.static('public'));

let picoSocket = null;

const serverTCP = net.createServer((socket) => {
    console.log('Pico W conectada!');
    picoSocket = socket;
    io.emit('estado_pico', { conectada: true });

    socket.on('close', () => {
        picoSocket = null;
        io.emit('estado_pico', { conectada: false });
    });
});

io.on('connection', (clienteWeb) => {
    clienteWeb.emit('estado_pico', { conectada: picoSocket !== null });
    clienteWeb.on('comando_generador', (instruccion) => {
        if (picoSocket) picoSocket.write(String(instruccion) + '\n');
    });
});

serverTCP.listen(8080);
serverHttp.listen(3000, () => console.log('Sistema AWG listo en puerto 3000'));