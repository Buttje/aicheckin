# Versioning System

This document describes the automatic version numbering system for `vc_commit_helper`.

## Version Format

The version follows a three-part semantic format with PEP 440 compliance:

```
{major}.{minor}.dev0+g{commit_sha}
```

For example: `0.5.dev0+g1fbcb8c`

### Components

1. **Major Version** (`{major}`)
   - Manually controlled by the programmer
   - Set in `src/vc_commit_helper/__init__.py` as `__base_version__`
   - Only increment when making breaking changes
   - Current value: `0`

2. **Minor Version** (`{minor}`)
   - Automatically incremented when a release is published
   - Derived from git tags following the pattern `v{major}.{minor}` (e.g., `v0.1`, `v0.2`)
   - The system finds the highest minor version from existing tags
   - Starts at `0` if no tags exist

3. **Build Number** (`dev0+g{commit_sha}`)
   - Uses the short git commit SHA (7 characters)
   - Automatically generated at runtime
   - Follows PEP 440 development release format
   - Shows as `dev0` when not in a git repository

## How It Works

### For Developers

The version is dynamically generated when the package is imported:

```python
from vc_commit_helper import __version__
print(__version__)  # e.g., "0.5.dev0+g1fbcb8c"
```

### For Releases

When a GitHub release is published, the CI/CD workflow automatically:

1. Reads the current major version from `__init__.py`
2. Finds the highest minor version from existing tags
3. Creates a new tag with the incremented minor version
4. Builds the package with the new version
5. Publishes to PyPI

#### Example Release Flow

**Initial state:**
- Major version in code: `0`
- Existing tags: none
- Current commit: `abc1234`
- Generated version: `0.0.dev0+gabc1234`

**After creating first release:**
1. CI workflow creates tag `v0.0`
2. Future builds will show version: `0.0.dev0+g{new_commit}`

**After creating second release:**
1. CI workflow creates tag `v0.1`
2. Future builds will show version: `0.1.dev0+g{new_commit}`

### Changing the Major Version

To increment the major version (e.g., from `0` to `1`):

1. Edit `src/vc_commit_helper/__init__.py`
2. Change `__base_version__ = "0"` to `__base_version__ = "1"`
3. Commit and push
4. Create a release - this will create tag `v1.0` (starting minor version at 0)

## Tag Naming Convention

Release tags must follow this pattern:
- Format: `v{major}.{minor}`
- Examples: `v0.1`, `v0.2`, `v1.0`, `v1.1`

The system parses these tags to determine the next minor version.

## Local Development

During development, the version reflects your current commit:

```bash
$ git rev-parse --short=7 HEAD
abc1234

$ python -c "from vc_commit_helper import __version__; print(__version__)"
0.2.dev0+gabc1234
```

## Testing

Comprehensive tests for the versioning system are in `tests/test_version.py`.

Run them with:
```bash
pytest tests/test_version.py -v
```

## Troubleshooting

**Version shows `dev0` without commit SHA:**
- You're not in a git repository or git is not available
- Fallback version is used: `{major}.{minor}.dev0`

**Minor version is incorrect:**
- Check that tags follow the `v{major}.{minor}` pattern
- List tags with: `git tag -l "v*"`
- Only tags matching the current major version are counted
