#!/usr/bin/env python3
"""
Script to fix remaining relative imports that should be absolute imports.
"""

import os
import re

def fix_relative_imports():
    """Fix relative imports that should be absolute."""
    
    # Files that need fixing
    files_to_fix = []
    
    # Get all Python files
    for root, dirs, files in os.walk('.'):
        if any(skip_dir in root for skip_dir in ['.git', '__pycache__', '.pytest_cache', 'venv', 'env']):
            continue
        for file in files:
            if file.endswith('.py'):
                files_to_fix.append(os.path.join(root, file))
    
    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix specific patterns that are problematic
            patterns_to_fix = [
                # Fix imports that should be absolute in the root package
                (r'from \.([^.\s]+) import', r'from \1 import'),
                (r'from \.([^.\s]+)\.([^.\s]+) import', r'from \1.\2 import'),
                (r'from \.([^.\s]+)\.([^.\s]+)\.([^.\s]+) import', r'from \1.\2.\3 import'),
                (r'from \.([^.\s]+)\.([^.\s]+)\.([^.\s]+)\.([^.\s]+) import', r'from \1.\2.\3.\4 import'),
            ]
            
            for pattern, replacement in patterns_to_fix:
                content = re.sub(pattern, replacement, content)
            
            # Write back if changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Fixed relative imports in: {file_path}")
        
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    print("Fixing remaining relative imports...")
    fix_relative_imports()
    print("Done!") 