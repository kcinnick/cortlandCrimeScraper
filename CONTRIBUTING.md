# CONTRIBUTING.md - Development Workflow

## Golden Rule: Never Commit to Master

**ALL commits must be made on a feature branch. Master branch is protected for reviewed, tested code only.**

### Required Workflow

```
master (only receives merged PRs)
  ↓
  ├─ feat/new-feature
  │  ├─ Work here
  │  ├─ Commit here
  │  └─ Create PR
  │
  ├─ fix/bug-name
  │  ├─ Work here
  │  ├─ Commit here
  │  └─ Create PR
  │
  ├─ chore/maintenance-task
  │  ├─ Work here
  │  ├─ Commit here
  │  └─ Create PR
  │
  └─ docs/documentation-update
     ├─ Work here
     ├─ Commit here
     └─ Create PR
```

### Branch Naming Convention

Use the following prefixes:

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feat/` | New features | `feat/add-email-notifications` |
| `fix/` | Bug fixes | `fix/openai-compatibility` |
| `docs/` | Documentation | `docs/update-setup-guide` |
| `chore/` | Maintenance, cleanup | `chore/update-dependencies` |
| `refactor/` | Code improvements | `refactor/simplify-scraper-logic` |
| `test/` | Tests | `test/improve-incident-coverage` |
| `style/` | Code style | `style/format-logging-calls` |

### Step-by-Step Workflow

**1. Create a new branch from master:**
```bash
git checkout master
git pull origin master
git checkout -b feat/your-feature-name
```

**2. Make your changes:**
```bash
# Edit files
vim src/file.py

# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add caching to database queries

- Add Redis cache layer
- Reduce query time by 50%
- Add cache invalidation on updates"
```

**3. Keep branch updated:**
```bash
git fetch origin
git rebase origin/master
```

**4. Push to remote:**
```bash
git push origin feat/your-feature-name
```

**5. Create Pull Request:**
- Open GitHub pull request
- Link related issues
- Wait for review
- Make requested changes
- Merge once approved

**6. Cleanup:**
```bash
git checkout master
git pull origin master
git branch -d feat/your-feature-name
git push origin --delete feat/your-feature-name
```

### Commit Message Format

Follow conventional commits:

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Code style (formatting, missing semicolons, etc.)
- `refactor:` - Code refactoring without feature/bug change
- `perf:` - Performance improvement
- `test:` - Test additions or changes
- `chore:` - Build process, dependency updates, etc.

**Example:**
```
fix: resolve openai/httpx compatibility issue

Update openai from 1.3.9 to 1.26.0 and pin httpx to 0.24.1
to resolve TypeError on proxies argument.

Fixes #42

Tests:
- python flask_app/app.py now runs without errors
- pytest passes all existing tests
```

### DO's and DON'Ts

**✅ DO:**
- Always branch from `master`
- Write descriptive commit messages
- Test code before pushing
- Create small, focused pull requests
- Link related issues in PR description
- Keep branches up to date with master
- Squash related commits if appropriate

**❌ DON'T:**
- Commit directly to `master`
- Push without testing locally
- Create massive PRs with many unrelated changes
- Force push to master
- Leave old branches lying around
- Commit to master even for "quick fixes"
- Merge your own PR without review

### Pre-Commit Checklist

Before pushing:
```bash
# 1. Run tests
pytest

# 2. Check code quality
python -m py_compile models/*.py police_fire/**/*.py

# 3. Verify imports work
python -c "from database import get_database_session; print('✓')"

# 4. Review your changes
git diff

# 5. Check commit message
git log -1
```

### Emergency Hotfixes

Even for critical bugs:
1. Create `fix/emergency-hotfix-name` branch
2. Make minimal, focused changes
3. Create PR with urgent flag
4. Request expedited review
5. Test thoroughly before merge

Never bypass the branch → PR → merge workflow.

### Questions?

Refer to:
- AGENTS.md - Project architecture
- SETUP.md - Getting started
- docs/DATABASE_SETUP.md - Database management
- tests/README.md - Testing guide

