import { Redis } from '@upstash/redis'

// Initialize the Redis client from environment variables.
// This will be reused across all serverless functions.
const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});

export default redis; 