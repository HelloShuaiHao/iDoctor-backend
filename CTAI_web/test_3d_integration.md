# 3D可视化集成测试指南

## 问题诊断步骤

### 1. 检查前端是否成功构建
```bash
cd CTAI_web
npm run build
# 查看是否有编译错误
```

### 2. 检查浏览器控制台
打开浏览器开发者工具（F12），查看：
- Console标签页是否有JavaScript错误
- Network标签页检查API调用
- 查找以 `[3D检查]` 或 `[3D加载]` 开头的日志

### 3. 验证3D可视化区域是否显示
进入任意病例的Detail页面，应该能看到：
- "3D模型可视化" 标题
- 类型选择下拉框（腰大肌/全肌肉）
- "重建3D模型" 按钮
- 提示信息："暂无3D模型，请点击'重建3D模型'按钮生成"

### 4. 测试3D重建流程

#### 手动触发重建
1. 进入Detail页面
2. 点击"重建3D模型"按钮
3. 观察控制台输出
4. 等待进度条完成
5. 检查是否显示3D查看器

#### 检查后端日志
```bash
# 查看后端日志
tail -f /path/to/backend/logs
```

查找关键日志：
- `收到3D重建请求`
- `开始3D重建任务`
- `3D重建完成`

### 5. 验证API端点

#### 测试check_3d_models端点
```bash
curl -X GET "http://localhost:4200/check_3d_models/{patient_name}/{study_date}"
```

期望返回：
```json
{
  "available": false,
  "models": []
}
```
或
```json
{
  "available": true,
  "models": [
    {
      "filename": "psoas_3d.stl",
      "mask_type": "psoas",
      "volume_mm3": 12345.67,
      "volume_ml": 12.35
    }
  ]
}
```

#### 测试reconstruct_3d端点
```bash
curl -X POST "http://localhost:4200/reconstruct_3d/{patient_name}/{study_date}" \
  -F "mask_type=psoas"
```

期望返回：
```json
{
  "task_id": "3d_recon_...",
  "message": "3D重建任务已提交"
}
```

### 6. 检查文件结构

确认这些文件存在：
```
CTAI_web/src/
├── components/
│   ├── Model3DViewer.vue  ✓ 新增
│   ├── ResultDetail.vue   ✓ 已修改
│   └── ...
├── api.js                  ✓ 已修改
└── ...

model-code/
├── recon.py               ✓ 已修改
├── app.py                 ✓ 已修改
└── ...
```

### 7. 验证Three.js安装

检查package.json:
```bash
cd CTAI_web
cat package.json | grep three
```

应该看到：
```json
"three": "^0.150.0"
```

### 8. 重新构建并清除缓存

```bash
# 前端
cd CTAI_web
rm -rf node_modules/.cache
rm -rf dist
npm run build

# 重启后端
pkill -f "python.*app.py"
python app.py
```

## 常见问题

### Q1: 3D可视化区域不显示
**A**: 检查 ResultDetail.vue 是否正确引入了 Model3DViewer 组件

### Q2: 点击"重建3D模型"无反应
**A**:
1. 检查浏览器控制台是否有错误
2. 检查Network标签，API调用是否成功
3. 确认后端recon.py模块是否正确导入

### Q3: 显示"加载3D模型失败"
**A**:
1. 检查模型文件是否存在：`output/{patient}/{date}/3d_models/`
2. 确认文件格式（应为.stl）
3. 检查文件权限

### Q4: Three.js加载失败
**A**:
```bash
cd CTAI_web
npm install three@0.150.0 --save
npm run build
```

## 预期效果

成功后应该看到：
1. ✅ Detail页面显示"3D模型可视化"区域
2. ✅ 可以选择模型类型（腰大肌/全肌肉）
3. ✅ 点击"重建3D模型"提交任务
4. ✅ 显示进度条
5. ✅ 完成后自动加载3D查看器
6. ✅ 可以用鼠标旋转、缩放模型
7. ✅ 显示模型统计信息（顶点数、面数）

## 调试日志示例

### 正常情况下的控制台输出：
```
[3D检查] 开始检查3D模型可用性... {patient: "xxx", date: "xxx", selectedMaskType: "psoas"}
[3D检查] API返回结果: {available: false, models: []}
[3D检查] 没有可用的3D模型

// 点击重建后：
[3D加载] 开始加载模型... {patient: "xxx", date: "xxx", currentModel: "psoas"}
[3D加载] 模型URL: http://localhost:4200/get_3d_model/xxx/xxx/psoas_3d.stl?t=...
[3D加载] 使用加载器: STLLoader
[3D加载] 几何体加载成功
[3D加载] 模型加载完成
```

## 联系支持

如果问题仍未解决，请提供：
1. 浏览器控制台完整日志
2. 后端日志
3. API调用的Network截图
4. 具体的错误信息
