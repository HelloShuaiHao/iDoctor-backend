/**
 * Web Worker for 3D reconstruction
 * 在后台线程执行重建,避免阻塞主线程
 */

import ndarray from 'ndarray';
import { surfaceNets } from 'isosurface';

self.addEventListener('message', async (e) => {
  const { type, data } = e.data;

  if (type === 'reconstruct') {
    try {
      await reconstruct(data);
    } catch (error) {
      self.postMessage({
        type: 'error',
        error: error.message
      });
    }
  }
});

async function reconstruct({ imageDataList, spacing, width, height }) {
  // 步骤1: 从主线程接收的图像数据构建3D体数据
  postProgress(30, '正在构建3D体数据...');
  const volume = imagesToNDArray(imageDataList, width, height);
  console.log('[Worker] 体数据shape:', volume.shape);

  // 步骤3: Z轴插值
  postProgress(45, '正在进行Z轴插值(3倍)...');
  const interpolated = interpolateZ(volume, 3);
  console.log('[Worker] 插值后shape:', interpolated.shape);

  // 步骤4: 高斯平滑 (在Worker中执行,不阻塞主线程)
  postProgress(60, '正在平滑处理...');
  const smoothed = gaussianSmooth(interpolated, 30);

  const dataStats = getDataStats(smoothed);
  console.log('[Worker] 平滑后数据统计:', dataStats);

  // 步骤5: Surface Nets生成网格
  postProgress(75, '正在生成3D网格...');
  const thresholdStats = getThresholdStats(smoothed, [0.01, 0.05, 0.1, 0.2]);
  console.log('[Worker] 阈值统计:', thresholdStats);

  const mesh = surfaceNets(smoothed, 0.05);
  console.log('[Worker] 网格生成完成:', {
    vertices: mesh.positions.length,
    triangles: mesh.cells.length
  });

  // 步骤6: 应用spacing并转换为可传输的格式
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
}

// 将主线程传来的图像数据转换为ndarray
function imagesToNDArray(imageDataList, width, height) {
  const depth = imageDataList.length;

  const data = new Float32Array(depth * height * width);
  const volume = ndarray(data, [depth, height, width]);

  for (let z = 0; z < depth; z++) {
    const pixels = imageDataList[z]; // Uint8ClampedArray from ImageData

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = (y * width + x) * 4;
        const value = pixels[idx] / 255.0;
        volume.set(z, y, x, value);
      }
    }
  }

  return volume;
}

// Z轴插值
function interpolateZ(volume, factor) {
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
        const value = h00 * v0 + h01 * v1;
        newVolume.set(nz, y, x, value);
      }
    }
  }

  return newVolume;
}

// 高斯平滑
function gaussianSmooth(volume, iterations) {
  let current = volume;

  for (let i = 0; i < iterations; i++) {
    current = smoothOnce(current);

    if ((i + 1) % 10 === 0) {
      postProgress(60 + (i + 1) / iterations * 15, `平滑迭代 ${i + 1}/${iterations}...`);
    }
  }

  return current;
}

// 单次平滑
function smoothOnce(volume) {
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
  }

  return result;
}

// 获取数据统计
function getDataStats(volume) {
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

// 获取阈值统计
function getThresholdStats(volume, thresholds) {
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

// 将mesh转换为可传输的几何体数据
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

  return {
    vertices: new Float32Array(vertices)
  };
}

// 发送进度更新
function postProgress(percent, message) {
  self.postMessage({
    type: 'progress',
    percent,
    message
  });
}
