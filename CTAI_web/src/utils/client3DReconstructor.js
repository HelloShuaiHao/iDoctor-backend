/**
 * 浏览器端3D重建工具
 * 使用Web Worker在后台线程执行重建,避免阻塞主线程
 */

import * as THREE from 'three';

export class Client3DReconstructor {
  constructor() {
    this.worker = null;
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

      // 动态导入依赖
      const ndarray = (await import('ndarray')).default;
      const { surfaceNets } = await import('isosurface');

      // 步骤1: 加载所有mask图像
      onProgress?.(10, '正在加载mask图像...');
      const images = await this.loadAllImagesForReconstruct(maskImageUrls, onProgress);

      // 步骤2: 转换为ndarray格式的3D体数据
      onProgress?.(30, '正在构建3D体数据...');
      const volume = await this.imagesToNDArray(images, ndarray);
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
      const mesh = surfaceNets(smoothed, 0.05);
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
  async imagesToNDArray(images, ndarray) {
    const width = images[0].width;
    const height = images[0].height;
    const depth = images.length;

    const data = new Float32Array(depth * height * width);
    const volume = ndarray(data, [depth, height, width]);

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
    const ndarray = (await import('ndarray')).default;
    const [d, h, w] = volume.shape;
    const newD = Math.floor((d - 1) * factor) + 1;

    const newData = new Float32Array(newD * h * w);
    const newVolume = ndarray(newData, [newD, h, w]);

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
    const ndarray = (await import('ndarray')).default;
    const [d, h, w] = volume.shape;
    const newData = new Float32Array(d * h * w);
    const result = ndarray(newData, [d, h, w]);

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

  /**
   * 创建内联 Worker (使用 Blob URL)
   */
  createWorker() {
    // Worker 代码作为字符串
    const workerCode = `
      // 动态导入 ndarray 和 isosurface (需要在构建时包含)
      importScripts('https://unpkg.com/ndarray@1.0.19/ndarray.js');
      importScripts('https://unpkg.com/isosurface@1.0.0/isosurface.js');

      self.addEventListener('message', async (e) => {
        const { type, data } = e.data;

        if (type === 'reconstruct') {
          try {
            await reconstruct(data);
          } catch (error) {
            self.postMessage({
              type: 'error',
              error: error.message + ' | Stack: ' + error.stack
            });
          }
        }
      });

      async function reconstruct({ imageDataList, spacing, width, height }) {
        try {
          console.log('[Worker] 接收到的数据:', {
            imageDataListLength: imageDataList ? imageDataList.length : 'undefined',
            width,
            height
          });

          if (!imageDataList || !imageDataList.length) {
            throw new Error('imageDataList is undefined or empty');
          }

          // 构建3D体数据
          postProgress(30, '正在构建3D体数据...');
          const volume = imagesToNDArray(imageDataList, width, height);

          // Z轴插值
          postProgress(45, '正在进行Z轴插值(3倍)...');
          const interpolated = interpolateZ(volume, 3);

          // 高斯平滑
          postProgress(60, '正在平滑处理...');
          const smoothed = gaussianSmooth(interpolated, 30);

          // Surface Nets生成网格
          postProgress(75, '正在生成3D网格...');
          const mesh = isosurface.surfaceNets(smoothed.data, smoothed.shape, 0.05);

          console.log('[Worker] 网格生成完成:', {
            vertices: mesh.positions.length,
            triangles: mesh.cells.length
          });

          // 转换为可传输的格式
          postProgress(90, '正在构建几何体...');
          const adjustedSpacing = {
            dx: spacing.dx,
            dy: spacing.dy,
            dz: spacing.dz / 3
          };

          const geometry = meshToGeometryData(mesh, adjustedSpacing);

          // 返回结果
          postProgress(100, '3D重建完成!');
          self.postMessage({
            type: 'complete',
            geometry: geometry
          });
        } catch (error) {
          throw new Error('Reconstruct failed: ' + error.message);
        }
      }

      function imagesToNDArray(imageDataList, width, height) {
        const depth = imageDataList.length;
        const data = new Float32Array(depth * height * width);

        for (let z = 0; z < depth; z++) {
          const pixels = imageDataList[z];
          for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
              const idx = (y * width + x) * 4;
              const value = pixels[idx] / 255.0;
              data[z * height * width + y * width + x] = value;
            }
          }
        }

        return { data, shape: [depth, height, width] };
      }

      function interpolateZ(volume, factor) {
        const [d, h, w] = volume.shape;
        const newD = Math.floor((d - 1) * factor) + 1;
        const newData = new Float32Array(newD * h * w);

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
              const v0 = volume.data[z0 * h * w + y * w + x];
              const v1 = volume.data[z1 * h * w + y * w + x];
              newData[nz * h * w + y * w + x] = h00 * v0 + h01 * v1;
            }
          }
        }

        return { data: newData, shape: [newD, h, w] };
      }

      function gaussianSmooth(volume, iterations) {
        let current = volume;
        for (let i = 0; i < iterations; i++) {
          current = smoothOnce(current);
          if ((i + 1) % 10 === 0) {
            postProgress(60 + (i + 1) / iterations * 15, \`平滑迭代 \${i + 1}/\${iterations}...\`);
          }
        }
        return current;
      }

      function smoothOnce(volume) {
        const [d, h, w] = volume.shape;
        const newData = new Float32Array(d * h * w);

        for (let z = 0; z < d; z++) {
          for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
              let sum = 0, count = 0;
              for (let dz = -1; dz <= 1; dz++) {
                for (let dy = -1; dy <= 1; dy++) {
                  for (let dx = -1; dx <= 1; dx++) {
                    const nz = z + dz, ny = y + dy, nx = x + dx;
                    if (nz >= 0 && nz < d && ny >= 0 && ny < h && nx >= 0 && nx < w) {
                      sum += volume.data[nz * h * w + ny * w + nx];
                      count++;
                    }
                  }
                }
              }
              newData[z * h * w + y * w + x] = sum / count;
            }
          }
        }

        return { data: newData, shape: volume.shape };
      }

      function meshToGeometryData(mesh, spacing) {
        const { positions, cells } = mesh;
        const vertices = [];

        for (let i = 0; i < cells.length; i++) {
          const cell = cells[i];
          for (let j = 0; j < 3; j++) {
            const vtx = positions[cell[j]];
            vertices.push(
              vtx[0] * spacing.dx,
              vtx[1] * spacing.dy,
              vtx[2] * spacing.dz
            );
          }
        }

        return { vertices: new Float32Array(vertices) };
      }

      function postProgress(percent, message) {
        self.postMessage({ type: 'progress', percent, message });
      }
    `;

    const blob = new Blob([workerCode], { type: 'application/javascript' });
    const workerUrl = URL.createObjectURL(blob);
    return new Worker(workerUrl);
  }

  /**
   * 从 Worker 返回的数据创建 Three.js 几何体
   */
  createThreeGeometry(geometryData) {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(geometryData.vertices, 3));

    // 计算法线
    geometry.computeVertexNormals();

    // 居中
    geometry.center();

    // 计算边界
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();

    console.log('[客户端3D] Three.js几何体创建完成:', {
      vertices: geometry.attributes.position.count,
      triangles: geometry.attributes.position.count / 3
    });

    return geometry;
  }

  // ============ 以下是旧的同步实现,保留作为fallback ============

  /**
   * 同步版本重建(fallback,不推荐使用,会阻塞主线程)
   */
  async reconstructSync(maskImageUrls, spacing, onProgress) {
    try {
      console.log('[客户端3D] 开始重建(同步模式)，mask图像数量:', maskImageUrls.length);

      const ndarray = (await import('ndarray')).default;
      const { surfaceNets } = await import('isosurface');

      // 步骤1: 加载所有mask图像
      onProgress?.(10, '正在加载mask图像...');
      const images = await this.loadImages(maskImageUrls, (loaded, total) => {
        const percent = 10 + (loaded / total) * 20;
        onProgress?.(percent, `加载图像 ${loaded}/${total}...`);
      });

      // 步骤2: 转换为ndarray格式的3D体数据
      onProgress?.(30, '正在构建3D体数据...');
      const volume = await this.imagesToNDArray(images);
      console.log('[客户端3D] 体数据shape:', volume.shape);

      // 步骤3: Z轴插值(提高层间连续性)
      onProgress?.(45, '正在进行Z轴插值(3倍)...');
      const interpolated = this.interpolateZ(volume, 3);
      console.log('[客户端3D] 插值后shape:', interpolated.shape);
      console.log('[客户端3D] 插值后数据统计:', this.getDataStats(interpolated));

      // 步骤4: 高斯平滑 (增加迭代次数以连接稀疏区域)
      onProgress?.(60, '正在平滑处理...');
      const smoothed = this.gaussianSmooth(interpolated, 30);  // 增加到30次以形成连续表面

      // 调试: 检查数据范围
      const dataStats = this.getDataStats(smoothed);
      console.log('[客户端3D] 平滑后数据统计:', dataStats);

      // 步骤5: Surface Nets生成网格 (降低阈值以包含更多边缘区域)
      onProgress?.(75, '正在生成3D网格(Surface Nets)...');

      // 调试: 检查有多少值超过不同的阈值
      const thresholdStats = this.getThresholdStats(smoothed, [0.01, 0.05, 0.1, 0.2]);
      console.log('[客户端3D] 阈值统计:', thresholdStats);

      const mesh = surfaceNets(smoothed, 0.05);  // 降低到0.05以捕获更多平滑后的边缘
      console.log('[客户端3D] 网格生成完成:', {
        vertices: mesh.positions.length,
        triangles: mesh.cells.length
      });

      // 步骤6: 转换为Three.js几何体
      onProgress?.(90, '正在构建Three.js几何体...');
      const adjustedSpacing = {
        dx: spacing.dx,
        dy: spacing.dy,
        dz: spacing.dz / 3  // 由于做了3倍插值
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
   * 加载所有图像
   */
  async loadImages(urls, onProgress) {
    const images = [];
    const total = urls.length;

    for (let i = 0; i < total; i++) {
      const img = await this.loadImage(urls[i]);
      images.push(img);
      onProgress?.(i + 1, total);
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
   * 将图像数组转换为ndarray格式的3D体数据
   */
  async imagesToNDArray(images) {
    const width = images[0].width;
    const height = images[0].height;
    const depth = images.length;

    console.log(`[客户端3D] 图像尺寸: ${width}x${height}, 深度: ${depth}`);

    // 创建3D ndarray
    const data = new Float32Array(depth * height * width);
    const volume = ndarray(data, [depth, height, width]);

    // 创建canvas用于提取像素数据
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
          // 归一化到0-1范围,保留灰度信息而不是二值化
          const value = pixels[idx] / 255.0;
          volume.set(z, y, x, value);
        }
      }
    }

    return volume;
  }

  /**
   * Z轴三次hermite插值
   */
  interpolateZ(volume, factor) {
    const [d, h, w] = volume.shape;
    const newD = Math.floor((d - 1) * factor) + 1;

    console.log(`[客户端3D] Z轴插值: ${d} -> ${newD} (${factor}倍)`);

    const newData = new Float32Array(newD * h * w);
    const newVolume = ndarray(newData, [newD, h, w]);

    for (let nz = 0; nz < newD; nz++) {
      const oz = nz / factor;
      const z0 = Math.floor(oz);
      const z1 = Math.min(z0 + 1, d - 1);
      const t = oz - z0;

      // 三次hermite插值系数
      const t2 = t * t;
      const t3 = t2 * t;
      const h00 = 2 * t3 - 3 * t2 + 1;
      const h01 = -2 * t3 + 3 * t2;

      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const v0 = volume.get(z0, y, x);
          const v1 = volume.get(z1, y, x);

          // Hermite插值(简化版，切线为0)
          const value = h00 * v0 + h01 * v1;
          newVolume.set(nz, y, x, value);
        }
      }
    }

    return newVolume;
  }

  /**
   * 3D高斯平滑
   */
  gaussianSmooth(volume, iterations) {
    console.log(`[客户端3D] 开始平滑处理 (${iterations}次迭代)...`);

    let current = volume;

    for (let i = 0; i < iterations; i++) {
      current = this.smoothOnce(current);

      if ((i + 1) % 10 === 0) {
        console.log(`[客户端3D] 平滑迭代 ${i + 1}/${iterations}`);
      }
    }

    return current;
  }

  /**
   * 单次平滑(3x3x3平均核)
   */
  smoothOnce(volume) {
    const [d, h, w] = volume.shape;
    const newData = new Float32Array(d * h * w);
    const result = ndarray(newData, [d, h, w]);

    for (let z = 0; z < d; z++) {
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          let sum = 0;
          let count = 0;

          // 3x3x3邻域
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
    }

    return result;
  }

  /**
   * 获取数据统计信息
   */
  getDataStats(volume) {
    const [d, h, w] = volume.shape;
    let min = Infinity, max = -Infinity, sum = 0, count = 0;
    let nonZeroCount = 0;

    for (let z = 0; z < d; z++) {
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const val = volume.get(z, y, x);
          if (val < min) min = val;
          if (val > max) max = val;
          sum += val;
          count++;
          if (val > 0) nonZeroCount++;
        }
      }
    }

    return {
      min,
      max,
      mean: sum / count,
      nonZeroCount,
      nonZeroPercent: (nonZeroCount / count * 100).toFixed(2) + '%'
    };
  }

  /**
   * 获取不同阈值下的统计信息
   */
  getThresholdStats(volume, thresholds) {
    const [d, h, w] = volume.shape;
    const stats = {};

    thresholds.forEach(threshold => {
      let count = 0;
      for (let z = 0; z < d; z++) {
        for (let y = 0; y < h; y++) {
          for (let x = 0; x < w; x++) {
            if (volume.get(z, y, x) >= threshold) {
              count++;
            }
          }
        }
      }
      const totalVoxels = d * h * w;
      stats[`>=${threshold}`] = {
        count,
        percent: (count / totalVoxels * 100).toFixed(3) + '%'
      };
    });

    return stats;
  }

  /**
   * 将Surface Nets mesh转换为Three.js BufferGeometry
   */
  meshToThreeGeometry(mesh, spacing) {
    const { positions, cells } = mesh;

    // 创建顶点数组
    const vertices = new Float32Array(cells.length * 9);

    for (let i = 0; i < cells.length; i++) {
      const cell = cells[i];

      for (let j = 0; j < 3; j++) {
        const vtx = positions[cell[j]];
        const idx = i * 9 + j * 3;

        // 应用spacing
        vertices[idx] = vtx[0] * spacing.dx;
        vertices[idx + 1] = vtx[1] * spacing.dy;
        vertices[idx + 2] = vtx[2] * spacing.dz;
      }
    }

    // 创建Three.js几何体
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

    // 计算法线
    geometry.computeVertexNormals();

    // 居中
    geometry.center();

    // 计算边界
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();

    console.log('[客户端3D] Three.js几何体创建完成:', {
      vertices: geometry.attributes.position.count,
      triangles: geometry.attributes.position.count / 3
    });

    return geometry;
  }
}

export default Client3DReconstructor;
