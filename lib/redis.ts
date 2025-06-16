import Redis from 'redis';

class RedisCache {
  private client: any;
  private connected: boolean = false;

  constructor() {
    if (process.env.REDIS_URL) {
      this.client = Redis.createClient({
        url: process.env.REDIS_URL
      });
      
      this.client.on('error', (err: any) => {
        console.error('Redis Client Error', err);
        this.connected = false;
      });

      this.client.on('connect', () => {
        this.connected = true;
      });

      this.connect();
    }
  }

  async connect() {
    if (!this.client) return;
    try {
      await this.client.connect();
    } catch (error) {
      console.error('Failed to connect to Redis:', error);
    }
  }

  async get(key: string): Promise<any> {
    if (!this.connected || !this.client) return null;
    
    try {
      const result = await this.client.get(key);
      return result ? JSON.parse(result) : null;
    } catch (error) {
      console.error('Redis GET error:', error);
      return null;
    }
  }

  async set(key: string, value: any, expireInSeconds: number = 180): Promise<boolean> {
    if (!this.connected || !this.client) return false;
    
    try {
      await this.client.setEx(key, expireInSeconds, JSON.stringify(value));
      return true;
    } catch (error) {
      console.error('Redis SET error:', error);
      return false;
    }
  }

  async exists(key: string): Promise<boolean> {
    if (!this.connected || !this.client) return false;
    
    try {
      const result = await this.client.exists(key);
      return result === 1;
    } catch (error) {
      console.error('Redis EXISTS error:', error);
      return false;
    }
  }

  async close() {
    if (this.client && this.connected) {
      await this.client.quit();
    }
  }
}

export default new RedisCache();