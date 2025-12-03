<template>
  <div class="model-3d-viewer">
    <div class="viewer-header">
      <h3>3D模型可视化</h3>
      <div class="viewer-controls">
        <el-button-group size="mini">
          <el-button @click="resetCamera" icon="el-icon-refresh">重置视角</el-button>
          <el-button @click="toggleRotation" :type="autoRotate ? 'primary' : ''">
            {{ autoRotate ? '停止旋转' : '自动旋转' }}
          </el-button>
        </el-button-group>
        <el-select v-model="currentModel" size="mini" placeholder="选择模型" style="margin-left: 10px; width: 150px;" @change="loadModel">
          <el-option label="腰大肌" value="psoas" />
          <el-option label="全肌肉" value="muscle" />
          <el-option label="椎骨" value="vertebra" />
        </el-select>
      </div>
    </div>

    <div
      ref="container"
      class="viewer-container"
      v-loading="loading"
      element-loading-text="加载3D模型中..."
    >
      <div v-if="error" class="error-message">
        <i class="el-icon-warning"></i>
        <p>{{ error }}</p>
        <el-button size="small" @click="loadModel">重试</el-button>
      </div>
    </div>

    <div class="viewer-info">
      <div class="info-item">
        <span class="label">顶点数:</span>
        <span class="value">{{ modelStats.vertices }}</span>
      </div>
      <div class="info-item">
        <span class="label">面数:</span>
        <span class="value">{{ modelStats.faces }}</span>
      </div>
      <div class="info-item">
        <span class="label">体积:</span>
        <span class="value">{{ modelStats.volume }}</span>
      </div>
    </div>

    <div class="viewer-tips">
      <p><i class="el-icon-info"></i> 鼠标左键拖动旋转，滚轮缩放，右键拖动平移</p>
    </div>
  </div>
</template>

<script>
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';

export default {
  name: 'Model3DViewer',
  props: {
    patient: {
      type: String,
      required: true
    },
    date: {
      type: String,
      required: true
    },
    selectedMaskType: {
      type: String,
      default: 'psoas'
    }
  },
  data() {
    return {
      loading: false,
      error: null,
      scene: null,
      camera: null,
      renderer: null,
      controls: null,
      currentMesh: null,
      autoRotate: false,
      animationId: null,
      currentModel: this.selectedMaskType || 'psoas', // 使用传入的prop作为初始值
      modelStats: {
        vertices: 0,
        faces: 0,
        volume: '-'
      }
    };
  },
  watch: {
    selectedMaskType(newVal) {
      // 当外部传入的maskType改变时，更新currentModel并重新加载
      if (newVal && newVal !== this.currentModel) {
        this.currentModel = newVal;
        this.loadModel();
      }
    }
  },
  mounted() {
    this.initScene();
    this.loadModel();
    window.addEventListener('resize', this.onWindowResize);
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.onWindowResize);
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }
    if (this.renderer) {
      this.renderer.dispose();
    }
  },
  methods: {
    initScene() {
      const container = this.$refs.container;
      if (!container) return;

      const width = container.clientWidth;
      const height = container.clientHeight || 500;

      // 创建场景
      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0xf5f5f5);

      // 创建相机
      this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000);
      this.camera.position.set(0, 0, 300);

      // 创建渲染器
      this.renderer = new THREE.WebGLRenderer({ antialias: true });
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(window.devicePixelRatio);
      container.appendChild(this.renderer.domElement);

      // 添加控制器
      this.controls = new OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;
      this.controls.screenSpacePanning = false;
      this.controls.minDistance = 50;
      this.controls.maxDistance = 1000;

      // 添加灯光
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
      this.scene.add(ambientLight);

      const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
      directionalLight1.position.set(1, 1, 1);
      this.scene.add(directionalLight1);

      const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
      directionalLight2.position.set(-1, -1, -1);
      this.scene.add(directionalLight2);

      // 添加网格辅助线
      const gridHelper = new THREE.GridHelper(400, 20, 0xcccccc, 0xe0e0e0);
      this.scene.add(gridHelper);

      // 开始渲染循环
      this.animate();
    },
    animate() {
      this.animationId = requestAnimationFrame(this.animate);

      if (this.autoRotate && this.currentMesh) {
        this.currentMesh.rotation.y += 0.005;
      }

      this.controls.update();
      this.renderer.render(this.scene, this.camera);
    },
    async loadModel() {
      console.log('[3D加载] 开始加载模型...', {
        patient: this.patient,
        date: this.date,
        currentModel: this.currentModel
      });

      this.loading = true;
      this.error = null;

      try {
        // 移除旧模型
        if (this.currentMesh) {
          this.scene.remove(this.currentMesh);
          if (this.currentMesh.geometry) {
            this.currentMesh.geometry.dispose();
          }
          if (this.currentMesh.material) {
            this.currentMesh.material.dispose();
          }
        }

        // 构建3D模型URL
        const modelUrl = this.get3DModelUrl(this.currentModel);
        console.log('[3D加载] 模型URL:', modelUrl);

        // 加载模型
        const loader = this.getLoader(modelUrl);
        console.log('[3D加载] 使用加载器:', loader.constructor.name);

        const geometry = await this.loadGeometry(loader, modelUrl);
        console.log('[3D加载] 几何体加载成功');

        // 居中几何体
        geometry.center();
        geometry.computeBoundingBox();
        geometry.computeVertexNormals();

        // 创建材质
        const material = new THREE.MeshPhongMaterial({
          color: this.getModelColor(this.currentModel),
          specular: 0x111111,
          shininess: 200,
          side: THREE.DoubleSide
        });

        // 创建网格
        this.currentMesh = new THREE.Mesh(geometry, material);
        this.scene.add(this.currentMesh);

        // 更新统计信息
        this.updateModelStats(geometry);

        // 调整相机位置以适应模型
        this.fitCameraToModel();

        console.log('[3D加载] 模型加载完成');
        this.$message.success('3D模型加载成功');
      } catch (err) {
        console.error('[3D加载] 加载3D模型失败:', err);
        this.error = err.message || '加载3D模型失败，请检查模型文件是否存在';
        this.$message.error(this.error);
      } finally {
        this.loading = false;
      }
    },
    getLoader(url) {
      if (url.endsWith('.stl')) {
        return new STLLoader();
      } else if (url.endsWith('.obj')) {
        return new OBJLoader();
      }
      throw new Error('不支持的模型格式');
    },
    loadGeometry(loader, url) {
      return new Promise((resolve, reject) => {
        loader.load(
          url,
          (geometry) => {
            if (geometry.isBufferGeometry) {
              resolve(geometry);
            } else if (geometry.children && geometry.children.length > 0) {
              // OBJ可能返回Group
              resolve(geometry.children[0].geometry);
            } else {
              reject(new Error('无效的几何体'));
            }
          },
          (progress) => {
            if (progress.lengthComputable) {
              const percent = (progress.loaded / progress.total) * 100;
              console.log(`加载进度: ${percent.toFixed(2)}%`);
            }
          },
          (error) => {
            reject(error);
          }
        );
      });
    },
    get3DModelUrl(modelType) {
      const BASE_URL = process.env.VUE_APP_BASE_URL || 'http://localhost:4200';
      const token = localStorage.getItem('access_token');
      const filename = this.getModelFilename(modelType);

      const params = new URLSearchParams();
      params.append('t', Date.now());
      if (token) {
        params.append('token', token);
      }

      return `${BASE_URL}/get_3d_model/${encodeURIComponent(this.patient)}/${this.date}/${filename}?${params.toString()}`;
    },
    getModelFilename(modelType) {
      const filenames = {
        psoas: 'psoas_3d.stl',
        muscle: 'muscle_3d.stl',
        vertebra: 'vertebra_3d.stl'
      };
      return filenames[modelType] || 'psoas_3d.stl';
    },
    getModelColor(modelType) {
      const colors = {
        psoas: 0xff6b6b,      // 红色 - 腰大肌
        muscle: 0x4ecdc4,     // 青色 - 全肌肉
        vertebra: 0xf7fff7    // 白色 - 椎骨
      };
      return colors[modelType] || 0xff6b6b;
    },
    updateModelStats(geometry) {
      const vertices = geometry.attributes.position.count;
      const faces = geometry.index ? geometry.index.count / 3 : vertices / 3;

      this.modelStats = {
        vertices: vertices.toLocaleString(),
        faces: Math.floor(faces).toLocaleString(),
        volume: '-' // 体积计算比较复杂，暂时显示-
      };
    },
    fitCameraToModel() {
      if (!this.currentMesh) return;

      const box = new THREE.Box3().setFromObject(this.currentMesh);
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());

      const maxDim = Math.max(size.x, size.y, size.z);
      const fov = this.camera.fov * (Math.PI / 180);
      let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
      cameraZ *= 1.5; // 增加一些边距

      this.camera.position.set(center.x, center.y, center.z + cameraZ);
      this.camera.lookAt(center);
      this.controls.target.copy(center);
      this.controls.update();
    },
    resetCamera() {
      this.camera.position.set(0, 0, 300);
      this.camera.lookAt(0, 0, 0);
      this.controls.target.set(0, 0, 0);
      this.controls.update();

      if (this.currentMesh) {
        this.fitCameraToModel();
      }
    },
    toggleRotation() {
      this.autoRotate = !this.autoRotate;
    },
    onWindowResize() {
      const container = this.$refs.container;
      if (!container) return;

      const width = container.clientWidth;
      const height = container.clientHeight;

      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(width, height);
    }
  }
};
</script>

<style scoped>
.model-3d-viewer {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.viewer-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.viewer-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.viewer-container {
  width: 100%;
  height: 500px;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f5f5;
  position: relative;
}

.error-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #f56c6c;
}

.error-message i {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-message p {
  margin: 0 0 16px 0;
  font-size: 14px;
}

.viewer-info {
  display: flex;
  gap: 20px;
  margin-top: 16px;
  padding: 12px;
  background: #f6f9ff;
  border-radius: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item .label {
  color: #666;
  font-size: 13px;
}

.info-item .value {
  color: #0f172a;
  font-weight: 600;
  font-size: 14px;
}

.viewer-tips {
  margin-top: 12px;
  padding: 8px 12px;
  background: #fff9e6;
  border-radius: 6px;
  border-left: 3px solid #ffc107;
}

.viewer-tips p {
  margin: 0;
  font-size: 12px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 6px;
}

.viewer-tips i {
  color: #ffc107;
}
</style>
