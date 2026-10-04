---
name: safe-cleanup-testing
description: Playbook for safely testing and verifying file deletion, send2trash workflows, and disk cleanup routines.
---

# Safe Cleanup & Testing Playbook

When developing or modifying tools that delete or trash files (such as `trash_path` in `src/storage_intelligence/tools/cleanup.py`), strictly adhere to these safety and testing guidelines.

## 1. Safety Principles

1. **Use `send2trash`**: Never call `os.remove`, `os.unlink`, or `shutil.rmtree` directly on user paths. `send2trash` places files into the platform's Recycle Bin / Trash.
2. **Deepest-Path-First Ordering**: When trashing multiple paths or directory trees, sort targets deepest-first (`sorted(paths, key=lambda t: (-len(Path(t).parts), t))`). Trashing a parent folder first causes child path deletions to fail with "file not found", confusing the status report.
3. **Deduplication**: Deduplicate paths before processing to prevent redundant deletion attempts.

## 2. Testing Workflows

### Mock Testing with `pytest`
- Always write tests using `pytest`'s built-in `tmp_path` fixture.
- Construct temporary directory structures in memory/tmp files before invoking cleanup logic.

Example test pattern:
```python
import pytest
from pathlib import Path
from storage_intelligence.tools.cleanup import trash_path


@pytest.mark.asyncio
async def test_trash_path_dry_run(tmp_path, mock_context):
    test_file = tmp_path / "sample.txt"
    test_file.write_text("hello")

    # Verify dry run
    result = await trash_path(path=str(test_file), confirm=False, ctx=mock_context)
    assert result["mode"] == "preview"
    assert test_file.exists()  # File must still exist!
```

### Manual Safety Verification
When testing manually in local environments:
- Never pass real user home directory paths (`~`, `/Users/.../Documents`) during experimental test runs.
- Use subdirectories inside a temporary test workspace.
