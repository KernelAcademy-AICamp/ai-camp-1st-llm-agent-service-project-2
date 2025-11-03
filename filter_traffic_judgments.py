#!/usr/bin/env python3
"""
Filter traffic-related judgment files from the criminal law dataset.
Filters for files related to traffic accidents and road traffic laws.
"""

import os
import csv
import shutil
from pathlib import Path
from typing import List, Set

# Source and destination paths
SOURCE_DIR = Path("/Users/nw_mac/Documents/Github_crawling/ai-camp-1st-llm-agent-service-project-2/.data/04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/3.개방데이터/1.데이터/Training/01.원천데이터/TS_판결문")
DEST_DIR = Path("/Users/nw_mac/Documents/Github_crawling/ai-camp-1st-llm-agent-service-project-2/.data_traffic/04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/3.개방데이터/1.데이터/Training/원천데이터/판결문")

# Keywords to identify traffic-related cases
TRAFFIC_KEYWORDS = [
    "교통사고",
    "도로교통법",
    "교통법",
    "음주운전",
    "무면허운전",
    "뺑소니",
    "특정범죄가중처벌등에관한법률",  # Often related to traffic accidents
    "특가법",
    "교통",
    "운전",
    "차량",
    "자동차",
    "오토바이",
    "이륜차",
    "보행자",
    "횡단보도",
    "신호위반",
    "과실치사",
    "과실치상",
    "업무상과실",
]


def is_traffic_related(file_path: Path) -> bool:
    """
    Check if a CSV file contains traffic-related content.

    Args:
        file_path: Path to the CSV file

    Returns:
        True if the file is traffic-related, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read the entire file content
            content = f.read().lower()

            # Check for any traffic-related keywords
            for keyword in TRAFFIC_KEYWORDS:
                if keyword.lower() in content:
                    return True

            return False
    except Exception as e:
        print(f"Error reading {file_path.name}: {e}")
        return False


def filter_and_copy_files():
    """
    Filter traffic-related files and copy them to the destination directory.
    """
    # Create destination directory
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created destination directory: {DEST_DIR}")

    # Get all CSV files
    csv_files = list(SOURCE_DIR.glob("*.csv"))
    total_files = len(csv_files)
    print(f"Found {total_files} CSV files to process")

    # Filter and copy
    traffic_files = []
    processed = 0

    for csv_file in csv_files:
        processed += 1

        if processed % 1000 == 0:
            print(f"Progress: {processed}/{total_files} files processed, {len(traffic_files)} traffic-related files found")

        if is_traffic_related(csv_file):
            traffic_files.append(csv_file)
            # Copy file to destination
            dest_file = DEST_DIR / csv_file.name
            shutil.copy2(csv_file, dest_file)

    print(f"\n=== Filtering Complete ===")
    print(f"Total files processed: {total_files}")
    print(f"Traffic-related files found: {len(traffic_files)}")
    print(f"Files copied to: {DEST_DIR}")

    # Print sample file names
    if traffic_files:
        print(f"\nSample traffic-related files:")
        for file in traffic_files[:10]:
            print(f"  - {file.name}")

    return traffic_files


if __name__ == "__main__":
    filter_and_copy_files()
