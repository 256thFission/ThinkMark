# Publishing ThinkMark to PyPI

This guide covers how to publish ThinkMark to PyPI for distribution.

## Setup Requirements

### 1. PyPI Account Setup
- Create accounts on [PyPI](https://pypi.org) and [Test PyPI](https://test.pypi.org)
- Enable 2FA on both accounts
- Generate API tokens for programmatic access

### 2. GitHub Repository Setup
- Configure GitHub repository settings
- Set up trusted publishing (recommended) or API tokens
- Update repository URLs in `pyproject.toml`

## Publishing Methods

### Method 1: Automated Publishing (Recommended)

#### Via GitHub Releases
1. Create a new release on GitHub
2. Tag format: `v0.2.0` (follows semantic versioning)
3. GitHub Actions will automatically build and publish to PyPI

#### Manual Trigger
```bash
# Trigger workflow manually to publish to Test PyPI
gh workflow run publish.yml -f test_pypi=true

# Trigger workflow manually to publish to PyPI
gh workflow run publish.yml -f test_pypi=false
```

### Method 2: Manual Publishing

#### Build Package Locally
```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Check package
twine check dist/*
```

#### Publish to Test PyPI (Testing)
```bash
# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ thinkmark
```

#### Publish to PyPI (Production)
```bash
# Upload to PyPI
twine upload dist/*
```

## GitHub Actions Configuration

### Trusted Publishing Setup (Recommended)
1. Go to PyPI → Account Settings → Publishing
2. Add a new "trusted publisher"
3. Configure:
   - PyPI project name: `thinkmark`
   - Owner: `your-github-username`
   - Repository: `ThinkMark`
   - Workflow: `publish.yml`
   - Environment: `release`

### Environment Protection Rules
1. Go to GitHub → Settings → Environments
2. Create environment named `release`
3. Add protection rules:
   - Required reviewers (optional)
   - Deployment branches: only protected branches

## Release Process

### 1. Prepare Release
```bash
# Update version in pyproject.toml
# Update CHANGELOG.md if exists
# Commit changes
git add pyproject.toml
git commit -m "Bump version to 0.2.1"
```

### 2. Create Release
```bash
# Create and push tag
git tag v0.2.1
git push origin v0.2.1

# Or create release via GitHub web interface
```

### 3. Verify Publication
- Check [PyPI project page](https://pypi.org/project/thinkmark/)
- Test installation: `pip install thinkmark==0.2.1`
- Verify CLI commands work

## Version Management

### Semantic Versioning
- `MAJOR.MINOR.PATCH` (e.g., `0.2.1`)
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Pre-release Versions
```bash
# Development versions
0.3.0a1  # Alpha
0.3.0b1  # Beta
0.3.0rc1 # Release candidate
```

## Package Metadata

Key fields in `pyproject.toml`:
- `name`: Package name on PyPI
- `version`: Current version
- `description`: Short package description
- `keywords`: Search keywords
- `classifiers`: Package categorization
- `urls`: Important links

## Troubleshooting

### Common Issues
- **Version already exists**: Increment version number
- **Authentication failed**: Check API tokens or trusted publishing setup
- **Package validation errors**: Run `twine check dist/*`
- **Import errors**: Verify package structure and dependencies

### Testing Locally
```bash
# Install in development mode
pip install -e .

# Test CLI commands
thinkmark --help
thinkmark-mcp --help

# Run tests
pytest
```

## Security Best Practices

1. **Never commit API tokens** to version control
2. **Use trusted publishing** when possible
3. **Enable 2FA** on PyPI accounts
4. **Review dependencies** for security vulnerabilities
5. **Use environment protection** rules in GitHub

## Monitoring

After publishing:
- Monitor PyPI download statistics
- Check for user issues and bug reports
- Monitor security advisories for dependencies
- Keep dependencies updated