#!/usr/bin/env python3
"""
Main Runner Script for Dashboard Icons Automation
This script:
1. Processes and compresses images
2. Logs into vendor portal
3. Uploads all configured icons
4. Generates detailed logs and screenshots
"""

import getpass
import os
import sys
from pathlib import Path

# Add automation folder to path
sys.path.insert(0, str(Path(__file__).parent))

import logging
import time
from datetime import datetime

from banner_promotion import BannerAutomation, BannerImageProcessor
from brand_setting import (
    BrandImageProcessor,
    BrandSettingAutomation,
    extract_colors_from_logo,
)
from dashboard_automation import VendorPortalAutomation
from image_processor import ImageProcessor
from intro_screen import (
    IntroImageProcessor,
    IntroScreenAutomation,
    build_slides_custom,
    build_slides_default,
)
from registration_fields import RegistrationFieldsAutomation
from old_dashboard_migration import run_old_dashboard_migration, run_old_dashboard_banner_migration
from old_dashboard_brand_setting import run_old_dashboard_brand_setting
from product_catalogue_migration import run_product_catalogue_migration
from surie_product_upload import run_surie_product_upload
from gift_management import run_gift_management, run_narmada_gifts
from user_type_creation import UserTypeAutomation
from app_settings_analysis import run_app_settings_analysis

# Setup logging
log_dir = Path("automation/logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"full_automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║   DASHBOARD ICONS AUTOMATION                                ║
    ║   Vendor Portal Auto-Upload System                          ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info(banner)


def ask_credentials():
    """Prompt the user for login credentials at runtime."""
    print()
    print("  ─── Enter your vendor portal credentials ───")
    email = input("  Email    : ").strip()
    password = getpass.getpass("  Password : ")  # hidden while typing
    print()
    return email, password


def main(email=None, password=None):
    """Main execution flow"""
    print_banner()

    logger.info(
        f"Automation started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )

    # Step 1: Process Images
    logger.info("=" * 60)
    logger.info("STEP 1: Processing and Compressing Images")
    logger.info("=" * 60)

    input_dir = "dashboardicons"
    output_dir = "automation/processed_images"

    processor = ImageProcessor(input_dir, output_dir)
    processed_images = processor.process_all_images()

    if not processed_images:
        logger.error("No images were processed. Aborting.")
        return False

    logger.info(f"✓ {len(processed_images)} images processed and ready\n")

    # Step 2: Get credentials
    logger.info("=" * 60)
    logger.info("STEP 2: Preparing Authentication")
    logger.info("=" * 60)

    # Use credentials passed in, fall back to env variables
    if not email:
        email = os.getenv("VENDOR_EMAIL", "")
    if not password:
        password = os.getenv("VENDOR_PASSWORD", "")

    logger.info(f"Using email: {email}")
    logger.info("✓ Credentials loaded\n")

    # Target User Type selection
    print()
    print("  ─── Target User Type ───")
    print("  Specify which User Type should receive these dashboard icons.")
    print("  (Enter 'all' to upload for all user types, or leave blank for 'all')")
    target_user_type = input("  User Type: ").strip()
    if not target_user_type:
        target_user_type = "all"
    logger.info(f"Target User Type: {target_user_type}")
    print()

    # Step 3: Run Automation
    logger.info("=" * 60)
    logger.info("STEP 3: Launching Browser and Starting Upload Process")
    logger.info("=" * 60)

    try:
        with VendorPortalAutomation(email, password, headless=False) as automation:
            # Login
            logger.info("\n→ Attempting login...\n")
            if not automation.login():
                logger.error("✗ Login failed. Aborting.")
                return False

            time.sleep(2)

            # Navigate to dashboard icons
            logger.info("\n→ Navigating to dashboard icons section...\n")
            if not automation.navigate_to_dashboard_icons():
                logger.error("✗ Failed to navigate. Aborting.")
                return False

            time.sleep(2)

            # Load and process icons
            import json

            config_path = Path("automation/icon_config.json")

            with open(config_path, "r") as f:
                config = json.load(f)

            configured_icons = config.get("icons", [])
            icons_to_add = []
            for entry in configured_icons:
                new_entry = dict(entry)
                new_entry["user_type"] = target_user_type
                icons_to_add.append(new_entry)

            logger.info(f"\n→ Starting batch upload of {len(icons_to_add)} icons...\n")
            successful, failed = automation.process_icons_batch(icons_to_add)

            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("AUTOMATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ Successful uploads: {successful}")
            logger.info(f"✗ Failed uploads: {failed}")
            logger.info(f"Total processed: {len(icons_to_add)}")
            if icons_to_add:
                logger.info(f"Success rate: {(successful / len(icons_to_add) * 100):.1f}%")
            logger.info("=" * 60)

            return True

    except Exception as e:
        logger.error(f"Unexpected error during automation: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return False


# ══════════════════════════════════════════════════════════════
# Shared utility — find a file by base-name, any extension
# ══════════════════════════════════════════════════════════════
SUPPORTED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}


def find_brand_asset(folder, base_name):
    """
    Search *folder* for any image file whose stem matches *base_name*
    (case-insensitive, any supported extension).

    Examples
    --------
    find_brand_asset("brandsetting", "logo")   # finds logo.png OR logo.jpg etc.
    find_brand_asset("brandsetting", "splash")  # finds splash.png OR splash.jpeg etc.

    Returns the full path string on success, or None if not found.
    """
    folder = Path(folder)
    if not folder.exists():
        logger.error(f"Brand asset folder not found: {folder}")
        return None

    for f in folder.iterdir():
        if (
            f.suffix.lower() in SUPPORTED_IMAGE_EXT
            and f.stem.lower() == base_name.lower()
        ):
            logger.info(f"  Found {base_name} asset: {f.name}")
            return str(f)

    logger.error(
        f"No file named '{base_name}' found in {folder}/  "
        f"(checked extensions: {', '.join(sorted(SUPPORTED_IMAGE_EXT))})"
    )
    return None


# ══════════════════════════════════════════════════════════════
# Brand Setting runner  (fully separate from dashboard icons)
# ══════════════════════════════════════════════════════════════
def run_brand_setting(email, password):
    """Process brand images and update Identity & Branding on the portal."""
    import json

    # ── Ask company name at runtime ───────────────────────────
    print()
    company_name = input("  Company / App Name : ").strip()
    if not company_name:
        print("  ❌ Company name cannot be empty.\n")
        return False

    # ── Load brand config ─────────────────────────────────────
    cfg_path = Path("automation/brand_config.json")
    with open(cfg_path, "r") as f:
        cfg = json.load(f)

    # ── Dynamically find logo and splash by base-name (any extension) ─
    brand_folder = cfg.get("brand_folder", "brandsetting")
    logo_src = find_brand_asset(brand_folder, "logo")
    splash_src = find_brand_asset(brand_folder, "splash")

    if not logo_src:
        print(
            f"  ❌ No 'logo' image found in {brand_folder}/  "
            f"(e.g. logo.png, logo.jpg, logo.jpeg)"
        )
        return False
    if not splash_src:
        print(
            f"  ❌ No 'splash' image found in {brand_folder}/  "
            f"(e.g. splash.png, splash.jpg, splash.jpeg)"
        )
        return False

    # ── Process images ────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("BRAND SETTING — Image Processing")
    logger.info("=" * 60)

    processor = BrandImageProcessor()
    logo_path = processor.process_logo(logo_src)
    splash_path = processor.process_splash(splash_src)

    # ── Auto-extract colors from logo at runtime ─────────────
    logger.info("")
    logger.info("Extracting brand colours from logo...")
    colors = extract_colors_from_logo(logo_src)
    if not colors:
        logger.warning("Colour extraction failed — colours will not be applied.")
        colors = {}

    # Print palette clearly in the terminal
    print()
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │   Brand Palette  (auto-detected from logo)      │")
    print("  ├─────────────────────────────────────────────────┤")
    if colors:
        labels = {
            "header_color": "Header     ",
            "background_color": "Background ",
            "body_color": "Body       ",
            "footer_color": "Footer     ",
        }
        descs = {
            "header_color": "from logo",
            "background_color": "35% darker",
            "body_color": "always white",
            "footer_color": "always light",
        }
        for key, label in labels.items():
            val = colors.get(key, "")
            desc = descs.get(key, "")
            print(f"  │   {label} {val}   {desc:20s} │")
    print("  └─────────────────────────────────────────────────┘")
    print()

    if not logo_path:
        logger.error("Logo could not be processed. Aborting brand setting.")
        return False
    if not splash_path:
        logger.error("Splash could not be processed. Aborting brand setting.")
        return False

    logger.info("✓ Both images ready\n")

    # ── Run browser automation ────────────────────────────────
    logger.info("=" * 60)
    logger.info("BRAND SETTING — Browser Automation")
    logger.info("=" * 60)

    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                logger.error("✗ Login failed. Aborting.")
                return False

            time.sleep(2)

            brand = BrandSettingAutomation(auto.driver)

            if not brand.navigate():
                logger.error("✗ Navigation failed. Aborting.")
                return False

            success = brand.fill_and_save(
                company_name=company_name,
                logo_path=logo_path,
                splash_path=splash_path,
                colors=colors,
            )
            return success

    except Exception as e:
        logger.error(f"Unexpected error in brand setting: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


# ══════════════════════════════════════════════════════════════
# Promotion Banners runner  (fully separate from other features)
# ══════════════════════════════════════════════════════════════
def run_promotion_banners(email, password):
    """Process all images in banner/ folder and publish them."""

    # ── Process images ────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PROMOTION BANNERS — Image Processing")
    logger.info("=" * 60)

    processor = BannerImageProcessor()
    banners = processor.process_all(folder="banner")

    if not banners:
        logger.error("No banner images could be processed. Aborting.")
        return False

    # Print what will be published
    print()
    print("  ┌─────────────────────────────────────────────────┐")
    print(f"  │   Banners ready to publish: {len(banners):<22}│")
    print("  ├─────────────────────────────────────────────────┤")
    for i, (title, path) in enumerate(banners, 1):
        mb = Path(path).stat().st_size / (1024 * 1024)
        print(f"  │  {i}. {title:<30}  {mb:.2f} MB  │")
    print("  └─────────────────────────────────────────────────┘")
    print()

    # ── Browser automation ────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PROMOTION BANNERS — Browser Automation")
    logger.info("=" * 60)

    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                logger.error("✗ Login failed. Aborting.")
                return False

            time.sleep(2)

            banner_auto = BannerAutomation(auto.driver)

            if not banner_auto.navigate():
                logger.error("✗ Navigation failed. Aborting.")
                return False

            successful, failed = banner_auto.publish_all(banners)
            return failed == 0

    except Exception as e:
        logger.error(f"Unexpected error in banner automation: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


# ══════════════════════════════════════════════════════════════
# Intro Screens runner  (fully separate from other features)
# ══════════════════════════════════════════════════════════════
def run_intro_screens(email, password):
    """Process all images in introscreen/ folder and launch them as intro screens."""

    # ── Process images ────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("INTRO SCREENS — Image Processing")
    logger.info("=" * 60)

    processor = IntroImageProcessor()
    image_paths = processor.process_all(folder="introscreen")

    if not image_paths:
        logger.error("No intro screen images could be processed. Aborting.")
        return False

    # ── Ask: default or custom content ───────────────────────
    print()
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │   Intro Screen Content                           │")
    print("  ├─────────────────────────────────────────────────┤")
    print("  │   D : Use default headers & descriptions         │")
    print("  │   C : Enter custom headers & descriptions        │")
    print("  └─────────────────────────────────────────────────┘")
    print()

    content_choice = input("  Your choice (D / C) : ").strip().upper()

    if content_choice == "D":
        slides = build_slides_default(image_paths)
        print()
        print("  ┌─────────────────────────────────────────────────┐")
        print(f"  │  Slides to launch: {len(slides):<30}│")
        print("  ├─────────────────────────────────────────────────┤")
        for i, s in enumerate(slides, 1):
            print(f"  │  {i}. {s['header']:<45}│")
        print("  └─────────────────────────────────────────────────┘")
        print()
    elif content_choice == "C":
        slides = build_slides_custom(image_paths)
    else:
        print("  ❌ Invalid choice. Using default content.")
        slides = build_slides_default(image_paths)

    # ── Browser automation ────────────────────────────────────
    logger.info("=" * 60)
    logger.info("INTRO SCREENS — Browser Automation")
    logger.info("=" * 60)

    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                logger.error("✗ Login failed. Aborting.")
                return False

            time.sleep(2)

            intro_auto = IntroScreenAutomation(auto.driver)

            if not intro_auto.navigate():
                logger.error("✗ Navigation failed. Aborting.")
                return False

            successful, failed = intro_auto.launch_all(slides)
            return failed == 0

    except Exception as e:
        logger.error(f"Unexpected error in intro screens automation: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


# ══════════════════════════════════════════════════════════════
# Registration Fields runner
# ══════════════════════════════════════════════════════════════
def run_registration_fields(email, password):
    """Add mandatory registration fields for all user types."""
    logger.info("=" * 60)
    logger.info("REGISTRATION FIELDS — Browser Automation")
    logger.info("=" * 60)

    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                logger.error("✗ Login failed. Aborting.")
                return False

            time.sleep(2)

            reg_auto = RegistrationFieldsAutomation(auto.driver)

            if not reg_auto.navigate():
                logger.error("✗ Navigation failed. Aborting.")
                return False

            success = reg_auto.process_all()
            return success

    except Exception as e:
        logger.error(f"Unexpected error in registration fields automation: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


# ══════════════════════════════════════════════════════════════
# Registration Fields (Specific User Types) runner  (Option 13)
# ══════════════════════════════════════════════════════════════
def run_registration_fields_specific(email, password):
    """
    Add mandatory registration fields but ONLY for specific user types
    chosen interactively by the operator (same fields as Option 5).
    """
    print()
    print("  ─── Registration Fields — Specific User Types ───")

    # 1. Ask how many user types
    while True:
        try:
            num_input = input("  How many user types do you want to process? ").strip()
            if not num_input:
                print("  ❌ Number cannot be empty.")
                continue
            num_users = int(num_input)
            if num_users <= 0:
                print("  ❌ Please enter a positive integer.")
                continue
            break
        except ValueError:
            print("  ❌ Invalid number. Please enter an integer.")

    # 2. Collect user type names one-by-one
    target_user_types = []
    for i in range(num_users):
        while True:
            name = input(f"  Enter User Type #{i + 1} Name: ").strip()
            if not name:
                print("  ❌ Name cannot be empty.")
                continue
            if name.lower() in [u.lower() for u in target_user_types]:
                print("  ❌ Name already entered. Please use a unique name.")
                continue
            target_user_types.append(name)
            break

    logger.info(f"Requested user types for registration fields: {target_user_types}")

    logger.info("=" * 60)
    logger.info("REGISTRATION FIELDS (SPECIFIC) — Browser Automation")
    logger.info("=" * 60)

    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                logger.error("✗ Login failed. Aborting.")
                return False

            time.sleep(2)

            reg_auto = RegistrationFieldsAutomation(auto.driver)

            if not reg_auto.navigate():
                logger.error("✗ Navigation failed. Aborting.")
                return False

            success = reg_auto.process_specific(target_user_types)
            return success

    except Exception as e:
        logger.error(f"Unexpected error in registration fields (specific) automation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_create_user_types(email, password):
    """Prompt user for user type details, create them on the portal, and upload dashboard icons only for them."""
    print()
    print("  ─── Create User Types & Upload Icons ───")
    
    # 1. Ask how many user types to create
    while True:
        try:
            num_input = input("  How many user types need to be created? ").strip()
            if not num_input:
                print("  ❌ Number cannot be empty.")
                continue
            num_users = int(num_input)
            if num_users <= 0:
                print("  ❌ Please enter a positive integer.")
                continue
            break
        except ValueError:
            print("  ❌ Invalid number. Please enter an integer.")

    # 2. Input user names one by one
    user_names = []
    for i in range(num_users):
        while True:
            name = input(f"  Enter User Type #{i+1} Name: ").strip()
            if not name:
                print("  ❌ Name cannot be empty.")
                continue
            if name in user_names:
                print("  ❌ Name already entered. Please use a unique name.")
                continue
            user_names.append(name)
            break

    logger.info(f"User types to be created: {user_names}")

    # 3. Process dashboard icons first (resizing/compression) to make sure they are ready
    logger.info("=" * 60)
    logger.info("STEP 1: Processing and Compressing Images")
    logger.info("=" * 60)

    input_dir = "dashboardicons"
    output_dir = "automation/processed_images"

    processor = ImageProcessor(input_dir, output_dir)
    processed_images = processor.process_all_images()

    if not processed_images:
        logger.error("No images were processed. Aborting.")
        return False

    logger.info(f"✓ {len(processed_images)} images processed and ready\n")

    # 4. Launch browser automation
    logger.info("=" * 60)
    logger.info("STEP 2: Creating User Types & Uploading Icons")
    logger.info("=" * 60)

    try:
        with VendorPortalAutomation(email, password, headless=False) as automation:
            # Login
            logger.info("\n→ Attempting login...\n")
            if not automation.login():
                logger.error("✗ Login failed. Aborting.")
                return False

            time.sleep(2)

            # Navigate to User Type settings and create each user type
            user_type_auto = UserTypeAutomation(automation.driver)
            if not user_type_auto.navigate():
                logger.error("✗ Failed to navigate to User Type settings. Aborting.")
                return False

            created_successfully = []
            for name in user_names:
                if user_type_auto.create_user_type(name):
                    created_successfully.append(name)
                else:
                    logger.warning(f"⚠ Failed to create user type '{name}'")

            if not created_successfully:
                logger.error("✗ No user types were created. Aborting icon upload.")
                return False

            logger.info(f"Successfully created user types: {created_successfully}")
            time.sleep(2)

            # Navigate to dashboard icons section
            logger.info("\n→ Navigating to dashboard icons section...\n")
            if not automation.navigate_to_dashboard_icons():
                logger.error("✗ Failed to navigate. Aborting.")
                return False

            time.sleep(2)

            # Load icons configuration
            import json
            config_path = Path("automation/icon_config.json")
            with open(config_path, "r") as f:
                config = json.load(f)

            configured_icons = config.get("icons", [])

            # Map the configured icons list to target ONLY the newly created user types
            icons_to_add = []
            for entry in configured_icons:
                for new_utype in created_successfully:
                    new_entry = dict(entry)
                    new_entry["user_type"] = new_utype
                    icons_to_add.append(new_entry)

            logger.info(f"\n→ Starting batch upload of {len(icons_to_add)} icons for {len(created_successfully)} user types...\n")
            successful, failed = automation.process_icons_batch(icons_to_add)

            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("USER TYPE CREATION & ICON UPLOAD SUMMARY")
            logger.info("=" * 60)
            logger.info(f"User types created: {created_successfully}")
            logger.info(f"✓ Successful uploads: {successful}")
            logger.info(f"✗ Failed uploads: {failed}")
            logger.info(f"Total processed: {len(icons_to_add)}")
            if icons_to_add:
                logger.info(f"Success rate: {(successful / len(icons_to_add) * 100):.1f}%")
            logger.info("=" * 60)

            return failed == 0

    except Exception as e:
        logger.error(f"Unexpected error in create user types automation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


# ══════════════════════════════════════════════════════════════
# Dynamic Dashboard Icons Custom Flow (Option 11)
# ══════════════════════════════════════════════════════════════

FILENAME_TO_ICON_IDENTITY = {
    "rewards": "gift",
    "blog": "blog",
    "update": "blog",
    "updates": "blog",
    "installation guide": "instalment",
    "instalment": "instalment",
    "kyc": "kycdetails",
    "kyc details": "kycdetails",
    "language": "chooselanguage",
    "choose language": "chooselanguage",
    "wallet": "wallet",
    "my wallet": "wallet",
    "nearby retailer": "retailer",
    "nearby retailers": "retailer",
    "retailer": "retailer",
    "product catalog": "productcatalogue",
    "product catalogue": "productcatalogue",
    "prospectus": "brochure",
    "brochure": "brochure",
    "refer and earn": "referandearn",
    "refer & earn": "referandearn",
    "referandearn": "referandearn",
    "scan activity": "codedetails",
    "code details": "codedetails",
    "scan history": "history",
    "history": "history",
    "send points": "transferpoints",
    "transfer points": "transferpoints",
    "support": "help",
    "help": "help",
    "tds": "tds",
    "claim history": "claimhistory",
    "e-warranty": "e-warrant",
    "ewarranty": "e-warrant",
}


def get_icon_identity(filename_stem: str) -> str:
    """Fuzzy/substring match filename stem to available dropdown values."""
    stem_lower = filename_stem.lower().strip()
    if stem_lower in FILENAME_TO_ICON_IDENTITY:
        return FILENAME_TO_ICON_IDENTITY[stem_lower]
    for key, val in FILENAME_TO_ICON_IDENTITY.items():
        if key in stem_lower or stem_lower in key:
            return val
    return "gift"


def get_toggle_option(filename_stem: str) -> str:
    """Determine portal toggle selection based on filename stem."""
    stem_lower = filename_stem.lower().strip()
    # Both
    if any(x in stem_lower for x in ["rewards", "refer", "wallet"]):
        return "both"
    # Side menu
    elif any(x in stem_lower for x in ["kyc", "language", "claim", "tds"]):
        return "side menu"
    # Dashboard only
    else:
        return "dashboard only"


def extract_dominant_color(image_path) -> str:
    """Extract the dominant saturated color from an image. Returns hex string."""
    try:
        from PIL import Image
        from collections import Counter
        img = Image.open(image_path).convert("RGB")
        img.thumbnail((100, 100))
        pixels = list(img.getdata())
        
        saturated = []
        for r, g, b in pixels:
            brightness = (r + g + b) / 3
            mx = max(r, g, b)
            mn = min(r, g, b)
            saturation = (mx - mn) / (mx + 1)
            
            # Filter for vibrant/saturated colors
            if saturation > 0.15 and 30 < brightness < 225:
                saturated.append((r // 8 * 8, g // 8 * 8, b // 8 * 8))
                
        if saturated:
            dominant = Counter(saturated).most_common(1)[0][0]
            return f"#{dominant[0]:02X}{dominant[1]:02X}{dominant[2]:02X}"
            
        # Fallback to general dominant pixel excluding extreme white/black
        filtered_pixels = [p for p in pixels if not (p[0] > 240 and p[1] > 240 and p[2] > 240) and not (p[0] < 15 and p[1] < 15 and p[2] < 15)]
        if filtered_pixels:
            dominant = Counter(filtered_pixels).most_common(1)[0][0]
        else:
            dominant = Counter(pixels).most_common(1)[0][0]
            
        return f"#{dominant[0]:02X}{dominant[1]:02X}{dominant[2]:02X}"
    except Exception as e:
        logger.error(f"Error extracting color from {image_path}: {e}")
        return "#4F46E5"


def find_matching_processed_image(entered_name: str, processed_images: dict):
    """
    Finds a processed image whose filename stem (case-insensitive) matches the entered_name.
    Also supports partial/fuzzy match.
    """
    name_lower = entered_name.lower().strip()
    # 1. Exact stem match
    for orig_filename, processed_path in processed_images.items():
        stem = Path(orig_filename).stem.lower().strip()
        if stem == name_lower:
            return orig_filename, processed_path
            
    # 2. Substring match
    for orig_filename, processed_path in processed_images.items():
        stem = Path(orig_filename).stem.lower().strip()
        if name_lower in stem or stem in name_lower:
            return orig_filename, processed_path
            
    # 3. Replace 'and' with '&' or vice-versa and try matching
    normalized_name = name_lower.replace("and", "&").replace("  ", " ").strip()
    for orig_filename, processed_path in processed_images.items():
        stem = Path(orig_filename).stem.lower().replace("and", "&").replace("  ", " ").strip()
        if stem == normalized_name or normalized_name in stem or stem in normalized_name:
            return orig_filename, processed_path

    return None, None


def run_dashboard_icons_specific_user_types(email, password) -> bool:
    """
    Upload specific dashboard icons for specific user types.
    """
    print()
    print("  ─── Add Specific Dashboard Icons to Specific User Types ───")

    # 1. Ask how many user types
    while True:
        try:
            num_input = input("  How many user types do you want to process? ").strip()
            if not num_input:
                print("  ❌ Number cannot be empty.")
                continue
            num_users = int(num_input)
            if num_users <= 0:
                print("  ❌ Please enter a positive integer.")
                continue
            break
        except ValueError:
            print("  ❌ Invalid number. Please enter an integer.")

    # 2. Collect user type names one-by-one
    target_user_types = []
    for i in range(num_users):
        while True:
            name = input(f"  Enter User Type #{i + 1} Name: ").strip()
            if not name:
                print("  ❌ Name cannot be empty.")
                continue
            if name.lower() in [u.lower() for u in target_user_types]:
                print("  ❌ Name already entered. Please use a unique name.")
                continue
            target_user_types.append(name)
            break

    # 3. Ask how many dashboard icons
    while True:
        try:
            num_input = input("  How many dashboard icons do you want to upload? ").strip()
            if not num_input:
                print("  ❌ Number cannot be empty.")
                continue
            num_icons = int(num_input)
            if num_icons <= 0:
                print("  ❌ Please enter a positive integer.")
                continue
            break
        except ValueError:
            print("  ❌ Invalid number. Please enter an integer.")

    # 4. Collect dashboard icon names one-by-one
    target_icon_names = []
    for i in range(num_icons):
        while True:
            name = input(f"  Enter Dashboard Icon #{i + 1} Name: ").strip()
            if not name:
                print("  ❌ Name cannot be empty.")
                continue
            if name.lower() in [ic.lower() for ic in target_icon_names]:
                print("  ❌ Icon name already entered. Please use a unique name.")
                continue
            target_icon_names.append(name)
            break

    logger.info(f"Target User Types: {target_user_types}")
    logger.info(f"Target Dashboard Icons: {target_icon_names}")

    # 5. Process all images from dashboardicons
    input_dir = "dashboardicons"
    output_dir = "automation/processed_images"

    processor = ImageProcessor(input_dir, output_dir)
    processed_images = processor.process_all_images()

    if not processed_images:
        logger.error("No images were processed from 'dashboardicons/'. Aborting.")
        return False

    # 6. Map each requested icon name to processed images
    matched_icons = []
    for entered_name in target_icon_names:
        orig_filename, processed_path = find_matching_processed_image(entered_name, processed_images)
        if not processed_path:
            logger.warning(f"⚠ Could not find any matching image for icon name: '{entered_name}' in dashboardicons/")
            print(f"  ⚠ Skipping unknown icon: '{entered_name}'")
            continue
        
        stem = Path(orig_filename).stem
        display_title = stem
        icon_identity = get_icon_identity(stem)
        icon_color = extract_dominant_color(processed_path)
        toggle_option = get_toggle_option(stem)
        
        matched_icons.append({
            "orig_filename": orig_filename,
            "processed_path": processed_path,
            "display_title": display_title,
            "icon_identity": icon_identity,
            "icon_color": icon_color,
            "toggle_option": toggle_option
        })

    if not matched_icons:
        logger.error("No matching dashboard icons were found. Aborting.")
        return False

    # 7. Construct icons to add for each user type
    icons_to_add = []
    for utype in target_user_types:
        for icon in matched_icons:
            icons_to_add.append({
                "user_type": utype,
                "icon_identity": icon["icon_identity"],
                "display_title": icon["display_title"],
                "image_path": icon["processed_path"],
                "toggle_option": icon["toggle_option"],
                "icon_color": icon["icon_color"]
            })

    logger.info(f"Generated {len(icons_to_add)} upload tasks for {len(target_user_types)} user types.")

    # 8. Launch browser automation
    logger.info("\n" + "=" * 60)
    logger.info("Launching Browser and Starting Upload Process")
    logger.info("=" * 60)

    try:
        with VendorPortalAutomation(email, password, headless=False) as automation:
            # Login
            logger.info("\n→ Attempting login...\n")
            if not automation.login():
                logger.error("✗ Login failed. Aborting.")
                return False

            time.sleep(2)

            # Navigate to dashboard icons
            logger.info("\n→ Navigating to dashboard icons section...\n")
            if not automation.navigate_to_dashboard_icons():
                logger.error("✗ Failed to navigate. Aborting.")
                return False

            time.sleep(2)

            logger.info(f"\n→ Starting batch upload of {len(icons_to_add)} custom icons...\n")
            successful, failed = automation.process_icons_batch(icons_to_add)

            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("SPECIFIC ICONS AUTOMATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ Successful uploads: {successful}")
            logger.info(f"✗ Failed uploads: {failed}")
            logger.info(f"Total processed: {len(icons_to_add)}")
            if icons_to_add:
                logger.info(f"Success rate: {(successful / len(icons_to_add) * 100):.1f}%")
            logger.info("=" * 60)

            return failed == 0

    except Exception as e:
        logger.error(f"Unexpected error during specific dashboard automation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_dashboard_icons_auto(email, password) -> bool:
    """Compress icons from dashboardicons/, extract info and upload to portal."""
    logger.info("=" * 60)
    logger.info("Custom Dashboard Icons Upload (Option 11)")
    logger.info("=" * 60)

    input_dir = "dashboardicons"
    output_dir = "automation/processed_images"

    processor = ImageProcessor(input_dir, output_dir)
    processed_images = processor.process_all_images()

    if not processed_images:
        logger.error("No images were processed from 'dashboardicons/'. Aborting.")
        return False

    logger.info(f"✓ {len(processed_images)} images processed successfully.\n")

    # Prompt for Target User Type
    print()
    print("  ─── Target User Type ───")
    print("  Specify which User Type should receive these dashboard icons.")
    print("  (Enter 'all' to upload for all user types, or leave blank for 'all')")
    target_user_type = input("  User Type: ").strip()
    if not target_user_type:
        target_user_type = "all"
    logger.info(f"Target User Type: {target_user_type}")
    print()

    # Build dynamically mapped configurations
    icons_to_add = []
    for filename, processed_path in processed_images.items():
        stem = Path(filename).stem
        display_title = stem
        icon_identity = get_icon_identity(stem)
        icon_color = extract_dominant_color(processed_path)
        toggle_option = get_toggle_option(stem)

        logger.info(f"Dynamically mapped image '{filename}':")
        logger.info(f"  → Extracted Title: {display_title}")
        logger.info(f"  → Matched Identity: {icon_identity}")
        logger.info(f"  → Extracted Color: {icon_color}")
        logger.info(f"  → Toggle Option: {toggle_option}")

        icons_to_add.append({
            "user_type": target_user_type,
            "icon_identity": icon_identity,
            "display_title": display_title,
            "image_path": processed_path,
            "toggle_option": toggle_option,
            "icon_color": icon_color
        })

    # Launch automation
    logger.info("\n" + "=" * 60)
    logger.info("Launching Browser and Starting Upload Process")
    logger.info("=" * 60)

    try:
        with VendorPortalAutomation(email, password, headless=False) as automation:
            # Login
            logger.info("\n→ Attempting login...\n")
            if not automation.login():
                logger.error("✗ Login failed. Aborting.")
                return False

            time.sleep(2)

            # Navigate to dashboard icons
            logger.info("\n→ Navigating to dashboard icons section...\n")
            if not automation.navigate_to_dashboard_icons():
                logger.error("✗ Failed to navigate. Aborting.")
                return False

            time.sleep(2)

            logger.info(f"\n→ Starting batch upload of {len(icons_to_add)} custom icons...\n")
            successful, failed = automation.process_icons_batch(icons_to_add)

            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("CUSTOM AUTOMATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ Successful uploads: {successful}")
            logger.info(f"✗ Failed uploads: {failed}")
            logger.info(f"Total processed: {len(icons_to_add)}")
            if icons_to_add:
                logger.info(f"Success rate: {(successful / len(icons_to_add) * 100):.1f}%")
            logger.info("=" * 60)

            return failed == 0

    except Exception as e:
        logger.error(f"Unexpected error during dynamic dashboard automation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def show_old_dashboard_menu() -> str:
    """
    Sub-menu for Old Dashboard operations.
    Returns the user's sub-choice as a string.
    """
    print()
    print("  ╔══════════════════════════════════════════════════════════╗")
    print("  ║          OLD DASHBOARD — Select Operation               ║")
    print("  ╠══════════════════════════════════════════════════════════╣")
    print("  ║                                                          ║")
    print("  ║   Press 1 : Brand Setting      (Logo / Splash / Name)   ║")
    print("  ║   Press 2 : Introduction Setting                         ║")
    print("  ║   Press 3 : Banner BL          (coming soon)             ║")
    print("  ║   Press 4 : Product Catalogue  (coming soon)             ║")
    print("  ║   Press 0 : Back to Main Menu                            ║")
    print("  ║                                                          ║")
    print("  ╚══════════════════════════════════════════════════════════╝")
    print()
    return input("  Select task: ").strip()


def show_menu():
    """
    Main menu — add new options here in the future.
    Returns the user's choice as a string.
    """
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          VCQRU VENDOR PORTAL — AUTOMATION MENU              ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║                                                              ║")
    print("║   Press 1 : Dashboard Icons                                  ║")
    print("║   Press 2 : Brand Setting  (Identity & Branding)             ║")
    print("║   Press 3 : Promotion Banners                                ║")
    print("║   Press 4 : Intro Screens                                    ║")
    print("║   Press 5 : Registration Fields                              ║")
    print("║   Press 6 : Old Dashboard                                    ║")
    print("║   Press 7 : Surie Product Upload                             ║")
    print("║   Press 8 : Gift Management                                  ║")
    print("║   Press 9 : Create User Type                                 ║")
    print("║   Press 11: Dynamic Dashboard Icons (Auto Name & Color)      ║")
    print("║   Press 12: Add Narmada Gifts                                ║")
    print("║   Press 13: Registration Fields (Specific User Types)        ║")
    print("║   Press 14: Add Specific Icons to Specific User Types        ║")
    print("║   Press 17: Analyze App Settings (Identity, Support & Icons) ║")
    print("║   Press 0 : Exit                                             ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    return input("  Enter your choice: ").strip()


if __name__ == "__main__":
    try:
        # Check environment variables first, fall back to interactive prompting
        email = os.getenv("VENDOR_EMAIL", "").strip()
        password = os.getenv("VENDOR_PASSWORD", "").strip()
        if not email or not password:
            email, password = ask_credentials()
            
        if not email or not password:
            print("  ❌ Email or password cannot be empty.\n")
            sys.exit(1)

        is_unattended = os.getenv("AUTOMATION_CHOICE") is not None
        while True:  # ← keep looping until user quits
            if is_unattended:
                choice = os.getenv("AUTOMATION_CHOICE", "").strip()
            else:
                choice = show_menu()

            # ── Exit ──────────────────────────────────────────────────
            if choice == "0":
                print("\n  Goodbye! 👋\n")
                # Credentials will disappear from memory when the process exits
                sys.exit(0)

            # ── Invalid ───────────────────────────────────────────────
            elif choice not in {"1", "2", "3", "4", "5", "6", "7", "8", "9", "11", "12", "13", "14", "17"}:
                print(
                    f"\n  ❌ Invalid choice '{choice}'. Please enter a valid option.\n"
                )
                continue  # show menu again immediately

            # ── Run selected task ─────────────────────────────────────
            if choice == "1":
                logger.info("User selected: Dashboard Icons")
                success = run_dashboard_icons_auto(email, password)

            elif choice == "2":
                logger.info("User selected: Brand Setting")
                success = run_brand_setting(email, password)

            elif choice == "3":
                logger.info("User selected: Promotion Banners")
                success = run_promotion_banners(email, password)

            elif choice == "4":
                logger.info("User selected: Intro Screens")
                success = run_intro_screens(email, password)

            elif choice == "5":
                logger.info("User selected: Registration Fields")
                success = run_registration_fields(email, password)

            elif choice == "6":
                logger.info("User selected: Old Dashboard")
                sub_choice = show_old_dashboard_menu()

                if sub_choice == "0":
                    # Go back to main menu without marking success/failure
                    continue

                elif sub_choice == "1":
                    # ── Brand Setting — extract logo, splash & company name ──
                    logger.info("  Old Dashboard → Brand Setting")
                    success = run_old_dashboard_brand_setting(email, password)

                elif sub_choice == "2":
                    # ── Introduction Setting — migrate intro screens ─────────
                    logger.info("  Old Dashboard → Introduction Setting")
                    success = run_old_dashboard_migration(email, password)

                elif sub_choice == "3":
                    # ── Banner BL ───────────────────────────────────────────
                    logger.info("  Old Dashboard → Banner BL")
                    success = run_old_dashboard_banner_migration(email, password)

                elif sub_choice == "4":
                    # ── Product Catalogue ───────────────────────────────────
                    logger.info("  Old Dashboard → Product Catalogue")
                    success = run_product_catalogue_migration(email, password)

                else:
                    print(f"\n  ❌ Invalid sub-choice '{sub_choice}'.\n")
                    success = False

            elif choice == "7":
                logger.info("User selected: Surie Product Upload")
                success = run_surie_product_upload(email, password)

            elif choice == "8":
                logger.info("User selected: Gift Management")
                # Find image in gift/ folder
                gift_folder = Path("gift")
                gift_images = list(gift_folder.glob("*.png")) + list(gift_folder.glob("*.jpg")) + list(gift_folder.glob("*.jpeg"))
                if not gift_images:
                    print("\n  ❌ No images found in gift/ folder.\n")
                    success = False
                else:
                    image_path = gift_images[0]
                    success = run_gift_management(email, password, image_path)

            elif choice == "9":
                logger.info("User selected: Create User Type")
                success = run_create_user_types(email, password)

            elif choice == "11":
                logger.info("User selected: Dynamic Dashboard Icons (Auto Name & Color)")
                success = run_dashboard_icons_auto(email, password)

            elif choice == "12":
                logger.info("User selected: Add Narmada Gifts")
                success = run_narmada_gifts(email, password)

            elif choice == "13":
                logger.info("User selected: Registration Fields (Specific User Types)")
                success = run_registration_fields_specific(email, password)

            elif choice == "14":
                logger.info("User selected: Add Specific Icons to Specific User Types")
                success = run_dashboard_icons_specific_user_types(email, password)

            elif choice == "17":
                logger.info("User selected: Analyze App Settings (Identity, Support & Icons)")
                success = run_app_settings_analysis(email, password)

            # ── Result summary ────────────────────────────────────────
            logger.info(
                f"\nTask finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            logger.info(f"Log: {log_file}\n")

            if success:
                print("\n  ✓ Task completed successfully!")
                print(f"  Logs: automation/logs/\n")
            else:
                print("\n  ✗ Task completed with errors.")
                print(f"  Logs: automation/logs/\n")

            if is_unattended:
                sys.exit(0 if success else 1)

            # loop continues → menu shown again automatically

    except KeyboardInterrupt:
        print("\n\n  Interrupted. Goodbye! 👋\n")
        logger.info("Automation cancelled by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
