#!/usr/bin/env python3
"""
Helper script to run grading workflow from project root.
Usage: python run_grading.py <document_id> [rubric_path]
"""
import sys
import os
from pathlib import Path

# Add scripts to path
scripts_dir = Path(__file__).parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

# Change to project root
os.chdir(Path(__file__).parent)

# Import and run
from grading_workflow import main

if __name__ == "__main__":
    main()

