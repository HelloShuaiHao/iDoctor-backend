# 生产环境部署指南

## 🚀 快速部署流程

### 1. 本地构建
```bash
# 跳过TypeScript检查的快速构建
npm run build:skip-types

# 或使用完整的构建流程（需修复TypeScript错误）
npm run build

# 或使用部署脚本
npm run deploy:prod
```

### 2. 验证构建结果
```bash
# 检查文件
ls -la dist/

# 验证生产环境URL配置
grep -r "ai.bygpu.com:55304" dist/
```

### 3. 上传到服务器
```bash
# 使用scp上传
scp -r dist/ user@ai.bygpu.com:/path/to/web/

# 或使用rsync
rsync -avz dist/ user@ai.bygpu.com:/path/to/web/
```

## 🌐 服务器配置

### Nginx 配置示例
```nginx
server {
    listen 55303;
    server_name ai.bygpu.com;
    
    root /path/to/web/dist;
    index index.html;
    
    # 支持React Router
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # 静态资源缓存
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
```

### Apache 配置示例
```apache
<VirtualHost *:55303>
    ServerName ai.bygpu.com
    DocumentRoot /path/to/web/dist
    
    # 支持React Router
    <Directory /path/to/web/dist>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
        
        # React Router重写规则
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>
    
    # 静态资源缓存
    <Directory /path/to/web/dist/assets>
        ExpiresActive On
        ExpiresDefault "access plus 1 year"
    </Directory>
</VirtualHost>
```

## 🔧 环境配置

### 环境变量文件优先级
```
.env.local          (本地开发，git忽略)
.env.production     (生产环境，本次部署使用)
.env.development    (开发环境)
.env                (默认配置)
```

### 当前生产配置 (.env.production)
```env
VITE_AUTH_API_URL=http://ai.bygpu.com:9001
VITE_PAYMENT_API_URL=http://ai.bygpu.com:9002
VITE_IDOCTOR_API_URL=http://ai.bygpu.com:4200
VITE_IDOCTOR_APP_URL=http://ai.bygpu.com:55304
VITE_APP_NAME=iDoctor 专业医疗影像分析平台
VITE_DEV_MODE=false
```

## 🚦 部署检查清单

### 构建前检查
- [ ] 确认 `.env.production` 配置正确
- [ ] 验证所有API端点可访问
- [ ] 检查Flask应用(55304端口)运行正常

### 构建检查
- [ ] 构建成功无错误
- [ ] `dist/` 目录生成
- [ ] 生产环境URL正确替换

### 服务器检查
- [ ] Nginx/Apache配置正确
- [ ] 端口55303开放
- [ ] SSL证书配置（推荐HTTPS）
- [ ] 防火墙规则设置

### 功能验证
- [ ] 前端页面正常加载
- [ ] "立即体验分析服务"按钮跳转正确
- [ ] 用户注册/登录功能正常
- [ ] 支付功能测试通过

## 🔄 更新部署

### 快速更新流程
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建
npm run build:skip-types

# 3. 上传到服务器
rsync -avz dist/ user@ai.bygpu.com:/path/to/web/

# 4. 重启服务器（如果需要）
sudo systemctl reload nginx
```

### 回滚策略
```bash
# 备份当前版本
cp -r /path/to/web/dist /path/to/web/dist.backup.$(date +%Y%m%d_%H%M%S)

# 回滚到上一版本
mv /path/to/web/dist.backup.TIMESTAMP /path/to/web/dist
```

## 🐛 故障排查

### 常见问题

1. **页面空白**
   - 检查控制台错误
   - 验证静态资源路径
   - 确认服务器配置

2. **API请求失败**
   - 验证API服务运行状态
   - 检查CORS配置
   - 确认端口开放

3. **跳转失败**
   - 验证Flask应用运行(55304端口)
   - 检查端口转发配置
   - 确认环境变量正确

### 调试命令
```bash
# 查看服务状态
sudo systemctl status nginx
netstat -tlnp | grep :55303

# 测试API连接
curl http://ai.bygpu.com:9001/health
curl http://ai.bygpu.com:55304

# 查看日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## 📊 性能优化

### 构建优化
- 启用代码分割
- 压缩静态资源
- 使用CDN加速

### 服务器优化
- 启用Gzip压缩
- 配置静态资源缓存
- 使用HTTP/2

这就是完整的生产环境部署流程！