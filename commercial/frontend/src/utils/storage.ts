/**
 * LocalStorage 工具函数
 */

export const storage = {
  /**
   * 获取存储的值
   */
  get<T>(key: string): T | null {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch (error) {
      console.error(`读取 localStorage 失败: ${key}`, error);
      return null;
    }
  },

  /**
   * 设置存储的值
   */
  set<T>(key: string, value: T): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error(`写入 localStorage 失败: ${key}`, error);
    }
  },

  /**
   * 删除存储的值
   */
  remove(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error(`删除 localStorage 失败: ${key}`, error);
    }
  },

  /**
   * 清空所有存储
   */
  clear(): void {
    try {
      localStorage.clear();
    } catch (error) {
      console.error('清空 localStorage 失败', error);
    }
  },
};
