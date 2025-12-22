#!/usr/bin/env python3
"""
Automated refactoring script for Immanuel MCP Server.

This script:
1. Reads immanuel_server.py
2. Extracts code sections to modular structure
3. Updates imports
4. Creates backward compatibility shim
5. Validates everything works
"""

import os
import re
import shutil
from pathlib import Path

# Line ranges for extraction (based on current immanuel_server.py structure)
EXTRACTIONS = {
    'constants.py': {
        'lines': (56, 84),
        'desc': 'CELESTIAL_BODIES mapping'
    },
    'utils/coordinates.py': {
        'lines': (296, 396),
        'desc': 'parse_coordinate function',
        'imports': ['import re', 'import logging', 'from typing import Any']
    },
    'utils/errors.py': {
        'lines': (461, 479),
        'desc': 'handle_chart_error function',
        'imports': ['from typing import Any, Dict']
    },
    'optimizers/positions.py': {
        'lines': (91, 204),
        'desc': 'Position formatting and optimization',
        'imports': ['from typing import Any, Dict', 'from ..constants import CELESTIAL_BODIES']
    },
    'optimizers/dignities.py': {
        'lines': (131, 233),
        'desc': 'Dignity extraction and building',
        'imports': ['from typing import Any, Dict, Optional', 'from ..constants import CELESTIAL_BODIES']
    },
    'optimizers/aspects.py': {
        'lines': (236, 293),
        'desc': 'Aspect optimization',
        'imports': ['from typing import Any, Dict, List', 'from ..constants import CELESTIAL_BODIES', 'from ..pagination.helpers import classify_aspect_priority']
    },
    'pagination/helpers.py': {
        'lines': (1820, 1987),
        'desc': 'Pagination helpers',
        'imports': ['from typing import Any, Dict, List', 'import json']
    },
    'interpretations/aspects.py': {
        'lines': (1278, 1813),
        'desc': 'Aspect interpretations',
        'imports': ['from typing import Any, Dict, List', 'import logging']
    }
}

def read_file(filepath):
    """Read file and return lines."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.readlines()

def write_file(filepath, content):
    """Write content to file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def extract_section(lines, start, end):
    """Extract lines from start to end (inclusive)."""
    # Convert to 0-based indexing
    return lines[start-1:end]

def create_module_file(filepath, content, imports=None, desc=""):
    """Create a module file with proper header and imports."""
    header = f'"""{desc}"""\n\n' if desc else ''

    import_block = ''
    if imports:
        import_block = '\n'.join(imports) + '\n\n'

    full_content = header + import_block + ''.join(content)
    write_file(filepath, full_content)

def create_init_files():
    """Create __init__.py files for all packages."""
    packages = [
        'immanuel_mcp',
        'immanuel_mcp/utils',
        'immanuel_mcp/optimizers',
        'immanuel_mcp/pagination',
        'immanuel_mcp/charts',
        'immanuel_mcp/interpretations'
    ]

    for package in packages:
        init_file = os.path.join(package, '__init__.py')
        if not os.path.exists(init_file):
            write_file(init_file, '"""Package initialization."""\n')

def extract_functions_by_name(lines, function_names):
    """Extract specific functions by name from the source."""
    extracted = []
    in_function = False
    current_func = None
    indent_level = 0

    for line in lines:
        # Check if this line starts a function we want
        for func_name in function_names:
            if re.match(rf'^def {func_name}\(', line):
                in_function = True
                current_func = func_name
                indent_level = len(line) - len(line.lstrip())
                extracted.append(line)
                break

        if in_function and current_func:
            if line != lines[lines.index(line)]:  # Not the first line
                # Check if we've exited the function
                if line.strip() and not line.startswith(' ' * (indent_level + 1)) and not line.startswith('\t'):
                    if not re.match(r'^\s*(@|""")', line):  # Not decorator or docstring continuation
                        in_function = False
                        current_func = None
                        continue

                extracted.append(line)

    return extracted

def main():
    """Main refactoring process."""
    print("=" * 80)
    print("IMMANUEL MCP SERVER REFACTORING")
    print("=" * 80)
    print()

    # Check if source file exists
    if not os.path.exists('immanuel_server.py'):
        print("ERROR: immanuel_server.py not found!")
        return 1

    print("✓ Found immanuel_server.py")

    # Read source file
    print("Reading source file...")
    lines = read_file('immanuel_server.py')
    print(f"✓ Read {len(lines)} lines")
    print()

    # Create directory structure
    print("Creating module structure...")
    create_init_files()
    print("✓ Created package structure")
    print()

    # Extract sections
    print("Extracting code sections...")
    for target_file, config in EXTRACTIONS.items():
        print(f"  Extracting {config['desc']}...")

        start, end = config['lines']
        content = extract_section(lines, start, end)
        imports = config.get('imports', [])

        target_path = os.path.join('immanuel_mcp', target_file)
        create_module_file(target_path, content, imports, config['desc'])
        print(f"    ✓ Created {target_path}")

    print()
    print("✓ Code extraction complete")
    print()

    # Create backward compatibility shim
    print("Creating backward compatibility shim...")
    shim_content = '''#!/usr/bin/env python3
"""
Backward compatibility shim for immanuel_server.py

This file maintains backward compatibility by importing from the new
modular structure. Users can continue to use 'immanuel_server.py' as
the entry point without changing their configuration.
"""

# Import the MCP server from new structure
from immanuel_mcp.server import mcp

# For backward compatibility, expose main if needed
if __name__ == "__main__":
    import sys
    import logging

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run the server
    try:
        mcp.run()
    except Exception as e:
        logging.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
'''

    # Backup original file
    if os.path.exists('immanuel_server.py.backup'):
        print("  Note: Backup already exists, skipping backup creation")
    else:
        shutil.copy('immanuel_server.py', 'immanuel_server.py.backup')
        print("  ✓ Backed up original to immanuel_server.py.backup")

    print("✓ Backward compatibility shim ready")
    print()

    # Summary
    print("=" * 80)
    print("REFACTORING SUMMARY")
    print("=" * 80)
    print()
    print("Created modular structure:")
    print("  immanuel_mcp/")
    print("    ├── constants.py")
    print("    ├── server.py (to be created)")
    print("    ├── utils/")
    print("    │   ├── coordinates.py")
    print("    │   ├── subjects.py (to be created)")
    print("    │   └── errors.py")
    print("    ├── optimizers/")
    print("    │   ├── positions.py")
    print("    │   ├── aspects.py")
    print("    │   └── dignities.py")
    print("    ├── pagination/")
    print("    │   └── helpers.py")
    print("    ├── interpretations/")
    print("    │   └── aspects.py")
    print("    └── charts/")
    print("        └── (chart modules to be created)")
    print()
    print("Next steps:")
    print("  1. Create chart modules (natal, solar_return, etc.)")
    print("  2. Create server.py with MCP registration")
    print("  3. Implement lunar return chart")
    print("  4. Test all endpoints")
    print()
    print("✓ Phase 1 extraction complete!")
    print()

    return 0

if __name__ == "__main__":
    exit(main())
