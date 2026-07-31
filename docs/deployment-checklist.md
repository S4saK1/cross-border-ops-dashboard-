# Deployment Checklist

## Pre-Deployment
- [ ] **Secrets**: Verify `SECRET_KEY` is set to a strong, unique value in production environment.
- [ ] **CORS**: Verify `ALLOWED_ORIGINS` in `docker-compose.yml` includes only trusted domains.
- [ ] **Backups**: Verify backup script produces a non-empty file in `./backups/` with timestamp matching current date, and exit code is 0.
- [ ] **SSL**: Ensure SSL certificates are valid and configured in Nginx.

## Deployment
- [ ] **Code**: Pull latest changes from main branch.
- [ ] **Build**: Run `docker compose build --no-cache` to ensure fresh images.
- [ ] **Migrations**: If schema changes exist, run migrations (currently handled by `init_db.py` but Alembic is recommended for future).
- [ ] **Start**: Run `docker compose up -d`.
- [ ] **Health Check**: Verify `curl http://localhost:8000/health` returns 200 OK.

## Post-Deployment
- [ ] **Smoke Test**: Login as admin and perform a basic CRUD operation.
- [ ] **Logs**: Monitor logs for 5 minutes (`docker compose logs -f`) to ensure no errors.
- [ ] **Rollback Plan**: Verify you can revert to the previous docker image tag if needed.
