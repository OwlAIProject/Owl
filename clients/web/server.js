const http = require('http');
const next = require('next');
const httpProxy = require('http-proxy');

const port = process.env.PORT || 3000;
const dev = process.env.NODE_ENV !== 'production';
const app = next({ dev });
const handle = app.getRequestHandler();

const proxy = httpProxy.createProxyServer({});

const backendBaseUrl = process.env.OWL_API_URL || 'http://127.0.0.1:8000';

app.prepare().then(() => {
  const server = http.createServer((req, res) => {
    if (req.url.startsWith('/api/socket')) {
      req.url = req.url.replace('/api/socket', '')
      req.url = '/socket.io/' + req.url;
      proxy.web(req, res, {
        target: backendBaseUrl,
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
        target: backendBaseUrl,
      });
    }
  });

  server.listen(port, (err) => {
    if (err) throw err;
    console.log(`> Ready on http://127.0.0.1:${port}`);
  });
});