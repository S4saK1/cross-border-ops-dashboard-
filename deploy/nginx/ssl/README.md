# SSL 证书目录

自签名证书仅用于开发/测试环境，**禁止用于生产**。

## 生产部署

使用 Let's Encrypt 获取正式证书：

```bash
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/nginx/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem deploy/nginx/ssl/
```

## 文件清单

| 文件 | 说明 |
|------|------|
| `fullchain.pem` | 证书链（含中间证书） |
| `privkey.pem` | 私钥（权限 600） |

## 自动续期

建议配合 certbot renew hook：

```bash
certbot renew --post-hook "docker compose -f docker-compose.prod.yml restart nginx"
```
