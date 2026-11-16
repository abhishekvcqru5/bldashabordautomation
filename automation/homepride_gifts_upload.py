# -*- coding: utf-8 -*-
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

# Pre-defined HomePride Gift Scheme (11 Tiers)
HOMEPRIDE_SCHEME = [
    {
        "tier": 1,
        "points": "5000",
        "value": "5000",
        "title": "CASIO MTP घड़ी / मिक्सर ग्राइंडर / ट्रॉली सूटकेस",
        "description": "CASIO MTP घड़ी / मिक्सर ग्राइंडर / ट्रॉली सूटकेस",
        "images": ["5000_1.png", "5000_2.png", "5000_3.png"],
        "items_summary": "CASIO MTP Watch, Mixer Grinder, Trolley Suitcase"
    },
    {
        "tier": 2,
        "points": "10000",
        "value": "10000",
        "title": "बोट एयरडोप्स सुप्रीम / 35gm चांदी का सिक्का",
        "description": "बोट एयरडोप्स सुप्रीम / 35gm चांदी का सिक्का",
        "images": ["10000_1.png", "10000_2.png"],
        "items_summary": "boAt Airdopes Supreme, 35gm Silver Coin"
    },
    {
        "tier": 3,
        "points": "20000",
        "value": "20000",
        "title": "सेमसंग वॉशिंग मशीन 7 kg टॉप लोड / TCL 32 इंच स्मार्ट LED TV",
        "description": "सेमसंग वॉशिंग मशीन 7 kg टॉप लोड / TCL 32 इंच स्मार्ट LED TV",
        "images": ["20000_1.png", "20000_2.png"],
        "items_summary": "Samsung 7kg Washing Machine, TCL 32 Smart LED TV"
    },
    {
        "tier": 4,
        "points": "30000",
        "value": "30000",
        "title": "सेमसंग 43 इंच 4K स्मार्ट टीवी / मोटोरोला एज 70 फ्यूजन",
        "description": "सेमसंग 43 इंच 4K स्मार्ट टीवी / मोटोरोला एज 70 फ्यूजन",
        "images": ["30000_1.png", "30000_2.png"],
        "items_summary": "Samsung 43 4K Smart TV, Motorola Edge 70 Fusion"
    },
    {
        "tier": 5,
        "points": "40000",
        "value": "40000",
        "title": "2.5 ग्राम 24K सोने का सिक्का / रजलेन 5, 16GB रैम, 512GB SSD / सेमसंग गैलेक्सी A56 5G",
        "description": "2.5 ग्राम 24K सोने का सिक्का / रजलेन 5, 16GB रैम, 512GB SSD / सेमसंग गैलेक्सी A56 5G",
        "images": ["40000_1.png", "40000_2.png", "40000_3.png"],
        "items_summary": "2.5g 24K Gold Coin, Ryzen 5 Laptop, Samsung Galaxy A56 5G"
    },
    {
        "tier": 6,
        "points": "50000",
        "value": "50000",
        "title": "ओरिएर एयर कंडीशनर 1.5-टन, 3-स्टार इन्वर्टर / नथिंग फोन",
        "description": "ओरिएर एयर कंडीशनर 1.5-टन, 3-स्टार इन्वर्टर / नथिंग फोन",
        "images": ["50000_1.png", "50000_2.png"],
        "items_summary": "1.5-Ton Inverter AC, Nothing Phone"
    },
    {
        "tier": 7,
        "points": "75000",
        "value": "75000",
        "title": "सोनी स्मार्ट टीवी 55 इंच / सेमसंग रेफ्रिजरेटर 467 L डबल डोर",
        "description": "सोनी स्मार्ट टीवी 55 इंच / सेमसंग रेफ्रिजरेटर 467 L डबल डोर",
        "images": ["75000_1.png", "75000_2.png"],
        "items_summary": "Sony 55 Smart TV, Samsung 467L Refrigerator"
    },
    {
        "tier": 8,
        "points": "100000",
        "value": "100000",
        "title": "एक्टिवा 125 / हीरो स्प्लेंडर प्लस",
        "description": "एक्टिवा 125 / हीरो स्प्लेंडर प्लस",
        "images": ["100000_1.png", "100000_2.png"],
        "items_summary": "Activa 125, Hero Splendor Plus"
    },
    {
        "tier": 9,
        "points": "200000",
        "value": "200000",
        "title": "आईफोन 18 प्रो मैक्स / इलेक्ट्रिक स्कूटर",
        "description": "आईफोन 18 प्रो मैक्स / इलेक्ट्रिक स्कूटर",
        "images": ["200000_1.png", "200000_2.png"],
        "items_summary": "iPhone 18 Pro Max, Electric Scooter"
    },
    {
        "tier": 10,
        "points": "300000",
        "value": "300000",
        "title": "बुलेट क्लासिक 350",
        "description": "बुलेट क्लासिक 350",
        "images": ["300000_1.png"],
        "items_summary": "Bullet Classic 350"
    },
    {
        "tier": 11,
        "points": "500000",
        "value": "500000",
        "title": "30 ग्राम सोना / मारुति सुजुकी ऑल्टो कार / टाटा टियागो कार",
        "description": "30 ग्राम सोना / मारुति सुजुकी ऑल्टो कार / टाटा टियागो कार",
        "images": ["500000_1.png", "500000_2.png", "500000_3.png"],
        "items_summary": "30g Gold, Maruti Alto Car, Tata Tiago Car"
    }
]

def get_homepride_dir() -> Path:
    possible = [
        Path(__file__).resolve().parent.parent / "homepride",
        Path(__file__).resolve().parent / "homepride",
        Path("homepride")
    ]
    for p in possible:
        if p.exists() and p.is_dir():
            return p
    p = Path(__file__).resolve().parent.parent / "homepride"
    p.mkdir(parents=True, exist_ok=True)
    return p

def run_homepride_gifts_upload(email=None, password=None):
    homepride_dir = get_homepride_dir()
    
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
    print("  🏠 HOMEPRIDE GIFT SCHEME AUTOMATION (11 Tiers / Multi-Image Offerings)")
    print("=" * 65)
    print(f"  Images Directory: {homepride_dir.absolute()}")
    print("-" * 65)

    # Validate all images per tier
    prepared_tiers = []
    total_images_count = 0

    for tier_info in HOMEPRIDE_SCHEME:
        tier_num = tier_info["tier"]
        pts = tier_info["points"]
        val = tier_info["value"]
        title = tier_info["title"]
        desc = tier_info["description"]
        
        valid_paths = []
        for img_name in tier_info["images"]:
            p = homepride_dir / img_name
            if p.exists():
                valid_paths.append(str(p.absolute()))
            else:
                logger.warning(f"⚠ Missing image: {img_name}")

        total_images_count += len(valid_paths)
        prepared_tiers.append({
            "tier": tier_num,
            "name": title,
            "description": desc,
            "points": pts,
            "value": val,
            "image_names": tier_info["images"],
            "image_paths": valid_paths
        })

    print(f"  Prepared 11 Offerings ({total_images_count} total images):")
    for t in prepared_tiers:
        img_str = ", ".join(t["image_names"])
        print(f"  Tier {t['tier']:2d} | {t['points']} Pts/₹ | {len(t['image_paths'])} images ({img_str}) | {t['name'][:35]}...")
    print("=" * 65)

    confirm = input("\n  Start uploading all 11 HomePride gift offerings (with multiple images)? (Y/n): ").strip().lower()
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

            # Check and fetch available user types
            available_user_types, is_multiple = gift_auto.get_available_user_types()
            if available_user_types:
                logger.info(f"Detected available target audience user types: {available_user_types}")
            else:
                logger.info("Using default target audience (all available options will be selected)")

            successful = 0
            failed = 0
            total = len(prepared_tiers)

            for idx, tier in enumerate(prepared_tiers, 1):
                img_names_str = ", ".join(tier["image_names"])
                logger.info(f"\n[{idx}/{total}] Uploading Tier {tier['tier']} | Points: {tier['points']} | Value: {tier['value']} | Images ({len(tier['image_paths'])}): {img_names_str}")
                print(f"  [{idx}/{total}] Uploading Tier {tier['tier']} (Points: {tier['points']}, {len(tier['image_paths'])} images: {img_names_str})...")

                gift_payload = {
                    "name": tier["name"],
                    "description": tier["description"],
                    "points": tier["points"],
                    "value": tier["value"],
                    "image_paths": tier["image_paths"]
                }

                if gift_auto.add_new_gift(gift_payload, target_user_types=available_user_types if available_user_types else None):
                    successful += 1
                    print(f"  ✓ Successfully created Tier {tier['tier']} offering with all {len(tier['image_paths'])} images!")
                else:
                    failed += 1
                    print(f"  ✗ Failed to upload Tier {tier['tier']}")

                time.sleep(2)

            print("\n" + "=" * 65)
            print("  🏠 HOMEPRIDE GIFTS UPLOAD SUMMARY")
            print("=" * 65)
            print(f"  Total Offerings Processed : {total}")
            print(f"  ✓ Successful Offerings   : {successful}")
            print(f"  ✗ Failed Offerings       : {failed}")
            print("=" * 65 + "\n")

            return failed == 0

    except Exception as e:
        logger.error(f"Unexpected error during HomePride gifts upload: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    run_homepride_gifts_upload()
