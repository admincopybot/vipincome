/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  env: {
    DATABASE_URL: process.env.DATABASE_URL,
    TRADELIST_API_KEY: process.env.TRADELIST_API_KEY,
    REDIS_URL: process.env.REDIS_URL,
    JWT_PUBLIC_KEY: process.env.JWT_PUBLIC_KEY,
  },
}

module.exports = nextConfig