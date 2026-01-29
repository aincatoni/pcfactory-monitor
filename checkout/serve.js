#!/usr/bin/env node

/**
 * Simple HTTP server para servir el dashboard
 * Uso: node serve.js
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8080;

const mimeTypes = {
  '.html': 'text/html',
  '.json': 'application/json',
  '.js': 'text/javascript',
  '.css': 'text/css',
};

const server = http.createServer((req, res) => {
  let filePath = '.' + req.url;
  if (filePath === './') {
    filePath = './dashboard.html';
  }

  const extname = path.extname(filePath);
  const contentType = mimeTypes[extname] || 'text/plain';

  fs.readFile(filePath, (error, content) => {
    if (error) {
      if (error.code === 'ENOENT') {
        res.writeHead(404);
        res.end('404 - File not found');
      } else {
        res.writeHead(500);
        res.end('500 - Internal server error');
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

server.listen(PORT, () => {
  console.log(`\n🚀 Dashboard servidor iniciado en: http://localhost:${PORT}\n`);
  console.log(`   Abre tu navegador en: http://localhost:${PORT}/dashboard.html\n`);
  console.log(`   Presiona Ctrl+C para detener el servidor\n`);
});
