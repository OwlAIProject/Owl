const http = require('http');
const next = require('next');
const httpProxy = require('http-proxy');

const baseUrl = process.env.OWL_WEB_BASE_URL || 'http://localhost';
const port = process.env.OWL_WEB_PORT || 3000;
const apiBaseUrl = process.env.OWL_WEB_API_BASE_URL || 'http://localhost';
const apiPort = process.env.OWL_WEB_API_PORT || 8000;
const apiUrl = `${apiBaseUrl}:${apiPort}`;

const dev = process.env.OWL_WEB_ENVIRONMENT !== 'production';
const app = next({ dev });
const handle = app.getRequestHandler();
const proxy = httpProxy.createProxyServer({});

app.prepare().then(() => {
  const server = http.createServer((req, res) => {
    if (req.url.startsWith('/api/socket')) {
      req.url = req.url.replace('/api/socket', '')
      req.url = '/socket.io/' + req.url;
      proxy.web(req, res, {
        target: apiUrl,
        ws: true,
      });
    } else {
      handle(req, res);
    }
  });

  server.on('upgrade', (req, socket, head) => {
    if (req.url.startsWith('/api/socket')) {
      req.url = req.url.replace('/api/socket', '')
      req.url = '/socket.io/' + req.url;
      proxy.ws(req, socket, head, {
        target: apiUrl,
      });
    }
  });

  server.listen(port, (err) => {
    if (err) throw err;
    console.log(`> Ready on ${baseUrl}:${port}`);
  });
});