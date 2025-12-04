# 浏览器端3D重建实施指南

## 概述

将3D重建从服务器端(生成2.5G STL文件)迁移到浏览器端,显著减少网络传输,提升用户体验。

## 问题分析

**当前问题:**
- 服务器端生成2.5G的STL/OBJ文件
- 网络传输慢,用户等待时间长
- 服务器存储压力大

**解决方案:**
- 仅传输mask图像(通常每张几KB,总共几MB)
- 浏览器端直接进行Marching Cubes 3D重建
- 使用Web Workers避免阻塞UI

## 实施步骤

### 步骤1: 安装必要的npm包

```bash
cd /Users/mbp/Desktop/Work/Life/IDoctor/iDoctor-backend(云服务)/CTAI_web

# 安装3D重建所需的库
npm install --save isosurface ndarray ndarray-ops ndarray-fill ndarray-scratch

# 可选: 如果需要网格简化以进一步优化性能
npm install --save simplify-3d-mesh
```

### 步骤2: 创建浏览器端3D重建工具

创建文件: `CTAI_web/src/utils/client3DReconstructor.js`

```javascript
import * as THREE from 'three';
import ndarray from 'ndarray';
import ops from 'ndarray-ops';
import { surfaceNets } from 'isosurface'; // 或使用 marchingCubes

export class Client3DReconstructor {
  /**
   * 从mask图像生成3D几何体
   * @param {Array<string>} maskImageUrls - mask图像URL数组
   * @param {Object} spacing - 体素间距 {dx, dy, dz}
   * @param {Function} onProgress - 进度回调
   */
  async reconstruct(maskImageUrls, spacing, onProgress) {
    try {
      // 1. 加载所有mask图像
      onProgress?.(10, '加载mask图像...');
      const images = await this.loadImages(maskImageUrls);

      // 2. 转换为ndarray格式的3D体数据
      onProgress?.(30, '构建3D体数据...');
      const volume = await this.imagesToNDArray(images);

      // 3. Z轴插值(可选,提高层间连续性)
      onProgress?.(45, 'Z轴插值...');
      const interpolated = this.interpolateZ(volume, 3); // 3倍插值

      // 4. 平滑处理
      onProgress?.(60, '平滑处理...');
      const smoothed = this.gaussianSmooth(interpolated);

      // 5. Marching Cubes / Surface Nets
      onProgress?.(75, '生成3D网格...');
      const mesh = surfaceNets(smoothed, 0.5);

      // 6. 转换为Three.js几何体
      onProgress?.(90, '构建Three.js几何体...');
      const geometry = this.meshToThreeGeometry(mesh, spacing);

      onProgress?.(100, '完成!');
      return geometry;

    } catch (error) {
      console.error('[客户端3D] 重建失败:', error);
      throw error;
    }
  }

  async loadImages(urls) {
    return Promise.all(urls.map(url => this.loadImage(url)));
  }

  loadImage(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = url;
    });
  }

  async imagesToNDArray(images) {
    const width = images[0].width;
    const height = images[0].height;
    const depth = images.length;

    // 创建3D ndarray
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
          // 二值化: 任何非0值视为1
          volume.set(z, y, x, pixels[idx] > 0 ? 1.0 : 0.0);
        }
      }
    }

    return volume;
  }

  interpolateZ(volume, factor) {
    const [d, h, w] = volume.shape;
    const newD = (d - 1) * factor + 1;

    const newData = new Float32Array(newD * h * w);
    const newVolume = ndarray(newData, [newD, h, w]);

    for (let nz = 0; nz < newD; nz++) {
      const oz = nz / factor;
      const z0 = Math.floor(oz);
      const z1 = Math.min(z0 + 1, d - 1);
      const t = oz - z0;

      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const v0 = volume.get(z0, y, x);
          const v1 = volume.get(z1, y, x);
          newVolume.set(nz, y, x, v0 * (1 - t) + v1 * t);
        }
      }
    }

    return newVolume;
  }

  gaussianSmooth(volume, iterations = 20) {
    // 使用ndarray-ops进行高效的卷积操作
    // 简化版本: 多次3x3x3平均
    let current = volume;

    for (let i = 0; i < iterations; i++) {
      current = this.smoothOnce(current);
    }

    return current;
  }

  smoothOnce(volume) {
    const [d, h, w] = volume.shape;
    const newData = new Float32Array(d * h * w);
    const result = ndarray(newData, [d, h, w]);

    for (let z = 0; z < d; z++) {
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          let sum = 0, count = 0;

          for (let dz = -1; dz <= 1; dz++) {
            for (let dy = -1; dy <= 1; dy++) {
              for (let dx = -1; dx <= 1; dx++) {
                const nz = z + dz, ny = y + dy, nx = x + dx;
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
        vertices[idx + 2] = vtx[2] * spacing.dz / 3; // 除以3因为做了3倍插值
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.computeVertexNormals();
    geometry.center();
    geometry.computeBoundingBox();

    return geometry;
  }
}

export default Client3DReconstructor;
```

### 步骤3: 添加后端API返回mask图像列表

在`CTAI_web`的后端API中添加:

**文件**: `api.py` (或类似的后端文件)

```python
from fastapi import APIRouter
from pathlib import Path

router = APIRouter()

@router.get("/get_mask_images/{patient}/{date}/{mask_type}")
async def get_mask_images(patient: str, date: str, mask_type: str):
    """
    返回mask图像URL列表,而不是生成STL文件
    mask_type: 'psoas' 或 'muscle'
    """
    # 确定mask目录
    if mask_type == 'psoas':
        mask_dir = f"output/{patient}/{date}/major_mask"  # 腰大肌mask
    elif mask_type == 'muscle':
        mask_dir = f"output/{patient}/{date}/full_mask"   # 全肌肉mask
    else:
        raise HTTPException(400, "Invalid mask_type")

    mask_path = Path(mask_dir)
    if not mask_path.exists():
        return {"available": False, "images": []}

    # 获取所有mask图像并排序
    mask_files = sorted([f.name for f in mask_path.glob("*.png")])

    return {
        "available": True,
        "images": mask_files,
        "count": len(mask_files),
        "mask_type": mask_type
    }
```

### 步骤4: 修改Model3DViewer.vue

修改`loadModel()`方法以支持客户端重建:

```javascript
// 在 Model3DViewer.vue 的 methods 中添加

async loadModel() {
  console.log('[3D加载] 开始加载模型...');
  this.loading = true;
  this.error = null;

  try {
    // 移除旧模型
    if (this.currentMesh) {
      this.scene.remove(this.currentMesh);
      this.currentMesh.geometry?.dispose();
      this.currentMesh.material?.dispose();
    }

    // **关键修改**: 使用客户端重建
    const geometry = await this.client3DReconstruction();

    // 创建材质和网格
    const material = new THREE.MeshPhongMaterial({
      color: this.getModelColor(this.currentModel),
      specular: 0x111111,
      shininess: 200,
      side: THREE.DoubleSide
    });

    this.currentMesh = new THREE.Mesh(geometry, material);
    this.scene.add(this.currentMesh);

    this.updateModelStats(geometry);
    this.fitCameraToModel();

    this.$message.success('3D模型加载成功');
  } catch (err) {
    console.error('[3D加载] 失败:', err);
    this.error = err.message || '加载失败';
    this.$message.error(this.error);
  } finally {
    this.loading = false;
  }
},

async client3DReconstruction() {
  // 导入重建器
  const { Client3DReconstructor } = await import('@/utils/client3DReconstructor');
  const reconstructor = new Client3DReconstructor();

  // 1. 获取mask图像列表
  const maskListUrl = `${process.env.VUE_APP_BASE_URL}/get_mask_images/${this.patient}/${this.date}/${this.currentModel}`;
  const response = await fetch(maskListUrl);
  const data = await response.json();

  if (!data.available || data.images.length === 0) {
    throw new Error('没有可用的mask图像');
  }

  // 2. 构建图像URL列表
  const baseUrl = `${process.env.VUE_APP_BASE_URL}/get_output_image/${this.patient}/${this.date}`;
  const folder = this.currentModel === 'psoas' ? 'major_mask' : 'full_mask';
  const maskUrls = data.images.map(img =>
    `${baseUrl}/${folder}/${img}?token=${localStorage.getItem('access_token')}&t=${Date.now()}`
  );

  console.log(`[客户端3D] 找到 ${maskUrls.length} 张mask图像`);

  // 3. 执行客户端重建
  const spacing = { dx: 0.73, dy: 0.73, dz: 3.0 }; // 根据实际CT spacing调整

  const geometry = await reconstructor.reconstruct(
    maskUrls,
    spacing,
    (percent, message) => {
      console.log(`[客户端3D] ${percent}% - ${message}`);
      // 可选: 更新loading消息显示进度
      this.loadingMessage = `${message} (${percent}%)`;
    }
  );

  return geometry;
}
```

### 步骤5: package.json确认

确保`CTAI_web/package.json`包含:

```json
{
  "dependencies": {
    "three": "^0.150.0",
    "isosurface": "^1.1.0",
    "ndarray": "^1.0.19",
    "ndarray-ops": "^1.2.2"
  }
}
```

## 性能优化建议

### 1. 使用Web Workers

为了避免阻塞主线程,可以将重建过程放在Web Worker中:

创建`CTAI_web/public/3d-worker.js`:

```javascript
importScripts('https://unpkg.com/isosurface@1.1.0/lib/surfacenets.js');

self.onmessage = async function(e) {
  const { volume, spacing } = e.data;

  try {
    // 在worker中执行marching cubes
    const mesh = surfaceNets(volume, 0.5);

    self.postMessage({
      success: true,
      mesh: mesh
    });
  } catch (error) {
    self.postMessage({
      success: false,
      error: error.message
    });
  }
};
```

### 2. 渐进式加载

如果mask图像很多,可以分批加载和处理:

```javascript
// 每次处理10张图像
const batchSize = 10;
for (let i = 0; i < maskUrls.length; i += batchSize) {
  const batch = maskUrls.slice(i, i + batchSize);
  await processBatch(batch);
  onProgress(i / maskUrls.length * 100);
}
```

### 3. 缓存重建结果

将重建后的几何体缓存到IndexedDB:

```javascript
// 使用localforage或直接使用IndexedDB
import localforage from 'localforage';

// 保存
await localforage.setItem(
  `3d_model_${patient}_${date}_${maskType}`,
  geometryData
);

// 加载
const cached = await localforage.getItem(
  `3d_model_${patient}_${date}_${maskType}`
);
```

## 预期效果

**数据传输对比:**

| 方案 | 数据量 | 传输时间(10Mbps) |
|------|--------|------------------|
| 服务器STL | 2.5GB | ~33分钟 |
| Mask图像(50张) | ~5MB | ~4秒 |

**总体提升:**
- 网络传输时间减少99%+
- 服务器存储压力大幅降低
- 用户可以实时看到重建进度

## 故障排查

### 问题1: CORS错误

如果遇到跨域问题,确保后端API设置了正确的CORS头:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 问题2: 内存不足

如果处理大量图像时内存不足:
- 减少Z轴插值倍数
- 减少平滑迭代次数
- 使用Web Worker隔离内存

### 问题3: 重建速度慢

优化方法:
- 降低图像分辨率(可以在加载时resize)
- 使用Surface Nets代替Marching Cubes (速度更快)
- 启用Web Worker并行处理

## 下一步

1. 先安装npm包并测试基础功能
2. 逐步添加优化(Web Workers, 缓存等)
3. 根据实际CT spacing调整参数
4. 添加更多的用户反馈(进度条, 预览等)
