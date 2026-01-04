# Testing Guide

## Quick Start

### Option 1: Docker (Recommended if Docker is available)

**Start Docker daemon:**
```bash
sudo systemctl start docker
sudo systemctl enable docker  # Optional: enable on boot
```

**Run tests:**
```bash
./docker-test.sh
```

### Option 2: Install Python 3.11/3.12 from AUR

If Docker is not available, install Python 3.11 or 3.12:

```bash
# Install Python 3.11 from AUR
yay -S python311

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install test dependencies
pip install -r requirements.test.txt

# Run tests
pytest
```

### Option 3: Use Podman (Docker alternative)

If you have Podman installed instead of Docker:

```bash
# Build and run with Podman
podman build -f Dockerfile.test -t synology-photo-sync-test .
podman run --rm synology-photo-sync-test
```

### Option 4: Skip Local Testing (Use CI/CD)

If you can't run tests locally due to Python 3.13 issues:

1. Push your code to GitHub
2. The CI/CD pipeline will automatically run tests on Python 3.11 and 3.12
3. Check the GitHub Actions tab for test results

## Running Tests

Once you have a working environment:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_sync_client.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=custom_components.synology_photo_sync

# Run specific test
pytest tests/test_sync_client.py::test_sync_source_success
```

## Troubleshooting

### Docker Issues

**Docker daemon not running:**
```bash
sudo systemctl start docker
```

**Permission denied:**
```bash
# Add user to docker group (requires logout/login)
sudo usermod -aG docker $USER
```

### Python 3.13 Issues

If you're stuck with Python 3.13 and can't use Docker or install Python 3.11/3.12:

1. **Use GitHub Actions**: Push code and let CI/CD run tests
2. **Use a different machine/VM**: Test on a system with Python 3.11/3.12
3. **Wait for Python 3.13 fix**: The expat issue should be resolved in future Python updates

## Test Structure

- `tests/test_sync_client.py` - Tests for the sync client
- `tests/test_config_flow.py` - Tests for configuration flow
- `tests/test_init.py` - Tests for integration setup
- `tests/conftest.py` - Pytest fixtures and configuration


