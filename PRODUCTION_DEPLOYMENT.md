# MediaVault - Production Deployment Guide

## ✅ Prerequisites Complete

- [x] Backend built and tested
- [x] Frontend built (`npm run build`)
- [x] Database schema migrated
- [x] Nginx config created
- [x] SSL certificates ready (wildcard *.orourkes.me)
- [x] Domain registered in Cloudflare (mediavault.orourkes.me)

---

## 🚀 Production Deployment Steps

### Step 1: Verify SSL Certificates

```bash
# Check that wildcard certs exist
ls -lh /home/mercury/projects/domain_certificates/orourkes.me-wildcard.*

# Should see:
# orourkes.me-wildcard.crt
# orourkes.me-wildcard.key
```

**If certificates don't exist,** follow the SSL certificate management skill to get them from pfSense.

### Step 2: Install nginx Configuration

```bash
# Copy nginx config to sites-available
sudo cp /home/mercury/projects/mediavault/nginx-mediavault-production.conf \
  /etc/nginx/sites-available/mediavault.orourkes.me

# Create symlink to enable site
sudo ln -s /etc/nginx/sites-available/mediavault.orourkes.me \
  /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Expected output:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Step 3: Reload nginx

```bash
# Reload nginx to apply new configuration
sudo systemctl reload nginx

# Check nginx status
sudo systemctl status nginx

# Verify site is configured
sudo nginx -T | grep mediavault
```

### Step 4: Install systemd Service for Backend

```bash
# Copy service file
sudo cp /home/mercury/projects/mediavault/mediavault-backend.service \
  /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable mediavault-backend.service

# Start service
sudo systemctl start mediavault-backend.service

# Check status
sudo systemctl status mediavault-backend.service
```

### Step 5: Verify Deployment

```bash
# Check backend is running
curl http://localhost:8007/api/health

# Should return:
# {"status":"healthy","app":"MediaVault","version":"0.1.0","environment":"production"}

# Check HTTPS works
curl -I https://mediavault.orourkes.me

# Should return:
# HTTP/2 200
# strict-transport-security: max-age=31536000; includeSubDomains; preload

# Check frontend loads
curl -I https://mediavault.orourkes.me/

# Should return:
# HTTP/2 200
# content-type: text/html
```

### Step 6: Test in Browser

1. Open https://mediavault.orourkes.me
2. Verify SSL certificate is valid (green lock)
3. Check Dashboard loads
4. Go to Scanner page
5. Run a test scan

---

## 🔧 Service Management

### Start/Stop Services

```bash
# Start backend
sudo systemctl start mediavault-backend

# Stop backend
sudo systemctl stop mediavault-backend

# Restart backend
sudo systemctl restart mediavault-backend

# View logs
sudo journalctl -u mediavault-backend -f

# Reload nginx
sudo systemctl reload nginx
```

### Update Application

```bash
# Backend updates
cd /home/mercury/projects/mediavault/backend
git pull  # or make changes
sudo systemctl restart mediavault-backend

# Frontend updates
cd /home/mercury/projects/mediavault/frontend
npm run build
sudo systemctl reload nginx
```

---

## 📊 Monitoring

### View Logs

```bash
# Backend logs (systemd journal)
sudo journalctl -u mediavault-backend -f

# Nginx access logs
sudo tail -f /var/log/nginx/mediavault-access.log

# Nginx error logs
sudo tail -f /var/log/nginx/mediavault-error.log

# Database logs
docker logs pm-ideas-postgres -f
```

### Check Service Status

```bash
# Backend service
sudo systemctl status mediavault-backend

# Nginx
sudo systemctl status nginx

# Database container
docker ps | grep postgres
```

---

## 🐛 Troubleshooting

### Backend Not Starting

```bash
# Check service status
sudo systemctl status mediavault-backend

# View full logs
sudo journalctl -u mediavault-backend -n 100

# Test backend manually
cd /home/mercury/projects/mediavault/backend
uvicorn app.main:app --host 0.0.0.0 --port 8007

# Common issues:
# - Port 8007 already in use: pkill -f "uvicorn app.main"
# - Database connection failed: Check .env file
# - Python dependencies missing: pip install -r requirements.txt
```

### Frontend Not Loading

```bash
# Check nginx config
sudo nginx -t

# Check nginx is running
sudo systemctl status nginx

# Check frontend files exist
ls -la /home/mercury/projects/mediavault/frontend/dist/

# Rebuild frontend
cd /home/mercury/projects/mediavault/frontend
npm run build
sudo systemctl reload nginx
```

### SSL Certificate Issues

```bash
# Verify certificate files
ls -lh /home/mercury/projects/domain_certificates/

# Test SSL connection
openssl s_client -connect mediavault.orourkes.me:443 -servername mediavault.orourkes.me

# Check certificate expiry
openssl x509 -in /home/mercury/projects/domain_certificates/orourkes.me-wildcard.crt -noout -dates
```

### Database Connection Issues

```bash
# Check database is running
docker ps | grep postgres

# Test connection
psql -U pm_ideas_user -h localhost -p 5433 -d mediavault -c "SELECT COUNT(*) FROM media_files;"

# Check database password in .env
grep DATABASE_URL /home/mercury/projects/mediavault/backend/.env
```

---

## 🔐 Security Checklist

- [x] HTTPS enforced (HTTP redirects to HTTPS)
- [x] SSL certificate valid (Let's Encrypt wildcard)
- [x] Security headers configured (HSTS, X-Frame-Options, etc.)
- [x] Sensitive files blocked (dotfiles)
- [x] Database password in .env (not in code)
- [x] Backend runs as mercury user (not root)
- [ ] Firewall configured (if needed)
- [ ] Rate limiting enabled (optional, for future)
- [ ] User authentication (optional, for future)

---

## 📈 Performance Optimization

### Backend

Already configured:
- 4 uvicorn workers for parallel processing
- Database connection pooling
- Async I/O with FastAPI

### Frontend

Already optimized:
- Production build with minification
- Static asset caching (1 year)
- Gzip compression via nginx

### Database

Current setup:
- Connection pooling enabled
- Indexes on key fields
- Efficient queries

---

## 🔄 Backup Strategy

### Database Backup

```bash
# Manual backup
docker exec pm-ideas-postgres pg_dump -U pm_ideas_user mediavault > mediavault_backup_$(date +%Y%m%d).sql

# Restore backup
docker exec -i pm-ideas-postgres psql -U pm_ideas_user mediavault < mediavault_backup_20251108.sql
```

### Application Backup

```bash
# Backup entire application
cd /home/mercury/projects
tar -czf mediavault_backup_$(date +%Y%m%d).tar.gz mediavault/

# Exclude node_modules and dist
tar -czf mediavault_backup.tar.gz \
  --exclude='node_modules' \
  --exclude='dist' \
  --exclude='__pycache__' \
  mediavault/
```

---

## 📚 Quick Reference

### URLs
- **Production:** https://mediavault.orourkes.me
- **API Docs:** https://mediavault.orourkes.me/docs
- **Health Check:** https://mediavault.orourkes.me/api/health

### Ports
- **Backend:** 8007 (localhost only)
- **Frontend:** Served by nginx (443/80)
- **Database:** 5433 (localhost only)

### File Locations
- **Frontend Build:** `/home/mercury/projects/mediavault/frontend/dist/`
- **Backend Code:** `/home/mercury/projects/mediavault/backend/`
- **nginx Config:** `/etc/nginx/sites-available/mediavault.orourkes.me`
- **systemd Service:** `/etc/systemd/system/mediavault-backend.service`
- **SSL Certs:** `/home/mercury/projects/domain_certificates/`
- **Logs:** `/var/log/nginx/mediavault-*.log`

### Key Commands
```bash
# Restart everything
sudo systemctl restart mediavault-backend
sudo systemctl reload nginx

# View logs
sudo journalctl -u mediavault-backend -f
sudo tail -f /var/log/nginx/mediavault-access.log

# Update frontend
cd frontend && npm run build && sudo systemctl reload nginx

# Test deployment
curl https://mediavault.orourkes.me/api/health
```

---

## ✅ Deployment Checklist

- [ ] SSL certificates verified
- [ ] nginx config installed
- [ ] nginx config tested (`sudo nginx -t`)
- [ ] nginx reloaded
- [ ] systemd service installed
- [ ] systemd service enabled
- [ ] systemd service started
- [ ] Backend health check passed
- [ ] HTTPS loads in browser
- [ ] Frontend displays correctly
- [ ] Can run a scan
- [ ] Can detect duplicates
- [ ] Can review duplicates

---

**Status:** Ready to deploy! Follow the steps above to go live.

**Estimated Time:** 10-15 minutes
