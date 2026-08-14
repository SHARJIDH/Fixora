<div align="center">

# Fixora

### Autonomous AI-Powered Cloud Agent for Code Generation, Validation & Pull Request Automation

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Next.js 14](https://img.shields.io/badge/Next.js_14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazonwebservices&logoColor=white)](https://aws.amazon.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

An **autonomous, LLM-powered DevOps agent** that monitors GitHub issues and pull requests, analyzes codebases with AI, generates intelligent code fixes, validates changes in isolated cloud sandboxes, and opens pull requests — all without human intervention.

**Built for developers, SREs, and platform engineers who want AI-driven automation across their software delivery lifecycle.**

[Features](#features) · [Architecture](#architecture) · [Quick Start](#quick-start) · [How It Works](#how-it-works) · [Tech Stack](#tech-stack) · [Roadmap](#roadmap)

</div>

---

## Why Fixora?

Traditional CI/CD pipelines execute predefined steps. **Fixora is an intelligent agent** — it reads issues, understands intent, reasons about code, generates targeted fixes, validates them in sandboxed environments, and delivers production-ready pull requests. It bridges the gap between issue tracking and code delivery with zero manual intervention.

| Traditional Automation | Fixora |
|---|---|
| Runs pre-written scripts | Reasons about code with LLMs |
| Requires manual code changes | Generates code autonomously |
| No validation before PR | Validates in isolated sandboxes |
| Single CI provider | Multi-cloud execution (Azure ACI, AWS Fargate, Docker) |
| One model, one provider | Multi-LLM support (Claude, GPT-4, Groq) |

---

## Features

### AI-Powered Code Intelligence
- **Multi-LLM Support** — Claude 3.5 Sonnet (via OpenRouter), GPT-4, Groq models with per-user model selection
- **Agentic Code Analysis** — Multi-turn AI reasoning with function calling for complex code changes
- **Smart File Selection** — Intelligently identifies relevant files from the entire codebase
- **Custom Rules Engine** — Define project-specific coding rules the AI follows during generation
- **Codebase Memory** — Persistent context storage per repository for improved AI decision-making

### Autonomous Code Validation & Sandboxing
- **Azure ACI Sandbox** — Isolated on-demand containers for low-cost cloud validation
- **AWS Fargate Fallback (Optional)** — Legacy/optional serverless fallback if explicitly enabled
- **Local Docker Sandbox** — Container-based validation for development environments
- **Full Stack Detection** — Auto-detects Python (pip/poetry), Node.js (npm/yarn/pnpm), Java, Go, Rust
- **Validation Pipeline** — Dependency installation, test execution, type checking (TypeScript/MyPy), linting, security scanning
- **Graceful Fallback** — Azure ACI → AWS Fargate (optional) → Docker → Local execution chain

### GitHub Integration & Automation
- **Webhook-Driven** — Real-time event processing for issue comments and PR feedback
- **Automated PR Creation** — Branch creation, code commits, and pull request generation
- **GitHub App Support** — OAuth-based authentication with installation tracking
- **Webhook Signature Verification** — Secure webhook validation
- **Rate Limit Handling** — Automatic backoff and retry logic

### Real-Time Dashboard & Monitoring
- **Live Job Streaming** — Socket.IO-powered real-time status updates and log streaming
- **Job History & Analytics** — Track all automation jobs with filtering and detailed views
- **Repository Management** — Connect repos, manage webhooks, view issues per repository
- **Code Diff Viewer** — Visual diff display for AI-generated changes
- **User Settings** — Per-user AI model selection, custom rules, account management

### Enterprise-Ready
- **OAuth Authentication** — GitHub and Google OAuth via Better-Auth
- **Subscription Management** — Built-in payment processing with Dodo Payments
- **PostgreSQL Support** — Production-grade database with SQLAlchemy ORM
- **Redis Job Queue** — Async task processing with Redis message queue
- **Security Scanning** — Built-in vulnerability detection for generated code

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Fixora Platform                            │
├──────────────────────────┬──────────────────────────────────────────┤
│                          │                                          │
│   Frontend (Next.js 14)  │         Backend (Flask + Python)         │
│   ┌──────────────────┐   │   ┌──────────────────────────────────┐  │
│   │ Dashboard UI      │   │   │ Webhook Handler                  │  │
│   │ Job Monitor       │   │   │ AI Service (OpenRouter / Groq)   │  │
│   │ Repo Manager      │   │   │ GitHub Service (PyGithub)        │  │
│   │ Settings Panel    │   │   │ PR Service                       │  │
│   │ Code Diff Viewer  │   │   │ Code Execution Service           │  │
│   │ OAuth Flow        │◄──┼──►│ Security Scanner                 │  │
│   └──────────────────┘   │   │ Database Layer (SQLAlchemy)       │  │
│                          │   └────────────┬─────────────────────┘  │
│   Real-time: Socket.IO   │                │                        │
│                          │   ┌────────────▼─────────────────────┐  │
│                          │   │     Execution Sandboxes           │  │
│                          │   │  ┌───────┐ ┌───────┐ ┌────────┐ ┌───────┐ │  │
│                          │   │  │Azure  │ │AWS    │ │Docker  │ │Local  │ │  │
│                          │   │  │ACI    │ │Fargate│ │Container│ │Exec  │ │  │
│                          │   │  └───────┘ └───────┘ └────────┘ └───────┘ │  │
│                          │   └──────────────────────────────────┘  │
├──────────────────────────┴──────────────────────────────────────────┤
│  External Services: GitHub API · OpenRouter · Groq · Azure (ACI/   │
│  Storage/ACR) · AWS (ECS/S3/CloudWatch/ECR) · Redis · PostgreSQL   │
│  · Dodo Payments                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
GitHub Issue/PR Comment
        │
        ▼
  Webhook Handler ──► Verify Signature
        │
        ▼
  Queue Job (Redis)
        │
        ▼
  Fetch Codebase ──► Smart File Selection
        │
        ▼
  AI Analysis ──► Multi-turn LLM Reasoning (Claude / GPT-4 / Groq)
        │
        ▼
  Generate Code Changes ──► Function Calling (replace, insert, edit)
        │
        ▼
  Create Branch + Commit Changes
        │
        ▼
      Validate in Sandbox ──► Azure ACI │ AWS Fargate │ Docker │ Local
        │
        ▼
  Create Pull Request
        │
        ▼
  Stream Results ──► Socket.IO ──► Dashboard
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (optional, for production job queue)
- Docker (optional, for local sandboxing)

### 1. Clone & Install

```bash
git clone https://github.com/your-username/fixora.git
cd fixora

# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Configure Environment

```bash
# Backend (.env)
OPENROUTER_API_KEY=your_openrouter_key
GITHUB_TOKEN=your_github_pat
GROQ_API_KEY=your_groq_key          # Optional
REDIS_URL=redis://localhost:6379     # Optional
DATABASE_URL=postgresql://...        # Optional, defaults to SQLite

# Azure Sandbox (Optional, recommended low-cost defaults)
USE_AZURE_SANDBOX=false
AZURE_EXECUTION_MODE=aci
AZURE_ACI_CPU=0.5
AZURE_ACI_MEMORY_GB=1
AZURE_ACI_TIMEOUT_SECONDS=300
AZURE_ENABLE_LOG_ANALYTICS=false

# REQUIRED when provisioning Azure resources
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_SUBSCRIPTION_ID=...
AZURE_RESOURCE_GROUP=fixora-rg
AZURE_LOCATION=centralindia

# Bootstrap Azure resources from repo root
./infrastructure/bootstrap_azure.sh

# Note: script name is bootstrap_azure.sh (not bootstap_azure.sh)

# Enable Azure only when needed for execution runs
export USE_AZURE_SANDBOX=true

# Optional: keep it enabled only for one command
USE_AZURE_SANDBOX=true python backend/app.py

# Turn it off after your Azure validation run
export USE_AZURE_SANDBOX=false

# Verify current sandbox flags
echo "USE_AZURE_SANDBOX=$USE_AZURE_SANDBOX USE_AWS_SANDBOX=$USE_AWS_SANDBOX"

# AWS fallback is not required for Azure mode.
# Only set AWS_* keys if you explicitly enable USE_AWS_SANDBOX=true.
```

### 3. Run

```bash
# Terminal 1 - Backend
cd backend && python app.py

# Terminal 2 - Frontend
cd frontend && npm run dev
```

The dashboard will be available at `http://localhost:3000` and the API at `http://localhost:8000`.

### 4. Connect a Repository

1. Open the dashboard and sign in with GitHub OAuth
2. Navigate to **Repositories** and connect your repos
3. Webhooks are automatically configured via the GitHub App
4. Comment `@fixora fix the login bug` on any issue — the agent takes it from there

---

## How It Works

1. **Trigger** — A user mentions the bot in a GitHub issue or PR comment
2. **Analyze** — The agent fetches the repository structure and relevant files, then uses multi-turn LLM reasoning to understand the problem
3. **Generate** — AI generates targeted code changes using function calling (file edits, replacements, insertions)
4. **Validate** — Changes are tested in an isolated sandbox (Azure ACI by default, AWS Fargate optional fallback, Docker/local fallback) — running tests, type checks, linting, and security scans
5. **Deliver** — A pull request is created with the validated changes, complete with a detailed description
6. **Monitor** — The entire pipeline streams real-time updates to the dashboard via Socket.IO

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, TypeScript, React, Tailwind CSS, Shadcn UI, Socket.IO Client, React Flow |
| **Backend** | Python 3.11, Flask, Flask-SocketIO, SQLAlchemy, Celery |
| **AI/LLM** | OpenRouter (Claude 3.5 Sonnet), Groq, OpenAI GPT-4, Function Calling |
| **Cloud** | Azure ACI, Azure Storage, Azure Container Registry, AWS ECS Fargate, S3, ECR, CloudWatch, IAM, VPC |
| **Database** | PostgreSQL (production), SQLite (development) |
| **Queue** | Redis |
| **Auth** | Better-Auth (GitHub OAuth, Google OAuth) |
| **Payments** | Dodo Payments |
| **Containerization** | Docker, Azure ACI, AWS Fargate |
| **CI/CD** | GitHub Actions |

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/webhook` | POST | GitHub webhook handler |
| `/api/config` | POST | Save API configuration |
| `/api/config` | GET | Check credential status |
| `/api/jobs` | GET | List job history |
| `/api/jobs/<id>` | GET | Get job details |
| `/health` | GET | Health check |

---

## Guardrails & Evals

Fixora includes lightweight guardrails to reduce risky behavior in manual prompts and AI-issued shell commands.

### Guardrails Included

- Manual prompt guardrails:
      - Reject empty prompts
      - Reject oversized prompts (configurable with `MAX_MANUAL_PROMPT_CHARS`)
      - Block obvious secret-exfiltration intent patterns
- Exec command guardrails:
      - Reject oversized commands (configurable with `MAX_EXEC_COMMAND_CHARS`)
      - Block destructive/system-level patterns (`rm -rf /`, `mkfs`, `shutdown`, etc.)
      - Block environment/secret leakage patterns (`printenv`, metadata endpoint access)
- Log safety:
      - Redacts common token/key patterns before previews are logged

### Run Tests

```bash
cd backend
pytest tests/test_guardrails.py -q
```

### Run Evals

```bash
cd backend
python evals/run_guardrail_evals.py
```

The eval script exits non-zero if any expected allow/block behavior fails.

---

## Supported Languages & Frameworks

| Language | Package Managers | Test Frameworks | Type Checking |
|---|---|---|---|
| **Python** | pip, poetry | pytest, unittest | MyPy |
| **Node.js** | npm, yarn, pnpm | jest, mocha, vitest | TypeScript (tsc) |
| **Java** | maven, gradle | JUnit | — |
| **Go** | go modules | go test | — |
| **Rust** | cargo | cargo test | — |

---

## Roadmap

- [ ] Expand multi-cloud sandbox support (Container Apps, GCP Cloud Run)
- [ ] Kubernetes-native execution mode
- [ ] Slack / Discord notifications
- [ ] Jira and Linear integration
- [ ] Pre-PR approval workflows with human-in-the-loop
- [ ] Fine-tuned models for domain-specific codebases
- [ ] Plugin system for custom tools and integrations
- [ ] GitLab and Bitbucket support

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with AI, for developers who ship fast.**

</div>

---

## Author

**Kakumanu Ashok Reddy** — Full Stack & Cloud Developer

I built Fixora end-to-end — from the AI agent pipeline and cloud sandbox infrastructure to the real-time dashboard. This project reflects my skills across:

**Backend & Cloud:** Python, Flask, SQLAlchemy, AWS (ECS Fargate, S3, ECR, CloudWatch, IAM, VPC), Docker, Redis, PostgreSQL, REST APIs, WebSockets (Socket.IO)

**Frontend:** Next.js 14, React, TypeScript, Tailwind CSS, Shadcn UI, Real-time UI with Socket.IO

**AI/LLM Integration:** OpenRouter, Groq, OpenAI API, function calling, multi-turn agentic workflows, prompt engineering

**DevOps & Infrastructure:** GitHub Apps & Webhooks, OAuth flows, CI/CD, containerized code execution, sandboxed validation pipelines

**I'm open to work.** If you're hiring for Full Stack, Cloud, AI/LLM, or DevOps roles — I'd love to connect.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ashok_Reddy-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/ashok-reddy-kakumanu-8a3078247)
[![Email](https://img.shields.io/badge/Email-kakumanuashokreddyias2024@gmail.com-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:kakumanuashokreddyias2024@gmail.com)
[![GitHub](https://img.shields.io/badge/GitHub-ashokDevs-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ashokDevs)

<!-- Keywords: ai-agent autonomous-agent cloud-agent devops-automation ai-powered-devops llm-agent
agentic-ai agentic-workflow multi-agent-systems agent-orchestration intelligent-automation
sre site-reliability-engineering incident-response auto-remediation self-healing-infrastructure
cloud-automation cloud-native multi-cloud aws-fargate serverless-automation
ci-cd continuous-integration continuous-deployment infrastructure-automation
code-review pull-request-automation automated-code-review pr-automation code-generation
ai-code-review ai-code-generation autonomous-coding-agent
openai gpt-4 claude anthropic groq large-language-models generative-ai
python nextjs typescript flask react docker kubernetes
devops-tools platform-engineering aiops mlops chatops
workflow-automation task-automation no-code pipeline orchestration
sandbox code-execution code-validation security-scanning
real-time-monitoring observability webhook-automation github-automation
developer-tools software-engineering ai-assistant copilot
production-ready enterprise-grade developer-first -->
