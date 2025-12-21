# MCP Server Troubleshooting Guide

## Problem Summary

The Immanuel MCP server was failing to start in Claude Desktop with various configuration issues. This document outlines the problems encountered and the solutions implemented.

## Errors Encountered & Solutions

### 1. "Failed to spawn: `immanuel_server.py`" - Program Not Found

**Error Log:**
```
error: Failed to spawn: `immanuel_server.py`
  Caused by: program not found
```

**Root Cause:** The original configuration attempted to run the Python file directly without proper executable setup.

**Initial Failed Config:**
```json
"immanuel-astrology": {
    "command": "uv",
    "args": ["run", "immanuel_server.py"],
    "cwd": "C:\\Users\\BJJ\\Documents\\MCP\\astro-mcp"
}
```

**Problem:** `uv run immanuel_server.py` couldn't find the file because it needed the full path to the uv executable.

### 2. "Failed to spawn: `immanuel-mcp`" - Script Not Found

**Error Log:**
```
error: Failed to spawn: `immanuel-mcp`
  Caused by: program not found
```

**Root Cause:** Attempted to use the project script name without proper installation.

**Failed Config:**
```json
"immanuel-astrology": {
    "command": "C:\\Users\\BJJ\\.local\\bin\\uv.exe",
    "args": ["run", "immanuel-mcp"],
    "cwd": "C:\\Users\\BJJ\\Documents\\MCP\\astro-mcp"
}
```

**Problem:** The script `immanuel-mcp` wasn't accessible even though it was defined in `pyproject.toml`.

### 3. File Path Resolution Issues

**Error Log:**
```
C:\Users\BJJ\AppData\Roaming\uv\python\cpython-3.12.7-windows-x86_64-none\python.exe: 
can't open file 'C:\\Users\\BJJ\\AppData\\Local\\AnthropicClaude\\app-0.11.6\\immanuel_server.py': 
[Errno 2] No such file or directory
```

**Root Cause:** The `cwd` parameter wasn't being respected properly, causing Python to look in the wrong directory.

**Failed Config:**
```json
"immanuel-astrology": {
    "command": "C:\\Users\\BJJ\\.local\\bin\\uv.exe",
    "args": ["run", "python", "immanuel_server.py"],
    "cwd": "C:\\Users\\BJJ\\Documents\\MCP\\astro-mcp"
}
```

**Problem:** Even with `cwd` set, the Python interpreter was looking in Claude's app directory instead of the project directory.

### 4. "ModuleNotFoundError: No module named 'immanuel'"

**Error Log:**
```
Traceback (most recent call last):
  File "C:\Users\BJJ\Documents\MCP\astro-mcp\immanuel_server.py", line 14, in <module>
    import immanuel
ModuleNotFoundError: No module named 'immanuel'
```

**Root Cause:** Two issues:
1. Dependencies weren't installed (`uv sync` hadn't been run)
2. Even after installation, the virtual environment wasn't being used properly

**Solution Steps:**
1. **Install dependencies:** `uv sync` (creates .venv and installs packages)
2. **Use `--directory` flag:** Ensures uv uses the project's virtual environment

## Final Working Configuration

**Successful Config:**
```json
"immanuel-astrology": {
    "command": "C:\\Users\\BJJ\\.local\\bin\\uv.exe",
    "args": ["--directory", "C:\\Users\\BJJ\\Documents\\MCP\\astro-mcp", "run", "python", "immanuel_server.py"]
}
```

**Key Elements:**
- **Full path to uv executable:** `C:\\Users\\BJJ\\.local\\bin\\uv.exe`
- **`--directory` flag:** Tells uv which project directory to use
- **Relative file path:** `immanuel_server.py` (works because directory is specified)
- **No `cwd` parameter:** Not needed with `--directory`

## Best Practices for Future MCP Server Setup

### 1. Project Structure Requirements
- Ensure `pyproject.toml` exists with proper dependencies
- Run `uv sync` to create virtual environment and install dependencies
- Verify dependencies are installed: `uv pip list`

### 2. Claude Desktop Configuration Patterns

**For uv-based Python projects:**
```json
"server-name": {
    "command": "C:\\Users\\[USERNAME]\\.local\\bin\\uv.exe",
    "args": ["--directory", "C:\\path\\to\\project", "run", "python", "server_file.py"]
}
```

**Alternative using project scripts:**
```json
"server-name": {
    "command": "C:\\Users\\[USERNAME]\\.local\\bin\\uv.exe",
    "args": ["--directory", "C:\\path\\to\\project", "run", "script-name"]
}
```

### 3. Common Pitfalls to Avoid

1. **Don't use relative paths for uv command:** Use full path `C:\\Users\\[USERNAME]\\.local\\bin\\uv.exe`
2. **Don't rely on `cwd` alone:** Use `--directory` flag for proper project context
3. **Don't forget `uv sync`:** Always install dependencies before testing
4. **Don't assume scripts work immediately:** Test both script names and direct file execution

### 4. Troubleshooting Checklist

**Before configuring Claude Desktop:**
- [ ] Project has `pyproject.toml` with correct dependencies
- [ ] Run `uv sync` to install dependencies
- [ ] Verify `uv pip list` shows required packages
- [ ] Test server manually: `uv run python server_file.py`

**Claude Desktop Configuration:**
- [ ] Use full path to uv executable
- [ ] Use `--directory` flag with project path
- [ ] Start with simple Python file execution
- [ ] Test and restart Claude Desktop after changes

### 5. Testing Commands

**Manual testing (run from project directory):**
```cmd
# Test basic server startup
uv run python immanuel_server.py

# Test with directory flag (from any location)
uv --directory C:\path\to\project run python immanuel_server.py

# Test project script (if configured)
uv --directory C:\path\to\project run script-name
```

## Environment Context

**Development Environment:**
- WSL2 (Linux subsystem) for development
- Windows filesystem for project files
- Claude Desktop on Windows
- uv package manager for Python dependencies

**Key Insight:** The cross-platform nature (WSL + Windows) required careful attention to path formats and executable locations, but the core issues were about proper uv project configuration rather than cross-platform compatibility.

## Conclusion

The main lesson is that uv-based MCP servers require:
1. Proper dependency installation (`uv sync`)
2. Correct project context (`--directory` flag)
3. Full executable paths in Claude Desktop config
4. Testing the command manually before adding to Claude Desktop

This approach should work for any uv-based Python MCP server project.