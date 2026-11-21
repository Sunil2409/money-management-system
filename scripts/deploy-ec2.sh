#!/bin/bash
set -euo pipefail

IMAGE_TAG="${1:-latest}"
ECR_REGISTRY="${2:-}"
AWS_REGION="${3:-ap-south-1}"
S3_BUCKET="${4:-money-manager-statements-prod-c22ccadb}"
ECR_REPOSITORY="${5:-money-manager}"

echo "=========================================================="
echo " Starting Money Manager Production Deployment on EC2"
echo " Image Tag: $IMAGE_TAG"
echo " Registry:  $ECR_REGISTRY"
echo " Region:    $AWS_REGION"
echo " S3 Bucket: $S3_BUCKET"
echo "=========================================================="

cd /opt/moneymanager

echo "=== 1. Authenticating Docker to AWS ECR ==="
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "=== 2. Fetching Production Secrets from AWS SSM Parameter Store ==="
POSTGRES_PASSWORD=$(aws ssm get-parameter --name /moneymanager/prod/POSTGRES_PASSWORD --with-decryption --query Parameter.Value --output text --region "$AWS_REGION")
SECRET_KEY=$(aws ssm get-parameter --name /moneymanager/prod/SECRET_KEY --with-decryption --query Parameter.Value --output text --region "$AWS_REGION")
JWT_SECRET_KEY=$(aws ssm get-parameter --name /moneymanager/prod/JWT_SECRET_KEY --with-decryption --query Parameter.Value --output text --region "$AWS_REGION")

echo "=== 3. Writing .env Configuration File ==="
cat << EOF > .env
DEBUG=False
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
ECR_REGISTRY=$ECR_REGISTRY
ECR_REPOSITORY=$ECR_REPOSITORY
IMAGE_TAG=$IMAGE_TAG
AWS_DEFAULT_REGION=$AWS_REGION
AWS_STORAGE_BUCKET_NAME=$S3_BUCKET
ALLOWED_HOSTS=*
EOF
chmod 600 .env

echo "=== 4. Pulling Scanned Images from ECR ==="
docker compose -f docker-compose.prod.yml pull backend celery_worker

echo "=== 5. Starting Database and Redis Dependencies ==="
docker compose -f docker-compose.prod.yml up -d db redis

echo "=== 6. Running Database Migrations ==="
docker compose -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput

echo "=== 7. Collecting Static Assets ==="
docker compose -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput

echo "=== 8. Executing Rolling Container Recreate ==="
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "=== 9. Verifying Service Health via Nginx Reverse Proxy ==="
HEALTHY=0
for i in $(seq 1 15); do
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/api/health/ || true)
  if [ "$HTTP_STATUS" = "200" ]; then
    echo "Deployment healthcheck verified: HTTP 200 OK (attempt $i/15)"
    HEALTHY=1
    break
  fi
  echo "Waiting for service readiness (attempt $i/15, status: $HTTP_STATUS)..."
  sleep 4
done

if [ "$HEALTHY" -ne 1 ]; then
  echo "[FATAL] Production readiness healthcheck failed! Container logs:"
  docker compose -f docker-compose.prod.yml logs --tail=50 backend nginx
  exit 1
fi

echo "=== 10. Pruning Stale Docker Images ==="
docker image prune -af --filter "until=48h" || true

echo "=========================================================="
echo " Deployment Successfully Completed!"
echo "=========================================================="
