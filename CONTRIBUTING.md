# Contributing to Fixora

Thanks for your interest in contributing to Fixora! Here's how to get started.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/fixora.git
   cd fixora
   ```
3. Set up the development environment:
   ```bash
   # Backend
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Frontend
   cd ../frontend
   npm install
   ```
4. Create a `.env` file in the `backend/` directory using the variables from the README

## Development

- Backend runs on `http://localhost:8000`
- Frontend runs on `http://localhost:3000`

```bash
# Start backend
cd backend && python app.py

# Start frontend (separate terminal)
cd frontend && npm run dev
```

## Making Changes

1. Create a branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Test your changes locally
4. Commit with a clear message:
   ```bash
   git commit -m "feat: add support for X"
   ```
5. Push and open a pull request

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation
- `refactor:` — code refactoring
- `test:` — adding or updating tests
- `chore:` — maintenance tasks

## Pull Requests

- Keep PRs focused on a single change
- Include a description of what changed and why
- Link related issues if applicable
- Make sure existing functionality isn't broken

## Reporting Issues

Use the [issue templates](.github/ISSUE_TEMPLATE/) to report bugs or request features.

## Code Style

- **Python**: Follow PEP 8
- **TypeScript/React**: Follow the existing patterns in the codebase
- **CSS**: Use Tailwind utility classes

## Questions?

Open a [Discussion](https://github.com/ashokDevs/fixora/discussions) if you have questions or need help.
