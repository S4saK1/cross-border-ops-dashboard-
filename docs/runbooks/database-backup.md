# Database Backup Runbook

## Overview
This runbook describes how to backup and restore the SQLite database for the Bilingual CMS. The backup system includes automated daily backups, retention policies, and verification procedures.

## Backup Process

### Manual Backup
To manually trigger a backup:

```bash
bash scripts/backup.sh
```

### Automated Backup
The backup script is configured to run daily via cron in the production environment.
Location of backups: `/app/backups`

### Backup Features
- **Timestamped backups**: Each backup includes timestamp in filename
- **Retention policy**: Automatically deletes backups older than 7 days
- **Logging**: All backup operations are logged to `/app/backups/backup.log`
- **Verification**: Backup files are verified after creation
- **Error handling**: Script exits on errors with proper logging

### Backup File Naming
Format: `bilingual_cms_YYYYMMDD_HHMMSS.db`
Example: `bilingual_cms_20260723_143022.db`

## Restore Process

### Step 1: Stop the application
```bash
docker compose down
```

### Step 2: Identify the backup file
```bash
# List available backups
ls -F /app/backups/bilingual_cms_*.db

# Check backup details
ls -lh /app/backups/bilingual_cms_*.db

# View backup log
cat /app/backups/backup.log
```

### Step 3: Verify backup integrity
```bash
# Check if backup file is valid SQLite
docker compose exec -T backend python -c "
import sqlite3
try:
    conn = sqlite3.connect('/app/backups/BACKUP_FILE.db')
    conn.execute('SELECT count(*) FROM sqlite_master')
    print('Backup file is valid')
    conn.close()
except Exception as e:
    print(f'Backup file is invalid: {e}')
"
```

### Step 4: Restore the database
```bash
# Create a backup of current database (just in case)
cp ./data/runtime/bilingual_cms.db ./data/runtime/bilingual_cms.db.backup

# Restore from backup
cp /app/backups/bilingual_cms_YYYYMMDD_HHMMSS.db ./data/runtime/bilingual_cms.db
```

### Step 5: Start the application
```bash
docker compose up -d
```

### Step 6: Verify restoration
```bash
# Check application logs
docker compose logs -f backend

# Test health endpoint
curl http://localhost:8000/health

# Test basic functionality
curl http://localhost:8000/api/v1/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"admin"}'
```

## Backup Management

### Check backup status
```bash
# View backup directory
ls -lh /app/backups/

# Check backup log for recent activity
tail -20 /app/backups/backup.log

# Count current backups
find /app/backups -name "bilingual_cms_*.db" -type f | wc -l
```

### Manual cleanup
```bash
# Remove backups older than 3 days
find /app/backups -name "bilingual_cms_*.db" -type f -mtime +3 -delete

# Remove all backups (use with caution!)
find /app/backups -name "bilingual_cms_*.db" -type f -delete
```

### Backup to external storage
For production environments, consider backing up to external storage:

```bash
# Example: Backup to S3
aws s3 cp /app/backups/bilingual_cms_YYYYMMDD_HHMMSS.db s3://your-bucket/backups/

# Example: Backup to NFS mount
cp /app/backups/bilingual_cms_YYYYMMDD_HHMMSS.db /mnt/nfs/backups/
```

## Monitoring and Alerts

### Backup monitoring
- Check backup log regularly: `tail -f /app/backups/backup.log`
- Monitor backup directory size
- Set up alerts for failed backups

### Health checks
The application includes enhanced health checks that verify database connectivity:
- **Endpoint**: `GET /health`
- **Response**: Includes database connection status
- **Monitoring**: Can be integrated with Prometheus

## Troubleshooting

### Issue: Backup fails with permission error
**Solution**:
```bash
# Check directory permissions
ls -la /app/backups/

# Fix permissions if needed
chmod 755 /app/backups/
```

### Issue: Database file is locked
**Solution**:
```bash
# Stop the application first
docker compose down

# Then run backup
bash scripts/backup.sh

# Restart application
docker compose up -d
```

### Issue: Backup file is corrupted
**Solution**:
1. Check backup log for errors
2. Try restoring from an older backup
3. If no good backups exist, consider point-in-time recovery

## Disaster Recovery

### Recovery Point Objective (RPO)
- **Daily backups**: RPO = 24 hours
- **Recommended**: Implement more frequent backups for critical data

### Recovery Time Objective (RTO)
- **Target**: < 1 hour
- **Process**: Stop app → Restore DB → Start app → Verify

### Emergency procedures
1. **Database corruption**: Restore from latest backup
2. **Server failure**: Restore from off-site backup
3. **Data loss**: Contact development team for point-in-time recovery

## Security Considerations

### Backup security
- Backup files contain sensitive data
- Store backups in secure locations
- Encrypt backups for off-site storage
- Implement access controls

### Backup retention
- Default: 7 days retention
- Production: Consider 30 days retention
- Compliance: Follow data retention policies

## Related Documentation
- [Deployment Checklist](../deployment-checklist.md)
- [Monitoring Setup](monitoring-setup.md)
- [SRE Assessment Report](../../deliverables/gstack/sre-assessment.md)

---
**Document Version**: v2.0  
**Last Updated**: 2026-07-23  
**Maintainer**: Rex (SRE Engineer)
