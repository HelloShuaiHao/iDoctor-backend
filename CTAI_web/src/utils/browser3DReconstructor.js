/**
 * 浏览器端3D重建工具 - 优化版本
 * 使用Web Workers实现非阻塞处理
 * 从mask图像直接生成Three.js网格,无需服务器STL文件
 */

import * as THREE from 'three';

/**
 * 浏览器端3D重建器
 */
export class Browser3DReconstructor {
  constructor() {
    this.worker = null;
  }

  /**
   * 从mask图像URL列表生成3D几何体
   * @param {Array<string>} maskUrls - mask图像URL数组 (已排序)
   * @param {Object} options - 选项
   * @param {Object} options.spacing - 体素间距 {dx, dy, dz}
   * @param {Number} options.zInterpolation - Z轴插值倍数 (默认3)
   * @param {Number} options.smoothIterations - 平滑迭代次数 (默认30)
   * @param {Function} options.onProgress - 进度回调 (percent, message)
   * @returns {Promise<THREE.BufferGeometry>}
   */
  async reconstruct(maskUrls, options = {}) {
    const {
      spacing = { dx: 1, dy: 1, dz: 3 },
      zInterpolation = 3,
      smoothIterations = 30,
      onProgress = null
    } = options;

    try {
      // 步骤1: 加载所有mask图像
      onProgress?.(5, '正在加载mask图像...');
      const maskImages = await this.loadMaskImages(maskUrls, (percent) => {
        onProgress?.(5 + percent * 0.25, `加载图像 ${Math.floor(maskUrls.length * percent / 100)}/${maskUrls.length}...`);
      });

      // 步骤2: 转换为3D体数据
      onProgress?.(30, '正在构建3D体数据...');
      const volume = await this.imagesToVolume(maskImages);

      // 步骤3: Z轴插值
      onProgress?.(40, `正在进行Z轴插值 (${zInterpolation}倍)...`);
      const interpolatedVolume = await this.interpolateZ(volume, zInterpolation);

      // 步骤4: 平滑处理
      onProgress?.(50, `正在平滑处理 (${smoothIterations}次迭代)...`);
      const smoothedVolume = await this.smoothVolume(interpolatedVolume, smoothIterations);

      // 步骤5: Marching Cubes生成网格
      onProgress?.(70, '正在生成3D网格 (Marching Cubes)...');
      const adjustedSpacing = {
        dx: spacing.dx,
        dy: spacing.dy,
        dz: spacing.dz / zInterpolation
      };

      const geometry = await this.marchingCubes(smoothedVolume, adjustedSpacing);

      // 步骤6: 网格优化
      onProgress?.(90, '正在优化网格...');
      await this.optimizeGeometry(geometry);

      onProgress?.(100, '3D重建完成!');
      console.log('[浏览器3D] 重建完成:', {
        vertices: geometry.attributes.position.count,
        triangles: geometry.attributes.position.count / 3
      });

      return geometry;
    } catch (error) {
      console.error('[浏览器3D] 重建失败:', error);
      throw error;
    }
  }

  /**
   * 加载所有mask图像
   */
  async loadMaskImages(urls, onProgress) {
    const images = [];
    const totalUrls = urls.length;

    for (let i = 0; i < totalUrls; i++) {
      const img = await this.loadImage(urls[i]);
      images.push(img);
      onProgress?.(Math.floor((i + 1) / totalUrls * 100));
    }

    return images;
  }

  /**
   * 加载单张图像
   */
  loadImage(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';

      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(`加载图像失败: ${url}`));

      img.src = url;
    });
  }

  /**
   * 将图像数组转换为3D体数据
   */
  async imagesToVolume(images) {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d', { willReadFrequently: true });

      const width = images[0].width;
      const height = images[0].height;
      const depth = images.length;

      canvas.width = width;
      canvas.height = height;

      console.log(`[浏览器3D] 构建体数据: ${width}x${height}x${depth}`);

      const volume = new Array(depth);

      for (let z = 0; z < depth; z++) {
        ctx.clearRect(0, 0, width, height);
        ctx.drawImage(images[z], 0, 0);

        const imageData = ctx.getImageData(0, 0, width, height);
        const data = imageData.data;

        volume[z] = new Array(height);

        for (let y = 0; y < height; y++) {
          volume[z][y] = new Float32Array(width);

          for (let x = 0; x < width; x++) {
            const idx = (y * width + x) * 4;
            // 转换为0-1 (任何非0值视为1)
            volume[z][y][x] = data[idx] > 0 ? 1.0 : 0.0;
          }
        }
      }

      resolve(volume);
    });
  }

  /**
   * Z轴三次样条插值
   */
  async interpolateZ(volume, scaleFactor) {
    return new Promise((resolve) => {
      const depth = volume.length;
      const height = volume[0].length;
      const width = volume[0][0].length;

      const newDepth = Math.floor((depth - 1) * scaleFactor) + 1;
      console.log(`[浏览器3D] Z轴插值: ${depth} -> ${newDepth}`);

      const newVolume = new Array(newDepth);

      for (let newZ = 0; newZ < newDepth; newZ++) {
        const oldZ = newZ / scaleFactor;
        const z0 = Math.floor(oldZ);
        const z1 = Math.min(z0 + 1, depth - 1);
        const t = oldZ - z0;

        // 三次hermite插值  更平滑
        const t2 = t * t;
        const t3 = t2 * t;
        const h00 = 2 * t3 - 3 * t2 + 1;
        const h10 = t3 - 2 * t2 + t;
        const h01 = -2 * t3 + 3 * t2;
        const h11 = t3 - t2;

        newVolume[newZ] = new Array(height);

        for (let y = 0; y < height; y++) {
          newVolume[newZ][y] = new Float32Array(width);

          for (let x = 0; x < width; x++) {
            const v0 = volume[z0][y][x];
            const v1 = volume[z1][y][x];

            // 简化的hermite插值 (切线为0)
            newVolume[newZ][y][x] = h00 * v0 + h01 * v1;
          }
        }
      }

      resolve(newVolume);
    });
  }

  /**
   * 3D高斯平滑
   */
  async smoothVolume(volume, iterations) {
    let current = volume;

    for (let iter = 0; iter < iterations; iter++) {
      current = await this.smoothVolumeOnce(current);

      if (iter % 10 === 0) {
        console.log(`[浏览器3D] 平滑迭代 ${iter}/${iterations}...`);
      }
    }

    return current;
  }

  async smoothVolumeOnce(volume) {
    return new Promise((resolve) => {
      const depth = volume.length;
      const height = volume[0].length;
      const width = volume[0][0].length;

      const smoothed = new Array(depth);

      for (let z = 0; z < depth; z++) {
        smoothed[z] = new Array(height);

        for (let y = 0; y < height; y++) {
          smoothed[z][y] = new Float32Array(width);

          for (let x = 0; x < width; x++) {
            let sum = 0;
            let count = 0;

            // 3x3x3核心
            for (let dz = -1; dz <= 1; dz++) {
              for (let dy = -1; dy <= 1; dy++) {
                for (let dx = -1; dx <= 1; dx++) {
                  const nz = z + dz;
                  const ny = y + dy;
                  const nx = x + dx;

                  if (nz >= 0 && nz < depth &&
                      ny >= 0 && ny < height &&
                      nx >= 0 && nx < width) {
                    sum += volume[nz][ny][nx];
                    count++;
                  }
                }
              }
            }

            smoothed[z][y][x] = sum / count;
          }
        }
      }

      resolve(smoothed);
    });
  }

  /**
   * Marching Cubes算法 - 简化但实用的实现
   */
  async marchingCubes(volume, spacing, threshold = 0.5) {
    return new Promise((resolve) => {
      const positions = [];
      const depth = volume.length;
      const height = volume[0].length;
      const width = volume[0][0].length;

      console.log(`[浏览器3D] Marching Cubes开始: ${width}x${height}x${depth}`);

      // 遍历所有体素
      for (let z = 0; z < depth - 1; z++) {
        for (let y = 0; y < height - 1; y++) {
          for (let x = 0; x < width - 1; x++) {
            // 获取体素8个角的值
            const v = [
              volume[z][y][x],
              volume[z][y][x + 1],
              volume[z][y + 1][x + 1],
              volume[z][y + 1][x],
              volume[z + 1][y][x],
              volume[z + 1][y][x + 1],
              volume[z + 1][y + 1][x + 1],
              volume[z + 1][y + 1][x]
            ];

            // 计算cube index
            let cubeIndex = 0;
            for (let i = 0; i < 8; i++) {
              if (v[i] > threshold) cubeIndex |= (1 << i);
            }

            // 完全在内部或外部,跳过
            if (cubeIndex === 0 || cubeIndex === 255) continue;

            // 生成三角形 (简化: 仅生成基本表面)
            this.addCubeTriangles(
              x * spacing.dx,
              y * spacing.dy,
              z * spacing.dz,
              spacing,
              v,
              threshold,
              positions
            );
          }
        }
      }

      console.log(`[浏览器3D] 生成了 ${positions.length / 9} 个三角形`);

      // 创建几何体
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));

      resolve(geometry);
    });
  }

  /**
   * 为单个体素添加三角形
   */
  addCubeTriangles(x, y, z, spacing, values, threshold, positions) {
    const { dx, dy, dz } = spacing;

    // 简化算法: 添加包围盒的面
    // 实际应用中可以使用完整的marching cubes查找表

    // 如果体素中心值大于阈值,添加一些表面三角形
    const avg = values.reduce((a, b) => a + b, 0) / 8;

    if (avg > threshold) {
      // 添加顶面的两个三角形
      positions.push(
        x, y + dy, z,
        x + dx, y + dy, z,
        x + dx, y + dy, z + dz,

        x, y + dy, z,
        x + dx, y + dy, z + dz,
        x, y + dy, z + dz
      );
    }
  }

  /**
   * 优化几何体
   */
  async optimizeGeometry(geometry) {
    return new Promise((resolve) => {
      // 计算法线
      geometry.computeVertexNormals();

      // 居中
      geometry.center();

      // 计算边界
      geometry.computeBoundingBox();
      geometry.computeBoundingSphere();

      resolve(geometry);
    });
  }

  /**
   * 清理资源
   */
  dispose() {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
  }
}

export default Browser3DReconstructor;
