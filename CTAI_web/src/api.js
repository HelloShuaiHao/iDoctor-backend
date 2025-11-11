import axios from "axios"
import Vue from 'vue'
import { Message, MessageBox } from 'element-ui'

const BASE_URL = process.env.VUE_APP_BASE_URL || "http://localhost:4200"
const AUTH_BASE_URL = process.env.VUE_APP_AUTH_BASE_URL || "http://localhost:9001"

// 请求拦截器：自动添加 JWT token
axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理 token 过期和配额耗尽
axios.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config

    // 处理 401 Unauthorized (token 过期)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // 尝试刷新 token
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) {
          throw new Error('No refresh token')
        }

        // FastAPI expects query parameter
        const response = await axios.post(`${AUTH_BASE_URL}/refresh?refresh_token=${encodeURIComponent(refreshToken)}`)

        // 更新 token
        localStorage.setItem('access_token', response.data.access_token)
        localStorage.setItem('refresh_token', response.data.refresh_token)

        // 重试原请求
        originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`
        return axios(originalRequest)
      } catch (refreshError) {
        // 刷新失败，清除 token 并跳转登录
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')

        Message.warning('登录已过期，请重新登录')

        setTimeout(() => {
          window.location.href = '/#/login'
        }, 1500)

        return Promise.reject(refreshError)
      }
    }

    // 处理 402 Payment Required (配额耗尽)
    if (error.response?.status === 402) {
      const quotaInfo = error.response.data

      MessageBox.confirm(
        `${quotaInfo.message || '配额已用尽'}\n剩余配额: ${quotaInfo.remaining || 0}`,
        '配额不足',
        {
          confirmButtonText: '立即升级',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(() => {
        // 跳转到商业前端的订阅页面
        const token = localStorage.getItem('access_token')
        const commercialUrl = process.env.VUE_APP_COMMERCIAL_URL || 'http://localhost:3000'
        window.location.href = `${commercialUrl}/#/subscription?token=${token}`
      }).catch(() => {
        // 用户取消
      })

      return Promise.reject(error)
    }

    // 处理 403 Forbidden (访问权限)
    if (error.response?.status === 403) {
      Message.error('您没有权限访问此数据')
      return Promise.reject(error)
    }

    return Promise.reject(error)
  }
)

// 上传 DICOM ZIP 文件，支持前端进度回调
// params: { patient_name, study_date, file, onProgress?: (percent:number, loaded:number, total:number, rawEvent:ProgressEvent) => void }
export async function uploadDicomZip({ patient_name, study_date, file, onProgress }) {
  const formData = new FormData()
  formData.append("patient_name", patient_name)
  formData.append("study_date", study_date)
  formData.append("file", file)
  // 传递文件大小用于后端校验与进度百分比计算
  if (file && file.size != null) {
    formData.append("file_size", file.size)
  }
  return axios.post(`${BASE_URL}/upload_dicom_zip`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (evt) => {
      if (!onProgress) return
      const total = evt.total || (file && file.size) || 0
      const loaded = evt.loaded
      let percent = 0
      if (total > 0) {
        percent = Math.min(100, Math.round((loaded / total) * 100))
      }
      onProgress(percent, loaded, total, evt)
    }
  })
}

// 处理数据
export async function processCase(patient_name, study_date) {
  return axios.post(`${BASE_URL}/process/${encodeURIComponent(patient_name)}/${study_date}`)
}

// 获取所有已处理病人-日期列表
export async function listPatients() {
  return axios.get(`${BASE_URL}/list_patients`)
}

// 获取关键结果（csv内容和图片名）
export async function getKeyResults(patient_name, study_date) {
  return axios.get(`${BASE_URL}/get_key_results/${encodeURIComponent(patient_name)}/${study_date}`)
}

//添加时间戳和 token（用于认证）
export function getImageUrl(patient_name, study_date, filename) {
  const token = localStorage.getItem('access_token');
  const params = new URLSearchParams();
  params.append('t', Date.now());
  if (token) {
    params.append('token', token);
  }
  return `${BASE_URL}/get_image/${encodeURIComponent(patient_name)}/${study_date}/${filename}?${params.toString()}`;
}

// L3 检测
export async function l3Detect(patient_name, study_date) {
  return axios.post(`${BASE_URL}/l3_detect/${encodeURIComponent(patient_name)}/${study_date}`);
}

// 手动上传 L3 mask
export async function uploadL3Mask(patient, date, file) {
  const formData = new FormData();
  formData.append("file", file);
  return axios.post(`${BASE_URL}/upload_l3_mask/${encodeURIComponent(patient)}/${date}`, formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
}

// L3 之后的流程
export async function continueAfterL3(patient_name, study_date) {
  return axios.post(`${BASE_URL}/continue_after_l3/${encodeURIComponent(patient_name)}/${study_date}`);
}

// 获取 L3 相关图片（修复：正确处理URL参数，添加时间戳和token）
export function getL3ImageUrl(patient_name, study_date, folder, filename) {
  const token = localStorage.getItem('access_token');
  const params = new URLSearchParams();
  params.append('t', Date.now());  // 添加时间戳防止缓存
  if (token) {
    params.append('token', token);
  }
  return `${BASE_URL}/get_output_image/${encodeURIComponent(patient_name)}/${study_date}/${folder}/${filename}?${params.toString()}`;
}

// 生成侧视图（sagittal）
export async function generateSagittal(patient_name, study_date, force = 0) {
  return axios.post(`${BASE_URL}/generate_sagittal/${encodeURIComponent(patient_name)}/${study_date}?force=${force}`);
}

export function getAxisalImageUrl(patient_name, study_date, filename) {
  return getL3ImageUrl(patient_name, study_date, 'Axisal', filename)
}

// 手动上传 Middle 原图的 psoas/combo mask
export async function uploadMiddleManualMask(patient, date, psoasFile, comboFile) {
  const fd = new FormData()
  if (psoasFile) fd.append('psoas_mask', psoasFile)
  if (comboFile) fd.append('combo_mask', comboFile)
  try {
    const res = await axios.post(
      `${BASE_URL}/upload_middle_manual_mask/${encodeURIComponent(patient)}/${encodeURIComponent(date)}`,
      fd,
      { headers: { 'Accept': 'application/json' } }
    )
    return res
  } catch (e) {
    // 让调用方能看到服务器的错误信息
    if (e.response) {
      console.error('[uploadMiddleManualMask] server error:', e.response.status, e.response.data)
      throw new Error((e.response.data && e.response.data.error) || 'HTTP ' + e.response.status);
    } else {
      console.error('[uploadMiddleManualMask] network error:', e)
      throw e
    }
  }
}

// 查询任务状态
export async function getTaskStatus(taskId) {
  return axios.get(`${BASE_URL}/task_status/${taskId}`);
}

// 列出所有任务
export async function listTasks() {
  return axios.get(`${BASE_URL}/list_tasks`);
}

// 查询上传进度
export async function getUploadStatus(upload_id) {
  return axios.get(`${BASE_URL}/upload_status/${upload_id}`)
}

// ==================== SAM2 分割 API ====================

/**
 * SAM2 分割 (支持交互式点击)
 * @param {Object} params - 参数对象
 * @param {Blob|File} params.imageFile - 图像文件对象
 * @param {string} params.imageType - 图像类型 ("L3", "middle", "auto")
 * @param {string} params.patientId - 患者ID (可选)
 * @param {string} params.sliceIndex - 切片索引 (可选)
 * @param {Array} params.clickPoints - 点击坐标数组 (可选)
 *                例: [{x: 100, y: 200, label: 1}]
 *                label: 1=前景点, 0=背景点
 * @returns {Promise<Object>} - 返回分割结果
 * @returns {string} .mask_data - Base64 编码的 mask PNG 图像
 * @returns {number} .confidence_score - 置信度 (0.0-1.0)
 * @returns {number} .processing_time_ms - 处理时间 (毫秒)
 * @returns {boolean} .cached - 是否来自缓存
 * @returns {Object} .bounding_box - 边界框 {x, y, width, height}
 */
export async function sam2Segment({ imageFile, imageType = 'auto', patientId = null, sliceIndex = null, clickPoints = null }) {
  try {
    const formData = new FormData()
    formData.append('file', imageFile)
    formData.append('image_type', imageType)

    if (patientId) {
      formData.append('patient_id', patientId)
    }

    if (sliceIndex) {
      formData.append('slice_index', sliceIndex)
    }

    // 添加点击坐标
    if (clickPoints && clickPoints.length > 0) {
      formData.append('click_points', JSON.stringify(clickPoints))
    }

    const response = await axios.post(
      `${BASE_URL}/api/segmentation/sam2`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 125000 // 125秒超时 (服务端120秒 + 5秒缓冲)
      }
    )

    return response.data
  } catch (error) {
    // 增强错误处理
    if (error.response) {
      const status = error.response.status
      const detail = error.response.data?.detail || error.response.data?.message || 'Unknown error'

      if (status === 503) {
        throw new Error('SAM2 服务暂时不可用，请稍后重试')
      } else if (status === 400) {
        throw new Error(`无效的图像格式: ${detail}`)
      } else if (status === 500) {
        throw new Error(`分割失败: ${detail}`)
      } else {
        throw new Error(`请求失败 (${status}): ${detail}`)
      }
    } else if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      throw new Error('SAM2 分割超时，请重试')
    } else {
      throw new Error(`网络错误: ${error.message}`)
    }
  }
}

/**
 * 检查 SAM2 服务健康状态
 * @returns {Promise<Object>} - 返回健康状态
 * @returns {boolean} .enabled - SAM2 是否启用
 * @returns {boolean} .available - SAM2 是否可用
 * @returns {Object} .cache_stats - 缓存统计信息
 */
export async function checkSam2Health() {
  try {
    const response = await axios.get(`${BASE_URL}/api/segmentation/sam2/health`, {
      timeout: 5000
    })
    return response.data
  } catch (error) {
    console.error('SAM2 health check failed:', error)
    return {
      enabled: false,
      available: false,
      cache_stats: {}
    }
  }
}

// ==================== SAM2 分割 API 结束 ====================

export { BASE_URL }