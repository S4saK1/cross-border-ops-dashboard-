#!/usr/bin/env python3
"""
Generate a list of files to upload to GitHub, excluding .gitignore patterns.
"""
import os
import fnmatch
from pathlib import Path

def load_gitignore_patterns(gitignore_path):
    """Load patterns from .gitignore file."""
    patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    return patterns

def is_ignored(file_path, patterns, root_dir):
    """Check if a file should be ignored based on gitignore patterns."""
    # Get relative path from root
    rel_path = os.path.relpath(file_path, root_dir).replace('\\', '/')
    
    # Check against patterns
    for pattern in patterns:
        # Handle negation patterns
        if pattern.startswith('!'):
            continue
            
        # Handle directory patterns
        if pattern.endswith('/'):
            pattern = pattern[:-1]
            if os.path.isdir(file_path):
                if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(os.path.basename(file_path), pattern):
                    return True
        else:
            # Handle file patterns
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(os.path.basename(file_path), pattern):
                return True
    
    return False

def main():
    root_dir = Path(__file__).parent.parent
    gitignore_path = root_dir / '.gitignore'
    
    # Load gitignore patterns
    patterns = load_gitignore_patterns(gitignore_path)
    
    # Additional patterns to exclude
    additional_exclude = [
        '.env',
        '.env.local', 
        '.env.production',
        '*.db',
        '*.sqlite',
        '*.sqlite3',
        '__pycache__',
        '*.pyc',
        'node_modules',
        '.next',
        'data/',
        'logs/',
        '*.log',
        'temp/',
        'tmp/',
        '*.temp',
        '*.tmp',
        '.pytest_cache',
        '.coverage',
        'htmlcov',
        '.mypy_cache',
        '.ruff_cache',
        'coverage_html',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.Python',
        'build/',
        'dist/',
        'eggs/',
        '*.egg-info',
        '*.egg',
        'lib/',
        'lib64',
        'parts/',
        'sdist/',
        'var/',
        'wheels/',
        '.installed.cfg',
        'pip-log.txt',
        'pip-delete-this-directory.txt',
        '.github',  # We'll add this separately
        '.git',
        '.gitignore',  # We'll add this separately
        'nul',
        'test_password_validation.py',  # Temporary test file
        'scripts/init-git.sh',
        'scripts/init-git.bat',
        'scripts/generate_upload_list.py',
    ]
    
    all_files = []
    
    # Walk through directory
    for root, dirs, files in os.walk(root_dir):
        # Skip hidden directories and common excluded directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in [
            '__pycache__', 'node_modules', '.next', 'data', 'logs', 'temp', 'tmp',
            'build', 'dist', 'eggs', 'coverage_html', '.pytest_cache', '.mypy_cache',
            '.ruff_cache', 'htmlcov'
        ]]
        
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(root_dir)
            
            # Check if file should be excluded
            should_exclude = False
            
            # Check gitignore patterns
            if is_ignored(file_path, patterns, root_dir):
                should_exclude = True
            
            # Check additional patterns
            for pattern in additional_exclude:
                if fnmatch.fnmatch(str(rel_path), pattern) or fnmatch.fnmatch(file, pattern):
                    should_exclude = True
                    break
            
            if not should_exclude:
                all_files.append(str(rel_path))
    
    # Sort files for consistent output
    all_files.sort()
    
    # Print summary
    print(f"Total files to upload: {len(all_files)}")
    print("\nFiles by directory:")
    dir_counts = {}
    for file in all_files:
        dir_name = os.path.dirname(file)
        if dir_name == '':
            dir_name = '.'
        dir_counts[dir_name] = dir_counts.get(dir_name, 0) + 1
    
    for dir_name, count in sorted(dir_counts.items()):
        print(f"  {dir_name}: {count} files")
    
    # Write to file list
    with open(root_dir / 'upload_files.txt', 'w', encoding='utf-8') as f:
        for file in all_files:
            f.write(f"{file}\n")
    
    print(f"\nFile list written to: {root_dir / 'upload_files.txt'}")

if __name__ == "__main__":
    main()