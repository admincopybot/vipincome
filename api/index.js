// Vercel entry point - redirects to public/index.html
const fs = require('fs');
const path = require('path');

export default function handler(req, res) {
  const indexPath = path.join(__dirname, 'public', 'index.html');
  const indexHTML = fs.readFileSync(indexPath, 'utf8');
  
  res.setHeader('Content-Type', 'text/html');
  res.send(indexHTML);
}