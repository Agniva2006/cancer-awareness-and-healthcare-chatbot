# COMPLETE AWS DEPLOYMENT GUIDE
## Cancer Awareness Chatbot — Full Production Stack

> Written for THIS repo: FastAPI + TF-IDF/hybrid RAG + Groq + PostgreSQL/pgvector
> + Redis + Stripe + vanilla-JS frontend. Assumes Phases 1–5 are code-complete
> (they are) and that Docker builds locally (`docker compose build api`).

---

## WHY RENDER FAILED (read first)

Render free tier = **512 MB RAM**. Your API container needs **~1.5–2.2 GB**:

| Component | RSS |
|---|---|
| Python + FastAPI + SQLAlchemy | ~150 MB |
| sentence-transformers (PyTorch, all-MiniLM-L6-v2) | **~900–1,400 MB** |
| TF-IDF + BM25 in-memory index (80 docs, cheap) | ~50 MB |
| Uvicorn + requests | ~100 MB |

**Two-part fix on AWS (do BOTH):**

1. **RIGHT-SIZE the box**: use a 2–4 GB instance (not 512 MB).
2. **MEMORY OPTIMIZATION (do this regardless)**: the model is loaded at
   startup in `rag.py` AND `seed_knowledge.py`, but embeddings for the 80
   static JSON docs are only needed once. Precompute them and skip the model
   load at runtime:

   ```
   scripts/compute_embeddings.py  →  data/embeddings.json  (title→vector)
   rag.py loads the matrix from file; loads SentenceTransformer ONLY if
   the file is missing AND admin has added new docs via DB.
   ```
   That single change drops runtime RSS to **~350–500 MB** and makes even
   small instances viable. (Implementation note for me/you later: keep the
   dense path behind `EMBEDDINGS_FILE` env; fall back to sparse-only when
   absent — the RRF fusion already handles a missing list.)

---

## ARCHITECTURE (what we are building)

```
                        ┌─────────────┐
   Users ──HTTPS──▶ Route53 ──▶ CloudFront (optional CDN) ─┐
                        │                                   │
                        ▼                                   ▼
                 ┌──────────────┐                 ┌──────────────────┐
                 │ ALB (HTTPS)  │────▶ EC2 t3.small (Docker)       │
                 │ :443→:8000   │      ├─ api container (FastAPI)  │
                 └──────────────┘      ├─ redis container          │
                        │              └─ (db is RDS, not local)    │
                        ▼                                           │
                 ┌──────────────────────────────┐                   │
                 │ RDS PostgreSQL 16 + pgvector │◀──────────────────┘
                 │  (private subnet)            │
                 └──────────────────────────────┘
   S3 (backups)  ·  S3/CloudFront (frontend static site)  ·  SES (emails)
   Secrets Manager (keys)  ·  GitHub Actions (CI/CD)  ·  CloudWatch (logs)
```

**Cost estimate (monthly, us-east-1, on-demand):**

| Resource | Type | Cost |
|---|---|---|
| EC2 | t3.small (2 GB) | ~$15 |
| — or — | t3.micro (1 GB) w/ precomputed embeddings | ~$7.5 (free 12 mo w/ free tier) |
| RDS | db.t4g.micro (1 GB), single-AZ | ~$12 |
| ALB | 1 LCU-ish | ~$18 |
| S3 | backups + static site | <$2 |
| Data transfer | ~10 GB | <$1 |
| **Total** | | **~$35–45/mo** (or ~$25 with free-tier/years) |

**Cheaper alternative (worth knowing):** Lightsail $10/mo (2 GB VPS + managed
Postgres via RDS-lite) or EC2 with SQLite→pg on same box. The guide below uses
the "proper" split, but every step maps 1:1 to Lightsail if you want cheap.

---

## PART 0 — PREP (15 min)

0.1 AWS account + billing alerts:
  - Console → Billing → Budgets → Create budget: $30/mo, alert at 80%.
0.2 IAM user for CLI (or use root MFA + console; CLI preferred for CI):
  - IAM → Users → `cancer-chatbot-deployer` → attach `AdministratorAccess`
    (narrow it later) → create access key → save.
0.3 Install on your laptop:
  - AWS CLI v2: `winget install Amazon.AWSCLI` → `aws configure`
  - Session Manager plugin (for shell access without SSH keys):
    `winget install Amazon.SessionManagerPlugin`
0.4 Choose a region close to your users, e.g. `ap-south-1` (India) or
    `us-east-1`. ALL steps below assume you `export/set` once:
  ```powershell
  setx AWS_REGION ap-south-1
  setx AWS_DEFAULT_REGION ap-south-1
  aws sts get-caller-identity   # sanity check
  ```

---

## PART 1 — NETWORK (VPC, subnets, security groups) (20 min)

Use the **default VPC** to keep this simple (it has 2+ AZs already).

1.1 Get your default VPC id:
    `aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text`
    → save as `VPC_ID`. Also list subnets:
    `aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC_ID --query "Subnets[*].[SubnetId,AvailabilityZone]" --output table`
    → pick two subnets in **different AZs** → `SUBNET_A`, `SUBNET_B`.

1.2 **Security groups (3):**

    sg-chatbot-alb — inbound: 80, 443 from 0.0.0.0/0
    aws ec2 create-security-group --group-name sg-chatbot-alb --description "ALB" --vpc-id $VPC_ID

    sg-chatbot-ec2 — inbound: 8000 from sg-chatbot-alb ONLY; 22 from MyIP (or none — use SSM)
    aws ec2 authorize-security-group-ingress --group-id $SG_EC2 --protocol tcp --port 8000 --source-group $SG_ALB

    sg-chatbot-rds — inbound: 5432 from sg-chatbot-ec2 ONLY
    (RDS must NEVER be public. This is the single most important security step.)

1.3 Write the exact commands as you go into a `deploy_notes.md` — you will
    re-run them in CI later.

---

## PART 2 — DATABASE: RDS PostgreSQL 16 + pgvector (25 min)

2.1 Create the DB (CLI shown; console works too):
    aws rds create-db-instance \
      --db-instance-identifier cancer-chatbot-db \
      --db-instance-class db.t4g.micro \
      --engine postgres --engine-version 16.4 \
      --master-username chatbotadmin \
      --master-user-password '<STRONG-PASSWORD>' \
      --allocated-storage 20 --storage-type gp3 \
      --vpc-security-group-ids $SG_RDS \
      --db-subnet-group-name default \
      --no-publicly-accessible \
      --backup-retention-period 7 \
      --preferred-backup-window 03:00-04:00 \
      --deletion-protection

    KEY FLAGS you must not skip:
      --no-publicly-accessible   → private only
      --backup-retention-period 7 → automatic daily backups (roadmap §5.6)
      --deletion-protection       → nobody can `rm` your DB by accident

2.2 Wait: `aws rds wait db-instance-available --db-instance-identifier cancer-chatbot-db`
    (~5–10 min). Get endpoint:
    aws rds describe-db-instances --db-instance-identifier cancer-chatbot-db \
      --query "DBInstances[0].Endpoint.Address" --output text

2.3 **Enable pgvector** (RDS supports it, must be turned on):
    Connect from your EC2 (next part) or any client in the SG, then:
    CREATE EXTENSION IF NOT EXISTS vector;
    (Verify: `SELECT extname FROM pg_extension;` → vector)

2.4 Note the full URL for Secrets Manager (Part 5):
    postgresql://chatbotadmin:<PASSWORD>@<endpoint>:5432/postgres

2.5 **Backups — test the restore (roadmap: "a backup you've never restored
    is not a backup")**:
    aws rds create-db-snapshot --db-instance-identifier cancer-chatbot-db \
      --db-snapshot-identifier smoke-test-snap
    Restore to a temp instance once, verify tables exist, then delete the
    temp instance. Do this drill again after real data exists.

---

## PART 3 — EC2 (the app server) (30 min)

3.1 Create an IAM role for the instance (SSM access + S3 backup writes):
    - IAM → Roles → Create role → EC2 → policies:
        AmazonSSMManagedInstanceCore
        S3 policy limited to your backup bucket (Part 7)

3.2 Launch (or use console; t3.small = 2 GB RAM; t3.micro only works with
    the precomputed-embeddings optimization):
    aws ec2 run-instances \
      --image-id ami-0abcdef1234567890 \        # Amazon Linux 2023 (look up current)
      --instance-type t3.small \
      --key-name my-keypair \                    # create one first (or skip, use SSM)
      --security-group-ids $SG_EC2 \
      --subnet-id $SUBNET_A \
      --iam-instance-profile Name=cancer-chatbot-ec2-role \
      --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":30,"VolumeType":"gp3"}}]'

    30 GB disk: Docker images + model weights need headroom.

3.3 First-boot setup (via SSM Session Manager — no SSH keys needed):
    sudo dnf update -y
    sudo dnf install -y docker git
    sudo systemctl enable --now docker
    sudo usermod -aG docker ec2-user    # re-login after
    # Docker Compose v2:
    sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
      -o /usr/local/lib/docker/cli-plugins/docker-compose && sudo chmod +x $_

3.4 Get code onto the box — pick ONE:
    A) git clone https://github.com/<you>/cancer-awareness-and-healthcare-chatbot.git
       (make the repo private; secrets come from env, never from git)
    B) GitHub Actions deploys it (Part 9) — preferred for the long run.

3.5 On the box, create `/home/ec2-user/app/.env` (NEVER in git):
    DATABASE_URL=postgresql://...@<rds-endpoint>:5432/postgres
    GROQ_API_KEY=<rotated key>
    JWT_SECRET=<fresh 64-char random — rotate from the exposed one!>
    STRIPE_SECRET_KEY=sk_test_...      (rotate; live keys only after KYC)
    STRIPE_WEBHOOK_SECRET=whsec_...
    STRIPE_PRICE_PRO=price_...
    STRIPE_PRICE_CLINIC=price_...
    BILLING_PROVIDER=stripe
    FREE_PLAN_QUOTA=20
    REDIS_HOST=redis                   (the compose service name)
    REDIS_PORT=6379
    ALLOWED_ORIGINS=https://yourdomain.com,https://dxxxx.cloudfront.net,http://localhost:5501
    APP_BASE_URL=https://yourdomain.com
    LOG_FORMAT=json
    ENVIRONMENT=production
    SENTRY_DSN=                        (optional)
    chmod 600 .env

3.6 **Edit `docker-compose.yml` for prod (on the server)**: remove the local
    `db:` service (RDS replaces it) and keep only `api:` + `redis:`.
    Keep `restart: unless-stopped`.

---

## PART 4 — REDIS (10 min)

You already have it in compose (redis:7-alpine) running on the same EC2 —
**that is correct and enough** for single-instance:
  - rate-limit counters shared across uvicorn workers
  - `/health/ready` checks it

For multi-instance scaling later, migrate to **ElastiCache**:
  aws elasticache create-cache-cluster --cache-cluster-id chatbot-redis \
    --engine redis --cache-node-type cache.t3.micro --num-cache-nodes 1 \
    --security-group-ids $SG_REDIS
  → REDIS_HOST=<cluster-endpoint>, REDIS_PORT=6379, delete the compose service.

---

## PART 5 — SECRETS + EMAILS (15 min)

5.1 Secrets Manager (best practice — EC2 reads at boot; optional but proper):
    aws secretsmanager create-secret --name cancer-chatbot/prod \
      --secret-string file://prod-secrets.json
    Attach an IAM policy to the EC2 role allowing
    `secretsmanager:GetSecretValue` on that ARN.
    (MVP shortcut: plain `.env` on the box with 600 perms is acceptable;
    Secrets Manager is the "real product" answer.)

5.2 Email (verification + password reset) — **Amazon SES** is the cheap
    native option:
    - SES → Identities → verify your domain (add the DKIM CNAMEs to DNS)
    - Request **production access** (sandbox removal form; usually <1 day)
    - In `app/services/email.py`, implement an SES provider:
      boto3.client("sesv2").send_email(...) behind the existing
      EmailProvider interface — ConsoleEmailProvider stays as dev fallback.
    - Env: EMAIL_PROVIDER=ses, EMAIL_FROM=noreply@yourdomain.com
    (Alternative: keep Brevo/Resend — works from EC2 with zero AWS wiring.)

---

## PART 6 — RUNNING THE APP (first deploy) (20 min)

6.1 On the EC2, in the repo:
    docker compose build
    docker compose up -d api redis
6.2 Migrate + seed (ONE TIME, and after every schema change):
    docker compose exec api alembic upgrade head
    docker compose exec api python scripts/seed_knowledge.py
    docker compose exec api python scripts/seed_plans.py
6.3 Verify ON THE BOX:
    curl -s localhost:8000/health
    curl -s localhost:8000/health/ready
    → {"status":"ready","database":"ok","redis":"ok","llm":"configured"}
6.4 Run the smoke test with the public ALB URL once Part 8 is done:
    python scripts/smoke_test.py   (point BASE at https://yourdomain.com)

---

## PART 7 — S3 (backups + frontend) (20 min)

7.1 Backup bucket:
    aws s3 mb s3://cancer-chatbot-backups-<random> 
    Lifecycle rule: expire backups older than 30 days.
    Nightly pg_dump cron ON the EC2 (crontab -e):
      0 3 * * * docker exec cancer_chatbot_db pg_dump ... | gzip | aws s3 cp - s3://bucket/$(date +\%F).sql.gz
      (or pg_dump directly at the RDS endpoint from the EC2)
    AND a restore drill monthly — download, restore to a snapshot DB, verify.

7.2 Frontend static site (your vanilla JS SPA):
    aws s3 mb s3://cancer-chatbot-site
    aws s3 sync frontend/ s3://cancer-chatbot-site --delete
    Enable static hosting OR (better) CloudFront in front of it:
    - CloudFront → Origin: the S3 bucket (OAC enabled) → default doc index.html
    - SPA fallback: CloudFront function that rewrites 403/404 → /index.html
    - Note the https://dxxxx.cloudfront.net URL → add to ALLOWED_ORIGINS.
    IMPORTANT: in `frontend/script.js`, API_URL must be your HTTPS API domain
    (not localhost) — make it read a `config.js` or bake at deploy time.

---

## PART 8 — ALB + HTTPS + DOMAIN (30 min)

8.1 Target group (port 8000) → register the EC2 instance.
8.2 Application Load Balancer:
    - internet-facing, subnets A + B, SG = sg-chatbot-alb
    - HTTP :80 → redirect to HTTPS
    - HTTPS :443 → target group
8.3 Certificate (ACM — free):
    - Request a public cert for yourdomain.com (+ www)
    - Validate via DNS CNAME records ACM gives you
8.4 Route 53: A-ALIAS record yourdomain.com → the ALB.
8.5 Enforce HTTPS end-to-end. The API container itself stays plain HTTP
    (8000) inside the private network — standard practice.

---

## PART 9 — CI/CD WITH GITHUB ACTIONS (30 min)

`.github/workflows/deploy-aws.yml`:

```yaml
name: Deploy (AWS EC2)
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy over SSM
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: ap-south-1
        run: |
          aws ssm send-command \
            --instance-ids i-0xxxx \
            --document-name AWS-RunShellScript \
            --parameters commands='[
              "cd /home/ec2-user/app/cancer-awareness-and-healthcare-chatbot",
              "git pull --ff-only",
              "docker compose build api",
              "docker compose up -d api redis",
              "docker compose exec -T api alembic upgrade head"
            ]' --output text --query "Command.CommandId"
      - name: Health gate
        run: |
          sleep 60
          code=$(curl -s -o /dev/null -w "%{http_code}" https://yourdomain.com/health/ready)
          [ "$code" = "200" ] || (echo "NOT READY ($code)" && exit 1)
```

Repo secrets to add: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
(deployer IAM user from Part 0; NOT your root keys).
Branch rule: `main` deploys; feature branches only run CI (your ci.yml
already does lint+pytest+build).

---

## PART 10 — OBSERVABILITY & HARDENING (15 min)

- **CloudWatch agent** on EC2 → ship app logs (your LOG_FORMAT=json makes
  them queryable) + memory/disk metrics. ALARM on:
  - MemUsedPercent > 85% (the Render lesson)
  - StatusCheckFailed on the instance
  - ALB 5xx rate > 5%
- **Sentry**: set SENTRY_DSN on the box → stack traces with request context.
- **SG audit**: RDS SG allows 5432 only from sg-chatbot-ec2. Never 0.0.0.0/0.
- **Rotate the three exposed keys** (Groq, NVIDIA, Stripe) — still pending!
- **System updates**: `dnf automatic` or weekly manual patch window.

---

## PART 11 — GO-LIVE CHECKLIST

[ ] /health/ready = 200 with all "ok" via HTTPS on your real domain
[ ] alembic + both seed scripts ran against RDS; pgvector extension enabled
[ ] Register → login → /ask → sources visible E2E through the real domain
[ ] Stripe webhook endpoint added in dashboard → test purchase in test mode
      → subscription activates via webhook (NOT the success redirect)
[ ] Restore drill completed once for RDS snapshot + one S3 dump
[ ] CloudWatch alarm test (stop the api container, watch the alert fire)
[ ] ALLOWED_ORIGINS contains ONLY your real domains (no localhost in prod)
[ ] JWT_SECRET is fresh (rotated) and >= 32 chars
[ ] .env chmod 600, not in git; Secrets Manager migration scheduled
[ ] Sentry receives a test exception
[ ] Billing alarm active

---

## TROUBLESHOOTING (the hits you'll actually take)

| Symptom | Cause | Fix |
|---|---|---|
| api container restart-loops, OOM | model load on small instance | precompute embeddings (top of doc); t3.small minimum |
| /health/ready: database not ok | SG misconfig | RDS SG must allow 5432 from sg-chatbot-ec2 |
| "no pgvector" on migrate | extension not created | CREATE EXTENSION vector; on the RDS DB |
| 429 on register in prod tests | Redis counters shared | flushdb before load tests |
| CORS errors from the site | ALLOWED_ORIGINS missing the CloudFront domain | add exact origin, no trailing slash |
| Stripe webhook 400 | wrong whsec / not HTTPS | webhook secret must match dashboard endpoint |
| SES goes to spam | domain not verified / no DKIM | complete domain identity + DKIM before volume sends |
| Disk fills on EC2 | Docker build cache | `docker system prune -af` monthly; 30 GB volume |

---

## ORDER-OF-OPERATIONS SUMMARY (what to do, in order)

1. Billing alert → IAM deployer → AWS CLI
2. Default VPC → 3 security groups
3. RDS Postgres 16 (private, backups on) → CREATE EXTENSION vector
4. EC2 t3.small (SSM role) → docker + compose installed
5. .env on box (rotated secrets!) → compose WITHOUT local db
6. First build → migrate → seed → /health/ready green
7. S3 backup bucket + cron; S3/CloudFront static site
8. ALB + ACM cert + Route 53
9. GitHub Actions SSM deploy + health gate
10. CloudWatch alarms + Sentry + key rotation + restore drill
11. Go-live checklist

— END OF GUIDE —
