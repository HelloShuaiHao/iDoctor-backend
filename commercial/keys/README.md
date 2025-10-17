# 支付密钥文件目录

本目录用于存放支付宝和微信支付的密钥文件。

## ⚠️ 安全警告

**绝对不要将此目录下的 `.pem`、`.p12` 等密钥文件提交到 Git！**

已配置 `.gitignore` 自动忽略所有密钥文件。

## 📁 文件说明

### 支付宝密钥

- `alipay_private_key.pem` - 支付宝应用私钥（RSA2048）
- `alipay_public_key.pem` - 支付宝公钥（从支付宝平台获取）

### 微信支付密钥

- `apiclient_cert.pem` - 微信商户证书
- `apiclient_key.pem` - 微信商户私钥

## 🔧 配置步骤

详细配置步骤请参考：[支付系统配置指南](../docs/PAYMENT_SETUP_GUIDE.md)

### 快速检查清单

- [ ] 已生成支付宝密钥对
- [ ] 已上传支付宝应用公钥到开放平台
- [ ] 已下载支付宝公钥并保存为 `alipay_public_key.pem`
- [ ] 已从微信商户平台下载证书文件
- [ ] 已在 `.env` 文件中配置密钥路径
- [ ] 已验证文件权限（建议 `chmod 600 *.pem`）

## 📝 文件格式示例

### PEM 格式（支付宝/微信通用）

```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...（Base64编码内容）...
-----END RSA PRIVATE KEY-----
```

或

```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
...
-----END PUBLIC KEY-----
```

## 🛡️ 安全建议

1. **限制文件权限**
   ```bash
   chmod 600 keys/*.pem
   ```

2. **环境隔离**
   - 开发环境使用沙箱密钥
   - 生产环境使用正式密钥
   - 绝不混用

3. **定期轮换**
   - 建议每年更换一次密钥
   - 离职人员接触过的密钥立即更换

4. **备份密钥**
   - 将密钥安全存储在密码管理器或加密存储中
   - 不要通过聊天软件、邮件明文传输

## 🆘 故障排查

### 密钥读取失败

```python
FileNotFoundError: [Errno 2] No such file or directory: './keys/alipay_private_key.pem'
```

**解决**：确认密钥文件存在且路径正确

### 签名验证失败

```
invalid-signature
```

**解决**：
1. 检查密钥格式（必须有 BEGIN/END 行）
2. 确认支付宝公钥与平台显示一致
3. 验证私钥与上传的公钥匹配

## 📞 联系方式

如需帮助，请参考：
- [支付宝开放平台](https://open.alipay.com/)
- [微信支付商户平台](https://pay.weixin.qq.com/)
- 项目配置指南：`docs/PAYMENT_SETUP_GUIDE.md`
