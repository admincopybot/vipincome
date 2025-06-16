import jwt from 'jsonwebtoken';
import { NextApiRequest } from 'next';

export interface JWTPayload {
  sub: string;
  iat: number;
  exp: number;
}

// RS256 Public Key for OneClick Trading JWT validation
const PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4f5wg5l2hKsTeNem/V41
fGnJm6gOdrj8ym3rFkEjWT2btf06kkstX0BdVqKyGJm7TQsLt3nLDj9dxKwNsU0f
Vp4H3VHZrQNxVOgB2wG6dRkj7w+7QbqMTBJfEVUhkE9g0fOhp9Xg4GdO8g7N1qPb
f8n0WzGLWVFT5XPTfp5PaO3F6Q8Z5g5v1p4A2O4F8DQ8+P6K+N9w6zKtW5f6qW8x
f+bT7I7KqGbTr2XM7A3t0vOj5VRe8VQ7kK7Af6z8hD2L9Rg6K5z8X7g0+hWJn5zE
YOJr7qFzO5zRoE8TI6L8c4aZ6Eq2G6yKo8Y5J7cxW1yV+Q+p9zKJ9nK7p1Q2ov5X
QIDAQAB
-----END PUBLIC KEY-----`;

export function validateJWT(token: string): JWTPayload | null {
  try {
    const decoded = jwt.verify(token, PUBLIC_KEY, {
      algorithms: ['RS256'],
      issuer: undefined, // Allow any issuer for flexibility
      audience: undefined // Allow any audience for flexibility
    }) as JWTPayload;
    
    return decoded;
  } catch (error) {
    console.error('JWT validation failed:', error);
    return null;
  }
}

export function extractTokenFromRequest(req: NextApiRequest): string | null {
  const authHeader = req.headers.authorization;
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }
  
  return authHeader.substring(7); // Remove 'Bearer ' prefix
}

export function isAuthenticated(req: NextApiRequest): JWTPayload | null {
  const token = extractTokenFromRequest(req);
  
  if (!token) {
    return null;
  }
  
  return validateJWT(token);
}