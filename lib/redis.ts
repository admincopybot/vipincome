import { Redis } from '@upstash/redis';

let redis: Redis | null = null;

export function getRedisClient(): Redis {
  if (!redis) {
    redis = new Redis({
      url: process.env.UPSTASH_REDIS_REST_URL!,
      token: process.env.UPSTASH_REDIS_REST_TOKEN!,
    });
  }
  return redis;
}

export async function getCachedData<T>(key: string): Promise<T | null> {
  try {
    const client = getRedisClient();
    const data = await client.get(key);
    return data as T | null;
  } catch (error) {
    console.error(`Redis GET error for key ${key}:`, error);
    return null;
  }
}

export async function setCachedData<T>(
  key: string, 
  data: T, 
  expirationSeconds: number = 180
): Promise<void> {
  try {
    const client = getRedisClient();
    await client.setex(key, expirationSeconds, JSON.stringify(data));
  } catch (error) {
    console.error(`Redis SET error for key ${key}:`, error);
  }
}

export async function deleteCachedData(key: string): Promise<void> {
  try {
    const client = getRedisClient();
    await client.del(key);
  } catch (error) {
    console.error(`Redis DELETE error for key ${key}:`, error);
  }
}