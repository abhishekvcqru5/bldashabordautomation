#!/usr/bin/env python3
"""
Generate icon_config.json from CSV file

Usage:
    python generate_config.py input.csv [output.json]

CSV Format:
    user_type,icon_identity,display_title,image_file,toggle_option
    customer,gift,Gift,Gift.png,both
    vendor,ecommerce,E-Commerce,ecommerce.png,both
"""

import csv
import json
import sys
from pathlib import Path


def generate_config_from_csv(csv_path, output_path=None):
    """
    Generate icon_config.json from CSV file

    Args:
        csv_path: Path to CSV file
        output_path: Output JSON file path (default: icon_config.json)
    """
    if output_path is None:
        output_path = "automation/icon_config.json"

    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return False

    icons = []

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Validate headers
            if reader.fieldnames is None:
                print("Error: CSV file is empty")
                return False

            required_fields = {'user_type', 'icon_identity', 'display_title', 'image_file'}
            if not required_fields.issubset(set(reader.fieldnames)):
                print(f"Error: CSV must have columns: {', '.join(required_fields)}")
                print(f"Found columns: {', '.join(reader.fieldnames)}")
                return False

            for row_num, row in enumerate(reader, start=2):
                # Skip empty rows
                if not any(row.values()):
                    continue

                icon_entry = {
                    "user_type": row['user_type'].strip(),
                    "icon_identity": row['icon_identity'].strip(),
                    "display_title": row['display_title'].strip(),
                    "image_path": f"automation/processed_images/{row['image_file'].strip()}",
                    "toggle_option": row.get('toggle_option', 'both').strip().lower() or 'both'
                }

                # Validate required fields
                if not all([icon_entry['user_type'], icon_entry['icon_identity'], icon_entry['display_title']]):
                    print(f"Warning: Row {row_num} has empty fields, skipping")
                    continue

                icons.append(icon_entry)

        if not icons:
            print("Error: No valid icons found in CSV")
            return False

        # Create output structure
        config = {"icons": icons}

        # Write JSON
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        print(f"✓ Generated config with {len(icons)} icons")
        print(f"✓ Saved to: {output_file}")

        # Show summary
        user_types = set(icon['user_type'] for icon in icons)
        print(f"\nSummary:")
        print(f"  Total icons: {len(icons)}")
        print(f"  User types: {', '.join(sorted(user_types))}")

        return True

    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    csv_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "automation/icon_config.json"

    success = generate_config_from_csv(csv_file, output_file)
    sys.exit(0 if success else 1)
