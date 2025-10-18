# 端口配置说明

## 🌐 服务端口映射

### 开发环境
```
商业化前端：http://localhost:3000
认证服务：  http://localhost:9001  
支付服务：  http://localhost:9002
Flask前端： http://localhost:7500
```

### 生产环境（服务器）
```
商业化前端：http://ai.bygpu.com:55303
认证服务：  http://ai.bygpu.com:9001
支付服务：  http://ai.bygpu.com:9002
Flask前端： http://ai.bygpu.com:55304 → 内部7500端口
```

## ⚠️ 重要说明

### 端口转发机制
- **内部端口 7500**：Flask应用实际运行的端口（服务器内部）
- **外部端口 55304**：通过端口转发对外开放的端口

```bash
# 服务器端口转发配置
iptables -t nat -A PREROUTING -p tcp --dport 55304 -j REDIRECT --to-port 7500
# 或者使用nginx反向代理
```

### 用户访问流程
1. 用户点击"立即体验分析服务"按钮
2. 跳转到 `http://ai.bygpu.com:55304`
3. 服务器将请求转发到内部的 `7500` 端口
4. Flask应用响应请求

## 🔧 配置文件

### .env.development（开发）
```env
VITE_IDOCTOR_APP_URL=http://localhost:7500
```

### .env.production（生产）
```env
VITE_IDOCTOR_APP_URL=http://ai.bygpu.com:55304
```

## 🚀 部署注意事项

1. **开发测试**：使用本地7500端口
2. **生产部署**：必须使用外部55304端口
3. **网络访问**：确保防火墙开放55304端口
4. **SSL证书**：生产环境建议使用HTTPS