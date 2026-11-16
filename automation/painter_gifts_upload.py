import os
import sys
import time
import logging
from pathlib import Path

# Fix Windows console unicode output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure automation directory is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dashboard_automation import VendorPortalAutomation
from gift_management import GiftManagementAutomation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Pre-defined Gift Scheme from "Painter ke liye uphaar (4).pdf"
PAINTER_GIFTS = [
    {
        "num": 1,
        "name": "Double Bed Bedsheet",
        "description": "Double Bed Bedsheet",
        "points": "10",
        "value": "10"
    },
    {
        "num": 2,
        "name": "Bajaj Iron",
        "description": "Bajaj Iron",
        "points": "20",
        "value": "20"
    },
    {
        "num": 3,
        "name": "Boat Earbuds",
        "description": "Boat Earbuds",
        "points": "30",
        "value": "30"
    },
    {
        "num": 4,
        "name": "2.5 L Milton Water Jug",
        "description": "2.5 L Milton Water Jug",
        "points": "40",
        "value": "40"
    },
    {
        "num": 5,
        "name": "5 L Cooker (Hawkins)",
        "description": "5 L Cooker (Hawkins)",
        "points": "50",
        "value": "50"
    },
    {
        "num": 6,
        "name": "Crompton Mixer Grinder (3 Jar)",
        "description": "Crompton Mixer Grinder (3 Jar)",
        "points": "75",
        "value": "75"
    },
    {
        "num": 7,
        "name": "2 Pc Ceiling Fan (Crompton)",
        "description": "2 Pc Ceiling Fan (Crompton)",
        "points": "100",
        "value": "100"
    },
    {
        "num": 8,
        "name": "Usha Sewing Machine",
        "description": "Usha Sewing Machine",
        "points": "125",
        "value": "125"
    },
    {
        "num": 9,
        "name": "Room Cooler (Up to ₹5000)",
        "description": "Room Cooler (Up to ₹5000)",
        "points": "150",
        "value": "150"
    },
    {
        "num": 10,
        "name": "Ranger Cycle",
        "description": "Ranger Cycle",
        "points": "175",
        "value": "175"
    },
    {
        "num": 11,
        "name": "7.5 kg Semi Automatic Washing Machine",
        "description": "7.5 kg Semi Automatic Washing Machine",
        "points": "225",
        "value": "225"
    },
    {
        "num": 12,
        "name": "Philips Home Theater",
        "description": "Philips Home Theater",
        "points": "275",
        "value": "275"
    },
    {
        "num": 13,
        "name": "Almirah",
        "description": "Almirah",
        "points": "300",
        "value": "300"
    },
    {
        "num": 14,
        "name": "32\" LED TV",
        "description": "32\" LED TV",
        "points": "350",
        "value": "350"
    },
    {
        "num": 15,
        "name": "190 Ltr Refrigerator",
        "description": "190 Ltr Refrigerator",
        "points": "400",
        "value": "400"
    },
    {
        "num": 16,
        "name": "Mobile Phone (Up to ₹ 17,500)",
        "description": "Mobile Phone (Up to ₹ 17,500)",
        "points": "500",
        "value": "500"
    },
    {
        "num": 17,
        "name": "Double Door Fridge",
        "description": "Double Door Fridge",
        "points": "600",
        "value": "600"
    },
    {
        "num": 18,
        "name": "43\" LED TV",
        "description": "43\" LED TV",
        "points": "700",
        "value": "700"
    },
    {
        "num": 19,
        "name": "1.5 Ton Window AC",
        "description": "1.5 Ton Window AC",
        "points": "800",
        "value": "800"
    },
    {
        "num": 20,
        "name": "Laptop (Up to ₹35,000)",
        "description": "Laptop (Up to ₹35,000)",
        "points": "1000",
        "value": "1000"
    },
    {
        "num": 21,
        "name": "Electric Scooter (Up to ₹50,000)",
        "description": "Electric Scooter (Up to ₹50,000)",
        "points": "1500",
        "value": "1500"
    },
    {
        "num": 22,
        "name": "TVS Sport Bike (Ex-showroom)",
        "description": "TVS Sport Bike (Ex-showroom)",
        "points": "2500",
        "value": "2500"
    }
]

def find_image_for_gift(gift_dir: Path, num: int) -> Path:
    """Find matching image file in gift/ by number."""
    exts = [".png", ".jpg", ".jpeg", ".webp", ".PNG", ".JPG", ".JPEG"]
    for ext in exts:
        p = gift_dir / f"{num}{ext}"
        if p.exists():
            return p
    # Try finding any file starting with num
    for f in gift_dir.iterdir():
        if f.is_file() and f.stem == str(num):
            return f
    return None

def run_painter_gifts_upload(email=None, password=None):
    # Locate gift folder
    possible_folders = [
        Path(__file__).resolve().parent.parent / "gift",
        Path(__file__).resolve().parent / "gift",
        Path("gift")
    ]
    gift_dir = None
    for folder in possible_folders:
        if folder.exists() and folder.is_dir():
            gift_dir = folder
            break

    if not gift_dir:
        print("❌ 'gift' folder not found!")
        return False

    # Check credentials
    if not email:
        email = os.getenv("VENDOR_EMAIL", "").strip()
    if not password:
        password = os.getenv("VENDOR_PASSWORD", "").strip()

    if not email or not password:
        print("\n" + "=" * 65)
        print("  🔑 ENTER VENDOR PORTAL CREDENTIALS")
        print("=" * 65)
        if not email:
            email = input("  Email: ").strip()
        if not password:
            import getpass
            password = input("  Password: ").strip()

    if not email or not password:
        print("❌ Email and password are required.")
        return False

    print("\n" + "=" * 65)
    print("  🎨 PAINTER SCHEME GIFTS AUTOMATION (from PDF Scheme)")
    print("=" * 65)
    print(f"  Target Audience : Painter")
    print(f"  Total Gifts     : {len(PAINTER_GIFTS)}")
    print(f"  Gift Directory  : {gift_dir.absolute()}")
    print("-" * 65)

    # Validate image files
    prepared_gifts = []
    for item in PAINTER_GIFTS:
        img_path = find_image_for_gift(gift_dir, item["num"])
        if not img_path:
            logger.warning(f"⚠ Missing image for gift {item['num']} ({item['name']})")
        
        prepared_gifts.append({
            "name": item["name"],
            "description": item["description"],
            "points": item["points"],
            "value": item["value"],
            "target_user_types": ["Painter"],
            "image_path": str(img_path.absolute()) if img_path else None,
            "image_name": img_path.name if img_path else f"{item['num']}.png"
        })

    print("  Prepared Gifts List:")
    for idx, g in enumerate(prepared_gifts, 1):
        status = "✓ Ready" if g["image_path"] else "⚠ Image Missing"
        print(f"  {idx:2d}. [{status}] {g['name']:<40} Points: {g['points']:<5} Value: {g['value']:<5} Image: {g['image_name']}")
    print("=" * 65)

    confirm = input("\n  Start uploading all 22 Painter gifts to the portal? (Y/n): ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("❌ Upload cancelled.")
        return False

    print("\n🚀 Starting browser & logging in...")

    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                logger.error("✗ Login failed")
                return False

            time.sleep(2)
            gift_auto = GiftManagementAutomation(auto.driver)

            if not gift_auto.navigate():
                logger.error("✗ Failed to navigate to Gift Management")
                return False

            successful = 0
            failed = 0
            total = len(prepared_gifts)

            for idx, gift in enumerate(prepared_gifts, 1):
                logger.info(f"\n[{idx}/{total}] Uploading: '{gift['name']}' ({gift['image_name']}) for 'Painter'")
                print(f"  [{idx}/{total}] Uploading: '{gift['name']}' (Pts: {gift['points']}, Val: {gift['value']})...")

                if not gift["image_path"]:
                    logger.error(f"  ✗ Skipping gift {idx} due to missing image file")
                    failed += 1
                    continue

                if gift_auto.add_new_gift(gift, target_user_types=["Painter"]):
                    successful += 1
                    print(f"  ✓ Successfully uploaded: '{gift['name']}'")
                else:
                    failed += 1
                    print(f"  ✗ Failed to upload: '{gift['name']}'")
                
                time.sleep(1.5)

            print("\n" + "=" * 65)
            print("  🎨 PAINTER GIFTS UPLOAD SUMMARY")
            print("=" * 65)
            print(f"  Total Gifts Processed : {total}")
            print(f"  ✓ Successful Uploads  : {successful}")
            print(f"  ✗ Failed Uploads      : {failed}")
            print("=" * 65 + "\n")

            return failed == 0

    except Exception as e:
        logger.error(f"Unexpected error during painter gifts upload: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    run_painter_gifts_upload()
