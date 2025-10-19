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

        const response = await axios.post(`${AUTH_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken
        })

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
    const tokenParam = token ? `&token=${token}` : '';
    return `${BASE_URL}/get_image/${encodeURIComponent(patient_name)}/${study_date}/${filename}?t=${Date.now()}${tokenParam}`;
}

// ...existing code...

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

// 获取 L3 相关图片
export function getL3ImageUrl(patient_name, study_date, folder, filename) {
    const token = localStorage.getItem('access_token');
    const tokenParam = token ? `?token=${token}` : '';
    return `${BASE_URL}/get_output_image/${encodeURIComponent(patient_name)}/${study_date}/${folder}/${filename}${tokenParam}`;
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

export { BASE_URL }