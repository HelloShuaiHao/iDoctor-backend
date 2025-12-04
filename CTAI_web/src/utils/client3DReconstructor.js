/**
 * 浏览器端3D重建工具
 * 使用分片处理避免阻塞主线程
 */

import * as THREE from 'three';

export class Client3DReconstructor {
  constructor() {
    this.ndarray = null;
    this.surfaceNets = null;
  }

  /**
   * 从mask图像URL列表生成3D几何体
   * @param {Array<string>} maskImageUrls - mask图像URL数组(已排序)
   * @param {Object} spacing - 体素间距 {dx, dy, dz}
   * @param {Function} onProgress - 进度回调 (percent, message)
   * @returns {Promise<THREE.BufferGeometry>}
   */
  async reconstruct(maskImageUrls, spacing, onProgress) {
    try {
      console.log('[客户端3D] 开始重建(分片处理,避免阻塞)，mask图像数量:', maskImageUrls.length);

      // 动态导入依赖(只导入一次)
      if (!this.ndarray) {
        this.ndarray = (await import('ndarray')).default;
      }
      if (!this.surfaceNets) {
        const isosurfaceModule = await import('isosurface');
        this.surfaceNets = isosurfaceModule.surfaceNets;
      }

      // 步骤1: 加载所有mask图像
      onProgress?.(10, '正在加载mask图像...');
      const images = await this.loadAllImagesForReconstruct(maskImageUrls, onProgress);

      // 步骤2: 转换为ndarray格式的3D体数据
      onProgress?.(30, '正在构建3D体数据...');
      const volume = await this.imagesToNDArray(images);
      console.log('[客户端3D] 体数据shape:', volume.shape);

      // 步骤3: Z轴插值
      onProgress?.(45, '正在进行Z轴插值(3倍)...');
      const interpolated = await this.interpolateZAsync(volume, 3, onProgress);
      console.log('[客户端3D] 插值后shape:', interpolated.shape);

      // 步骤4: 高斯平滑 (分片执行,避免阻塞)
      onProgress?.(60, '正在平滑处理...');
      const smoothed = await this.gaussianSmoothAsync(interpolated, 30, onProgress);

      // 步骤5: Surface Nets生成网格
      onProgress?.(75, '正在生成3D网格(Surface Nets)...');
      const mesh = this.surfaceNets(smoothed, 0.05);
      console.log('[客户端3D] 网格生成完成:', {
        vertices: mesh.positions.length,
        triangles: mesh.cells.length
      });

      // 步骤6: 转换为Three.js几何体
      onProgress?.(90, '正在构建Three.js几何体...');
      const adjustedSpacing = {
        dx: spacing.dx,
        dy: spacing.dy,
        dz: spacing.dz / 3
      };
      const geometry = this.meshToThreeGeometry(mesh, adjustedSpacing);

      onProgress?.(100, '3D重建完成!');
      return geometry;

    } catch (error) {
      console.error('[客户端3D] 重建失败:', error);
      throw error;
    }
  }

  /**
   * 加载所有图像(用于重建)
   */
  async loadAllImagesForReconstruct(urls, onProgress) {
    const images = [];
    const total = urls.length;

    for (let i = 0; i < total; i++) {
      const img = await this.loadImage(urls[i]);
      images.push(img);
      const percent = 10 + (i + 1) / total * 20;
      onProgress?.(percent, `加载图像 ${i + 1}/${total}...`);
    }

    return images;
  }

  /**
   * 将图像数组转换为ndarray
   */
  async imagesToNDArray(images) {
    const width = images[0].width;
    const height = images[0].height;
    const depth = images.length;

    const data = new Float32Array(depth * height * width);
    const volume = this.ndarray(data, [depth, height, width]);

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });

    for (let z = 0; z < depth; z++) {
      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(images[z], 0, 0);

      const imageData = ctx.getImageData(0, 0, width, height);
      const pixels = imageData.data;

      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const idx = (y * width + x) * 4;
          const value = pixels[idx] / 255.0;
          volume.set(z, y, x, value);
        }
      }

      // 每处理一张图像就让出控制权
      if (z % 5 === 0) {
        await this.yield();
      }
    }

    return volume;
  }

  /**
   * Z轴插值 (分片执行)
   */
  async interpolateZAsync(volume, factor, onProgress) {
    const [d, h, w] = volume.shape;
    const newD = Math.floor((d - 1) * factor) + 1;

    const newData = new Float32Array(newD * h * w);
    const newVolume = this.ndarray(newData, [newD, h, w]);

    for (let nz = 0; nz < newD; nz++) {
      const oz = nz / factor;
      const z0 = Math.floor(oz);
      const z1 = Math.min(z0 + 1, d - 1);
      const t = oz - z0;

      const t2 = t * t;
      const t3 = t2 * t;
      const h00 = 2 * t3 - 3 * t2 + 1;
      const h01 = -2 * t3 + 3 * t2;

      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const v0 = volume.get(z0, y, x);
          const v1 = volume.get(z1, y, x);
          newVolume.set(nz, y, x, h00 * v0 + h01 * v1);
        }
      }

      // 每10层让出控制权
      if (nz % 10 === 0) {
        await this.yield();
      }
    }

    return newVolume;
  }

  /**
   * 高斯平滑 (分片执行,避免阻塞)
   */
  async gaussianSmoothAsync(volume, iterations, onProgress) {
    let current = volume;

    for (let i = 0; i < iterations; i++) {
      current = await this.smoothOnceAsync(current);

      if ((i + 1) % 5 === 0) {
        const percent = 60 + (i + 1) / iterations * 15;
        onProgress?.(percent, `平滑迭代 ${i + 1}/${iterations}...`);
      }
    }

    return current;
  }

  /**
   * 单次平滑 (分片执行)
   */
  async smoothOnceAsync(volume) {
    const [d, h, w] = volume.shape;
    const newData = new Float32Array(d * h * w);
    const result = this.ndarray(newData, [d, h, w]);

    for (let z = 0; z < d; z++) {
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          let sum = 0;
          let count = 0;

          for (let dz = -1; dz <= 1; dz++) {
            for (let dy = -1; dy <= 1; dy++) {
              for (let dx = -1; dx <= 1; dx++) {
                const nz = z + dz;
                const ny = y + dy;
                const nx = x + dx;

                if (nz >= 0 && nz < d && ny >= 0 && ny < h && nx >= 0 && nx < w) {
                  sum += volume.get(nz, ny, nx);
                  count++;
                }
              }
            }
          }

          result.set(z, y, x, sum / count);
        }
      }

      // 每处理一层就让出控制权
      if (z % 5 === 0) {
        await this.yield();
      }
    }

    return result;
  }

  /**
   * 将Surface Nets mesh转换为Three.js BufferGeometry
   */
  meshToThreeGeometry(mesh, spacing) {
    const { positions, cells } = mesh;

    const vertices = new Float32Array(cells.length * 9);

    for (let i = 0; i < cells.length; i++) {
      const cell = cells[i];

      for (let j = 0; j < 3; j++) {
        const vtx = positions[cell[j]];
        const idx = i * 9 + j * 3;

        vertices[idx] = vtx[0] * spacing.dx;
        vertices[idx + 1] = vtx[1] * spacing.dy;
        vertices[idx + 2] = vtx[2] * spacing.dz;
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

    geometry.computeVertexNormals();
    geometry.center();
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();

    console.log('[客户端3D] Three.js几何体创建完成:', {
      vertices: geometry.attributes.position.count,
      triangles: geometry.attributes.position.count / 3
    });

    return geometry;
  }

  /**
   * 让出控制权给浏览器渲染线程
   */
  yield() {
    return new Promise(resolve => setTimeout(resolve, 0));
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
}
