/**
 * SAM2 Service for Demo
 * Handles communication with SAM2 segmentation API
 */

import axios from 'axios';
import type { ClickPoint, SegmentationResult } from '@/types/demo';

// 创建 SAM2 专用的 API 实例
// 通过 Nginx 统一网关访问，避免 CORS 问题
// 生产环境下使用空字符串（相对路径），开发环境使用 localhost
const sam2API = axios.create({
  baseURL: import.meta.env.VITE_NGINX_BASE_URL !== undefined
    ? import.meta.env.VITE_NGINX_BASE_URL
    : 'http://localhost:3000',
  timeout: 30000,
});

export class DemoSAM2Service {
  /**
   * Perform segmentation with click points
   */
  async segmentWithClicks(
    imageFile: Blob,
    clickPoints: ClickPoint[]
  ): Promise<SegmentationResult> {
    // Create FormData payload
    // 参数名需要匹配 SAM2 服务定义（sam2_service.py:246-252）
    const formData = new FormData();
    formData.append('file', imageFile); // 必需
    formData.append('image_type', 'auto'); // 可选，默认 'auto'
    formData.append('return_format', 'base64'); // 可选，默认 'base64'
    formData.append('click_points', JSON.stringify(clickPoints)); // 可选

    try {
      const response = await sam2API.post('/api/segmentation/segment', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 120 seconds
      });

      // Validate response
      const result = response.data;
      if (!result.mask_data || typeof result.confidence_score !== 'number') {
        throw new Error('Invalid response format from SAM2 service');
      }

      return result as SegmentationResult;
    } catch (error: any) {
      // Handle specific error cases
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;

        if (status === 402) {
          throw new Error('配额已用尽，请升级订阅计划');
        } else if (status === 503) {
          throw new Error('AI分割服务暂时不可用，请稍后重试');
        } else if (status === 400) {
          throw new Error(data.message || '图片格式不受支持');
        }
      } else if (error.code === 'ECONNABORTED') {
        throw new Error('请求超时，请尝试使用较小的图片');
      } else if (error.message === 'Network Error') {
        throw new Error('无法连接到AI服务，请检查网络连接');
      }

      throw new Error(error.message || 'AI分割失败');
    }
  }

  /**
   * Check if SAM2 service is available
   */
  async checkServiceHealth(): Promise<boolean> {
    try {
      // Check SAM2 health via Nginx proxy
      await sam2API.get('/api/segmentation/health', { timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }
}

export const demoSAM2Service = new DemoSAM2Service();
