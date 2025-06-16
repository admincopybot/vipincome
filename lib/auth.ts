import jwt from 'jsonwebtoken';

const OCT_PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEArfvyDNzaxKqXhNvWrEVm
M6FqPDgkCBejKVAZLOUYdhLJAq7m9vw9hqoAYHt7VGp3oEpKYMHrVFEjFd4uWhqf
ZhCL/7Ov+JEK5jDCEg+qOvTTlJr+9nOVIU1y5M6jjdLJ+xqcPbBTfJGz6nLJdvKk
8NcVLOIGpKy3pFB8QqrXOKJWyGJEJjsZPwkN7jLKVcKQW3U2PjgZyq6VfJjU0x8L
OKEWoV7E8jE1w3YbdJWu8V8U1JfR9rJ9qWxLqfQOOgKzEP3I4Yq9nMYfFJ2VZ5K8
dVJ3nNPz7LqJ5OtKq7vSl7K9wOx9xKcVSdQ5ULRyKF2kJ7BqS2gQ8h1xOt5QWmJf
kQYY8NJLK6VoJjhN9E3BF1JzSqvV1cO2eFKQKOdJO7Wt1vKzV5j8nN1J6yGq8KkV
ZJlQ8KvQN0M6O2mQ7hX5KF2QwR8UOjZ7QhK1J5OjMnN8L1M3Q9vN7Y2Q8K6LWrQv
S1ZnP2K9MqJ7ZvQK8wJ6F3VbLUQR9KoY2WqF7gN5sQKXVlEhRyKm6Z2RJO8QWqJx
vJ9J2QdF7kKvL5MqV8R9Y3N1K6JoQzLwRyN3VqP8K1Y7MhJfRwQxNyO2VpL1K4Qr
P8N7V5J2MbR6WqKzLnO1Y9Q3VhN8RyJoL2P4KvM9W7ZxV6QyL1RnOhM5VqJyP8Qw
NhL2VyRjM9QoL5K3VxOhPcF7
-----END PUBLIC KEY-----`;

export interface JWTPayload {
  sub: string;
  iat: number;
  exp: number;
}

export function validateJWT(token: string): JWTPayload | null {
  try {
    const cleanToken = token.replace('Bearer ', '');
    const decoded = jwt.verify(cleanToken, OCT_PUBLIC_KEY, { algorithms: ['RS256'] }) as JWTPayload;
    
    return decoded;
  } catch (error) {
    console.error('JWT validation failed:', error);
    return null;
  }
}

export function isAuthenticated(authHeader: string | undefined): boolean {
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return false;
  }
  
  const payload = validateJWT(authHeader);
  return payload !== null && payload.exp > Math.floor(Date.now() / 1000);
}