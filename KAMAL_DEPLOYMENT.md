# Kamal Deployment Guide for Xavier AI Backend

## Prerequisites

1. **Server Setup**: You need a Linux server (Ubuntu 20.04+ recommended) with:
   - Docker installed
   - SSH access
   - Root or sudo privileges
   - Port 80 and 443 open for web traffic

2. **Domain**: A domain name pointing to your server's IP address

3. **Docker Hub Account**: For storing your container images

## Environment Variables

Before deploying, set these environment variables on your local machine:

```bash
# Docker Hub credentials
export DOCKER_HUB_TOKEN="your_docker_hub_personal_access_token"

# Application secrets
export SECRET_KEY="your_secret_key_here"
export QDRANT_API_KEY="your_qdrant_api_key"
export QDRANT_URL="your_qdrant_url"
export FIREBASE_CREDENTIALS="your_firebase_credentials_json"
export TOGETHER_API_KEY="your_together_ai_api_key"
export REDIS_URL="your_redis_connection_string"

# Payment services
export PAYPAL_CLIENT_ID="your_paypal_client_id"
export PAYPAL_CLIENT_SECRET="your_paypal_client_secret"
export STRIPE_SECRET_KEY="your_stripe_secret_key"
export STRIPE_PUBLISHABLE_KEY="your_stripe_publishable_key"

# Email service
export EMAIL_PASSWORD="your_email_password"
export EMAIL_USER="your_email_address"
```

## Configuration

1. **Update config/deploy.yml**:
   - Replace `YOUR_SERVER_IP_HERE` with your server's IP address
   - Replace `YOUR_DOMAIN_HERE` with your domain name

## Deployment Commands

1. **Setup (first time only)**:
   ```bash
   kamal setup
   ```

2. **Deploy**:
   ```bash
   kamal deploy
   ```

3. **Check status**:
   ```bash
   kamal app details
   ```

4. **View logs**:
   ```bash
   kamal app logs
   ```

5. **Restart application**:
   ```bash
   kamal app restart
   ```

6. **Execute commands in container**:
   ```bash
   kamal app exec "python -c 'print(\"Hello from container\")'"
   ```

## Useful Commands

- **Build and push image only**: `kamal build push`
- **SSH into server**: `kamal app exec --interactive bash`
- **Update environment variables**: `kamal env push`
- **Remove deployment**: `kamal app remove`

## Troubleshooting

1. **Health check failing**: Check logs with `kamal app logs`
2. **Container not starting**: Verify environment variables are set
3. **SSL issues**: Ensure domain is pointing to your server
4. **Build failures**: Check Dockerfile and dependencies

## SSL Certificate

Kamal automatically handles Let's Encrypt SSL certificates when you configure:
- `proxy.ssl: true`
- `proxy.host: your-domain.com`

The certificate will be automatically renewed.

## Monitoring

Access your application at: `https://your-domain.com`
Health check endpoint: `https://your-domain.com/health`

## Scaling

To add more servers, update the `servers.web` section in `config/deploy.yml`:

```yaml
servers:
  web:
    - 192.168.1.10
    - 192.168.1.11
```

Then run `kamal deploy` to deploy to all servers. 