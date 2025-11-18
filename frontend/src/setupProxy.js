const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      onProxyReq: function(proxyReq) {
        // Add required auth headers for development
        proxyReq.setHeader('X-User-Email', 'dev@example.com');
        proxyReq.setHeader('X-Proxy-Secret', 'dev-secret');
      }
    })
  );
};
