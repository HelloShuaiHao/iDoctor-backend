# 安全配置指南

## 🔒 敏感信息管理

### 重要原则

1. **永远不要将敏感信息硬编码到代码中**
2. **永远不要将 `.env` 文件提交到 Git**
3. **使用强密码和密钥**
4. **定期更换密钥和凭据**

### 配置文件说明

```
commercial/
├── .env                # ⚠️ 真实配置（不提交到git）
├── .env.example        # ✅ 配置模板（可以提交）
└── .gitignore          # ✅ 排除敏感文件
```

## 📝 初始化配置

### 1. 复制配置模板

```bash
cd commercial
cp .env.example .env
```

### 2. 编辑 .env 文件

```bash
# 使用你喜欢的编辑器
vim .env
# 或
code .env
```

### 3. 填写真实的配置值

```env
# 邮箱配置示例
SMTP_USER=your-real-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=your-real-email@gmail.com

# JWT密钥（生成强密钥）
JWT_SECRET_KEY=your-long-random-secret-key-here
```

## 🔑 生成安全密钥

### JWT密钥生成

```bash
# 使用 OpenSSL
openssl rand -hex 32

# 使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### Gmail应用专用密码

1. 登录 Google 账户
2. 开启两步验证：https://myaccount.google.com/security
3. 生成应用专用密码：https://myaccount.google.com/apppasswords
4. 使用生成的16位密码（不是Gmail登录密码）

## ⚠️ 常见安全错误

### ❌ 错误做法

```yaml
# docker-compose.yml
environment:
  SMTP_PASSWORD: my-real-password-123  # 直接硬编码！
```

```python
# config.py
SMTP_PASSWORD = "my-real-password-123"  # 直接硬编码！
```

### ✅ 正确做法

```yaml
# docker-compose.yml
env_file:
  - ../.env  # 从文件读取
environment:
  ENVIRONMENT: development  # 只放非敏感配置
```

```python
# config.py
class Settings(BaseSettings):
    SMTP_PASSWORD: str = ""  # 从环境变量读取

    model_config = SettingsConfigDict(
        env_file="../.env"
    )
```

## 🛡️ 生产环境最佳实践

### 1. 使用环境变量

生产环境推荐直接使用环境变量，而不是 `.env` 文件：

```bash
# 在服务器上设置
export SMTP_PASSWORD="production-password"
export JWT_SECRET_KEY="production-jwt-key"
```

### 2. 使用 Docker Secrets（推荐）

```yaml
# docker-compose.prod.yml
services:
  auth_service:
    secrets:
      - smtp_password
      - jwt_secret

secrets:
  smtp_password:
    external: true
  jwt_secret:
    external: true
```

### 3. 使用密钥管理服务

- **AWS Secrets Manager**
- **Azure Key Vault**
- **HashiCorp Vault**
- **Kubernetes Secrets**

## 📋 检查清单

部署前请确认：

- [ ] `.env` 文件在 `.gitignore` 中
- [ ] `.env.example` 不包含真实密钥
- [ ] 所有密钥都已更换为强密钥
- [ ] JWT密钥至少64位
- [ ] SMTP使用应用专用密码
- [ ] 数据库密码足够强
- [ ] 生产环境使用不同的密钥

## 🚨 如果密钥泄露怎么办

1. **立即更换所有泄露的密钥**
2. **检查是否有异常访问**
3. **更新 Git 历史（如果已提交）**

```bash
# 从Git历史中完全删除敏感文件
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch commercial/.env" \
  --prune-empty --tag-name-filter cat -- --all

git push origin --force --all
```

4. **通知团队成员更新密钥**

## 📚 相关资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [12 Factor App - Config](https://12factor.net/config)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

**记住：安全配置是保护用户数据和系统安全的第一道防线！**
