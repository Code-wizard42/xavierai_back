#!/usr/bin/env python3
"""
Script to fix import paths after deploying xavier_back as root directory.
This converts all 'from X import Y' to 'from X import Y' or 'from X import Y'
"""

import os
import re
import glob

def fix_imports_in_file(file_path):
    """Fix import statements in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern to match 'from X import Y'
        pattern = r'from xavier_back\.([^\s]+) import'
        
        def replace_import(match):
            module_path = match.group(1)
            
            # If it's a top-level module (config, extensions, etc.), use direct import
            if '.' not in module_path:
                return f'from {module_path} import'
            else:
                # For nested modules, use relative import
                return f'from {module_path} import'
        
        # Replace the imports
        content = re.sub(pattern, replace_import, content)
        
        # Also handle direct imports like 'import X'
        content = re.sub(r'import xavier_back\.([^\s]+)', r'import \1', content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed imports in: {file_path}")
            return True
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False
    
    return False

def main():
    """Main function to fix all imports."""
    print("Fixing import paths in Python files...")
    
    # Get all Python files in the current directory and subdirectories
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip_dir in root for skip_dir in ['.git', '__pycache__', '.pytest_cache', 'venv', 'env']):
            continue
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    fixed_count = 0
    total_files = len(python_files)
    
    for file_path in python_files:
        if fix_imports_in_file(file_path):
            fixed_count += 1
    
    print(f"\nCompleted! Fixed imports in {fixed_count} out of {total_files} Python files.")

if __name__ == "__main__":
    main() 