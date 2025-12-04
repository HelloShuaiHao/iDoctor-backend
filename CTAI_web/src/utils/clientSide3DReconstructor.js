/**
 * 浏览器端3D重建工具
 * 从mask图像堆栈直接生成Three.js几何体,无需服务器生成STL文件
 */

import * as THREE from 'three';

/**
 * 简化的Marching Cubes实现
 * 将3D体素数据转换为三角网格
 */
class MarchingCubes {
  constructor() {
    // Marching Cubes查找表 (简化版,仅支持基础情况)
    this.edgeTable = this._generateEdgeTable();
    this.triTable = this._generateTriTable();
  }

  /**
   * 从3D mask数组生成网格
   * @param {Array} volume - 3D数组 [z][y][x]
   * @param {Object} spacing - 体素间距 {dx, dy, dz}
   * @param {Number} threshold - 阈值 (默认0.5)
   * @returns {THREE.BufferGeometry}
   */
  march(volume, spacing = { dx: 1, dy: 1, dz: 1 }, threshold = 0.5) {
    const vertices = [];
    const faces = [];

    const depth = volume.length;
    const height = volume[0].length;
    const width = volume[0][0].length;

    console.log(`[客户端3D] 开始Marching Cubes: ${width}x${height}x${depth}`);

    // 遍历所有体素
    for (let z = 0; z < depth - 1; z++) {
      if (z % 10 === 0) {
        console.log(`[客户端3D] 处理第 ${z}/${depth} 层...`);
      }

      for (let y = 0; y < height - 1; y++) {
        for (let x = 0; x < width - 1; x++) {
          // 获取立方体8个顶点的值
          const cube = [
            volume[z][y][x],
            volume[z][y][x + 1],
            volume[z][y + 1][x + 1],
            volume[z][y + 1][x],
            volume[z + 1][y][x],
            volume[z + 1][y][x + 1],
            volume[z + 1][y + 1][x + 1],
            volume[z + 1][y + 1][x]
          ];

          // 计算立方体配置索引
          let cubeIndex = 0;
          for (let i = 0; i < 8; i++) {
            if (cube[i] > threshold) {
              cubeIndex |= (1 << i);
            }
          }

          // 如果完全在内部或外部,跳过
          if (cubeIndex === 0 || cubeIndex === 255) {
            continue;
          }

          // 生成三角形 (简化算法)
          this._generateTriangles(
            x, y, z,
            cube, cubeIndex,
            spacing, threshold,
            vertices, faces
          );
        }
      }
    }

    console.log(`[客户端3D] Marching Cubes完成: ${vertices.length}个顶点, ${faces.length}个面`);

    // 转换为Three.js几何体
    return this._createGeometry(vertices, faces);
  }

  _generateTriangles(x, y, z, cube, cubeIndex, spacing, threshold, vertices, faces) {
    // 简化版: 仅处理基础情况
    // 实际的Marching Cubes需要完整的查找表

    // 立方体顶点位置
    const corners = [
      [x, y, z],
      [x + 1, y, z],
      [x + 1, y + 1, z],
      [x, y + 1, z],
      [x, y, z + 1],
      [x + 1, y, z + 1],
      [x + 1, y + 1, z + 1],
      [x, y + 1, z + 1]
    ];

    // 应用spacing
    const scaledCorners = corners.map(c => [
      c[0] * spacing.dx,
      c[1] * spacing.dy,
      c[2] * spacing.dz
    ]);

    // 简单三角化: 如果中心点值大于阈值,生成三角形
    const centerValue = cube.reduce((a, b) => a + b, 0) / 8;

    if (centerValue > threshold) {
      // 生成一个简单的四面体或立方体的一部分
      const baseIdx = vertices.length;

      // 添加部分顶点
      vertices.push(...scaledCorners.slice(0, 4));

      // 添加两个三角形组成一个面
      faces.push([baseIdx, baseIdx + 1, baseIdx + 2]);
      faces.push([baseIdx, baseIdx + 2, baseIdx + 3]);
    }
  }

  _createGeometry(vertices, faces) {
    const geometry = new THREE.BufferGeometry();

    // 转换为flat array
    const positions = new Float32Array(faces.length * 9);
    let idx = 0;

    for (const face of faces) {
      for (const vIdx of face) {
        const v = vertices[vIdx];
        positions[idx++] = v[0];
        positions[idx++] = v[1];
        positions[idx++] = v[2];
      }
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.computeVertexNormals();

    return geometry;
  }

  _generateEdgeTable() {
    // Edge table placeholder
    return new Array(256).fill(0);
  }

  _generateTriTable() {
    // Triangle table placeholder
    return new Array(256).fill([]).map(() => new Array(16).fill(-1));
  }
}

/**
 * 主要的客户端3D重建器
 */
export class ClientSide3DReconstructor {
  constructor() {
    this.marchingCubes = new MarchingCubes();
  }

  /**
   * 从mask图像URL列表生成3D几何体
   * @param {Array<string>} maskUrls - mask图像URL数组
   * @param {Object} spacing - 体素间距
   * @param {Function} progressCallback - 进度回调 (percent, message)
   * @returns {Promise<THREE.BufferGeometry>}
   */
  async reconstructFrom Images(maskUrls, spacing = { dx: 1, dy: 1, dz: 3 }, progressCallback = null) {
    try {
      // 1. 加载所有mask图像
      progressCallback?.(10, '正在加载mask图像...');
      const maskImages = await this.loadMaskImages(maskUrls, progressCallback);

      // 2. 转换为3D体数据
      progressCallback?.(40, '正在构建3D体数据...');
      const volume = this.imagesToVolume(maskImages);

      // 3. 可选: Z轴插值以提高层间连续性
      progressCallback?.(50, '正在进行Z轴插值...');
      const interpolatedVolume = this.interpolateZ(volume, 3); // 3倍插值

      // 4. 平滑处理
      progressCallback?.(60, '正在平滑处理...');
      const smoothedVolume = this.smoothVolume(interpolatedVolume, 2);

      // 5. Marching Cubes生成网格
      progressCallback?.(70, '正在生成3D网格...');
      const adjustedSpacing = {
        dx: spacing.dx,
        dy: spacing.dy,
        dz: spacing.dz / 3 // 由于做了3倍插值
      };
      const geometry = this.marchingCubes.march(smoothedVolume, adjustedSpacing, 0.5);

      // 6. 后处理
      progressCallback?.(90, '正在优化网格...');
      this.optimizeGeometry(geometry);

      progressCallback?.(100, '完成!');
      return geometry;
    } catch (error) {
      console.error('[客户端3D] 重建失败:', error);
      throw error;
    }
  }

  /**
   * 加载所有mask图像
   */
  async loadMaskImages(urls, progressCallback) {
    const images = [];
    const totalUrls = urls.length;

    for (let i = 0; i < totalUrls; i++) {
      const url = urls[i];
      const img = await this.loadImage(url);
      images.push(img);

      const percent = 10 + Math.floor((i / totalUrls) * 30);
      progressCallback?.(percent, `加载图像 ${i + 1}/${totalUrls}...`);
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
  imagesToVolume(images) {
    if (images.length === 0) {
      throw new Error('没有图像数据');
    }

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    const width = images[0].width;
    const height = images[0].height;
    const depth = images.length;

    canvas.width = width;
    canvas.height = height;

    const volume = new Array(depth);

    for (let z = 0; z < depth; z++) {
      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(images[z], 0, 0);

      const imageData = ctx.getImageData(0, 0, width, height);
      const data = imageData.data;

      volume[z] = new Array(height);

      for (let y = 0; y < height; y++) {
        volume[z][y] = new Array(width);

        for (let x = 0; x < width; x++) {
          const idx = (y * width + x) * 4;
          // 将灰度值转换为0-1
          const value = data[idx] / 255.0;
          volume[z][y][x] = value;
        }
      }
    }

    return volume;
  }

  /**
   * Z轴插值
   */
  interpolateZ(volume, scaleFactor) {
    const depth = volume.length;
    const height = volume[0].length;
    const width = volume[0][0].length;

    const newDepth = depth * scaleFactor;
    const newVolume = new Array(newDepth);

    for (let newZ = 0; newZ < newDepth; newZ++) {
      const oldZ = newZ / scaleFactor;
      const z0 = Math.floor(oldZ);
      const z1 = Math.min(z0 + 1, depth - 1);
      const t = oldZ - z0;

      newVolume[newZ] = new Array(height);

      for (let y = 0; y < height; y++) {
        newVolume[newZ][y] = new Array(width);

        for (let x = 0; x < width; x++) {
          // 线性插值
          const v0 = volume[z0][y][x];
          const v1 = volume[z1][y][x];
          newVolume[newZ][y][x] = v0 * (1 - t) + v1 * t;
        }
      }
    }

    return newVolume;
  }

  /**
   * 3D平滑处理 (简单平均滤波)
   */
  smoothVolume(volume, iterations = 1) {
    let current = volume;

    for (let iter = 0; iter < iterations; iter++) {
      current = this.smoothVolumeOnce(current);
    }

    return current;
  }

  smoothVolumeOnce(volume) {
    const depth = volume.length;
    const height = volume[0].length;
    const width = volume[0][0].length;

    const smoothed = new Array(depth);

    for (let z = 0; z < depth; z++) {
      smoothed[z] = new Array(height);

      for (let y = 0; y < height; y++) {
        smoothed[z][y] = new Array(width);

        for (let x = 0; x < width; x++) {
          // 3x3x3 平均
          let sum = 0;
          let count = 0;

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

    return smoothed;
  }

  /**
   * 优化几何体
   */
  optimizeGeometry(geometry) {
    // 居中
    geometry.center();

    // 计算法线
    geometry.computeVertexNormals();

    // 计算边界框
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();

    return geometry;
  }
}

export default ClientSide3DReconstructor;
