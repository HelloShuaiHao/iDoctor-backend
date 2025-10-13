# 后台任务改造说明

## 📋 改动内容

### 1. **app.py** - 主要改动
- ✅ 添加全局 `task_status` 字典，存储任务状态
- ✅ 修改 `/process/{patient_name}/{study_date}` 为异步后台任务
- ✅ 修改 `/continue_after_l3/{patient_name}/{study_date}` 为异步后台任务
- ✅ 新增 `/task_status/{task_id}` 接口，查询任务状态
- ✅ 新增 `/list_tasks` 接口，列出所有任务

### 2. **seg.py** - nnUNet 优化
- ✅ 设置 `num_processes_preprocessing=0` 禁用预处理多进程
- ✅ 设置 `num_processes_segmentation_export=0` 禁用导出多进程
- ✅ 添加详细调试日志

### 3. **all_new.py** - 调试增强
- ✅ 添加详细的流程日志
- ✅ 标记关键步骤的开始和结束

---

## 🚀 使用方法

### 前端调用流程

#### 1. 提交任务
```javascript
// 调用 continue_after_l3
const response = await fetch('/continue_after_l3/613100/20250929', {
  method: 'POST'
});

const result = await response.json();
console.log(result);
// {
//   "status": "submitted",
//   "task_id": "613100_20250929",
//   "message": "任务已提交到后台处理，请轮询 /task_status/{task_id} 查看进度"
// }
```

#### 2. 轮询任务状态
```javascript
const taskId = result.task_id;

const interval = setInterval(async () => {
  const statusRes = await fetch(`/task_status/${taskId}`);
  const status = await statusRes.json();
  
  console.log(`进度: ${status.progress}% - ${status.message}`);
  
  if (status.status === 'completed') {
    clearInterval(interval);
    console.log('✅ 任务完成!', status.result);
  } else if (status.status === 'failed') {
    clearInterval(interval);
    console.error('❌ 任务失败:', status.error);
  }
}, 5000); // 每 5 秒查询一次
```

---

## 🧪 测试方法

### 方法 1：使用测试脚本（推荐）

```bash
# 安装依赖
pip install requests

# 测试 continue_after_l3
python test_backend.py 613100 20250929

# 列出所有任务
python test_backend.py list
```

### 方法 2：使用 curl

```bash
# 1. 提交任务
curl -X POST http://localhost:4200/continue_after_l3/613100/20250929

# 2. 查询状态
curl http://localhost:4200/task_status/613100_20250929

# 3. 列出所有任务
curl http://localhost:4200/list_tasks
```

### 方法 3：使用浏览器

直接访问：
- http://localhost:4200/list_tasks
- http://localhost:4200/task_status/613100_20250929

---

## 📊 任务状态说明

### 任务状态类型
- `processing`: 正在处理中
- `completed`: 处理完成
- `failed`: 处理失败
- `not_found`: 任务不存在

### 状态响应示例

#### 处理中
```json
{
  "status": "processing",
  "progress": 10,
  "message": "正在读取 DICOM 和 L3 mask..."
}
```

#### 完成
```json
{
  "status": "completed",
  "progress": 100,
  "message": "处理完成",
  "result": {
    "sagittal_png": "L3_png/sagittal_midResize.png",
    "l3_mask": "L3_clean_mask/sagittal_midResize.png",
    ...
  }
}
```

#### 失败
```json
{
  "status": "failed",
  "progress": 0,
  "message": "处理失败: ...",
  "error": "详细错误信息"
}
```

---

## 🔧 启动服务

```bash
# 1. 清理旧进程（重要！）
pkill -9 -f uvicorn
lsof -ti:4200 | xargs kill -9

# 2. 启动服务（单 worker）
uvicorn app:app --host 0.0.0.0 --port 4200 --workers 1 --timeout-keep-alive 30

# 或使用 gunicorn（推荐生产环境）
gunicorn app:app -w 2 -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:4200 \
    --timeout 600 \
    --max-requests 100 \
    --max-requests-jitter 10
```

---

## ✅ 优势

1. **不会超时**: HTTP 请求立即返回，不会因为推理耗时长而超时
2. **不会卡死**: 任务在后台执行，即使卡住也不影响其他请求
3. **可监控**: 前端可实时查询进度和状态
4. **可重试**: 任务失败后可以查看错误信息
5. **防重复**: 自动检测重复提交

---

## 🐛 调试

### 查看日志
```bash
# 服务端日志会显示详细的流程信息
[LOG] ========== 开始横断面切片 ==========
[LOG] ========== 开始腰大肌分割 ==========
[DEBUG] 开始推理: ...
[DEBUG] 推理完成: ...
```

### 监控资源
```bash
# 监控连接数
watch -n 1 'lsof -i :4200 | wc -l'

# 监控进程数
watch -n 1 'ps aux | grep python | wc -l'

# 监控 GPU
watch -n 1 nvidia-smi
```

