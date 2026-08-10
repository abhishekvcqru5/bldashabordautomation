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
from old_dashboard_migration import run_old_dashboard_migration, run_old_dashboard_banner_migration, run_old_dashboard_gift_migration
from old_dashboard_brand_setting import run_old_dashboard_brand_setting
from product_catalogue_migration import run_product_catalogue_migration
from surie_product_upload import run_surie_product_upload
from gift_management import run_gift_management, run_narmada_gifts
from user_type_creation import UserTypeAutomation
from app_settings_analysis import run_app_settings_analysis
from product_management_upload import run_product_management_upload
from ambica_product_upload import run_ambica_product_upload
from ambica_product_image_updater import run_ambica_image_updater

# Setup logging
log_dir = Path(__file__).resolve().parent / "logs"
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

    input_dir = str(Path(__file__).resolve().parent.parent / "dashboardicons")
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

            config_path = Path(__file__).resolve().parent / "icon_config.json"

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
    cfg_path = Path(__file__).resolve().parent / "brand_config.json"
    with open(cfg_path, "r") as f:
        cfg = json.load(f)

    # ── Dynamically find logo and splash by base-name (any extension) ─
    brand_folder_name = cfg.get("brand_folder", "brandsetting")
    brand_folder = Path(__file__).resolve().parent.parent / brand_folder_name
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
    banners = processor.process_all(folder=Path(__file__).resolve().parent.parent / "banner")

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
    image_paths = processor.process_all(folder=Path(__file__).resolve().parent.parent / "introscreen")

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

    input_dir = str(Path(__file__).resolve().parent.parent / "dashboardicons")
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
            config_path = Path(__file__).resolve().parent / "icon_config.json"
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
    "activity": "claimhistory",
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
    "ecommerce": "ecommerce",
    "e-commerce": "ecommerce",
    "e commerce": "ecommerce",
    "share point": "transferpoints",
    "sharepoint": "transferpoints",
    "aboutus": "aboutus",
    "about us": "aboutus",
    "contactus": "contactus",
    "contact us": "contactus",
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
    elif any(x in stem_lower for x in ["kyc", "language", "claim", "tds", "about"]):
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
    input_dir = str(Path(__file__).resolve().parent.parent / "dashboardicons")
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

    input_dir = str(Path(__file__).resolve().parent.parent / "dashboardicons")
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


def download_sheet_credentials() -> list:
    """Download Google Sheet CSV and extract credentials."""
    import urllib.request
    import csv
    
    url = "https://docs.google.com/spreadsheets/d/13WzwuUF6GY7mi5FPh-ISZdAAWX_a3DCsmnn4clnRk0g/export?format=csv&gid=0"
    logger.info(f"Downloading credentials from Google Sheet: {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            lines = [line.decode('utf-8') for line in response.readlines()]
            reader = csv.reader(lines)
            rows = list(reader)
            
            if not rows:
                logger.error("Google Sheet is empty.")
                return []
                
            # Parse headers
            headers = [h.strip().lower() for h in rows[0]]
            
            # Find column indices
            email_idx = -1
            password_idx = -1
            company_idx = -1
            
            for idx, h in enumerate(headers):
                if 'email' in h:
                    email_idx = idx
                elif 'password' in h or 'pass' in h:
                    password_idx = idx
                elif 'company' in h or 'name' in h:
                    company_idx = idx
                    
            if email_idx == -1 or password_idx == -1:
                logger.error("Could not find email or password columns in Google Sheet headers.")
                return []
                
            credentials = []
            for row in rows[1:]:
                if (email_idx != -1 and len(row) > email_idx) and \
                   (password_idx != -1 and len(row) > password_idx) and \
                   (company_idx != -1 and len(row) > company_idx):
                    email = row[email_idx].strip()
                    password = row[password_idx].strip()
                    company = row[company_idx].strip()
                    if email and password and company:
                        credentials.append({
                            "company": company,
                            "email": email,
                            "password": password
                        })
            logger.info(f"Found {len(credentials)} credential sets (fully populated) in Google Sheet.")
            return credentials
    except Exception as e:
        logger.error(f"Failed to download Google Sheet: {e}")
        return []


def run_single_update(email, password, target_user_type=None, target_icon_id=None) -> bool:
    """Run update of dashboard icons for a single vendor portal account."""
    logger.info("=" * 60)
    logger.info(f"UPDATING DASHBOARD ICONS FOR: {email}")
    if target_user_type or target_icon_id:
        logger.info(f"Filters applied -> User Type: {target_user_type}, Icon ID: {target_icon_id}")
    logger.info("=" * 60)

    # 1. Process local images first
    input_dir = str(Path(__file__).resolve().parent.parent / "dashboardicons")
    output_dir = "automation/processed_images"

    logger.info("Processing images from dashboardicons/...")
    processor = ImageProcessor(input_dir, output_dir)
    processed_images = processor.process_all_images()

    if not processed_images:
        logger.error("No images processed. Aborting update.")
        return False

    logger.info(f"✓ {len(processed_images)} images processed.")

    # 2. Build local files list with stems and identities (clean identity without fallback)
    local_icons = []
    for filename, processed_path in processed_images.items():
        stem = Path(filename).stem
        stem_lower = stem.lower().strip()
        clean_identity = ""
        if stem_lower in FILENAME_TO_ICON_IDENTITY:
            clean_identity = FILENAME_TO_ICON_IDENTITY[stem_lower]
        else:
            for key, val in FILENAME_TO_ICON_IDENTITY.items():
                if key in stem_lower or stem_lower in key:
                    clean_identity = val
                    break
        local_icons.append({
            "filename": filename,
            "processed_path": processed_path,
            "stem": stem,
            "identity": clean_identity,
            "color": extract_dominant_color(processed_path)
        })

    # 3. Launch browser
    try:
        import re
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        with VendorPortalAutomation(email, password, headless=False) as automation:
            if not automation.login():
                logger.error("✗ Login failed.")
                return "login_failed"  # special sentinel so caller knows it was a login issue

            time.sleep(2)

            # Navigate to Dashboard Icons using the proper card click flow
            logger.info("Navigating to dashboard icons section...")
            if not automation.navigate_to_dashboard_icons():
                logger.error("✗ Navigation failed.")
                return False

            # Wait for table to load
            try:
                table = WebDriverWait(automation.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
            except Exception:
                logger.error("✗ Table not found on dashboard icons page.")
                return False

            # Retrieve all rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            logger.info(f"Total rows found: {len(rows)}")

            update_tasks = []
            current_user_type = "All"
            
            for idx, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) == 1:
                    hdr_text = cells[0].text.strip()
                    match = re.search(r'^([a-zA-Z\s]+?)\s+\d+', hdr_text)
                    if match:
                        current_user_type = match.group(1).strip().title()
                    else:
                        current_user_type = hdr_text.title()
                    continue

                if len(cells) >= 6:
                    cell_1_text = cells[1].text.strip().replace("\n", " ")
                    color_match = re.search(r'(#[A-Fa-f0-9]{6})', cell_1_text)
                    id_match = re.search(r'ID:\s*([a-zA-Z0-9_\-]+)', cell_1_text)

                    icon_id = id_match.group(1) if id_match else ""
                    title = cell_1_text
                    if color_match:
                        title = title.split(color_match.group(1))[0].strip()
                    elif "ID:" in title:
                        title = title.split("ID:")[0].strip()
                    title = title.replace("", "").strip(" •-")
                    logger.info(f"Parsed Row {idx}: UserType='{current_user_type}', Title='{title}', ID='{icon_id}'")

                    # Apply specific update filters if specified
                    if target_user_type and current_user_type.lower().strip() != target_user_type.lower().strip():
                        continue
                    if target_icon_id and icon_id.lower().strip() != target_icon_id.lower().strip():
                        continue

                    # Match with local icon
                    matched_local = None
                    
                    # Priority 1: Stem exact match
                    for loc in local_icons:
                        if loc["stem"].lower().strip() == title.lower().strip():
                            matched_local = loc
                            break
                    
                    # Priority 2: Stem fuzzy match
                    if not matched_local:
                        for loc in local_icons:
                            stem_norm = loc["stem"].lower().replace("and", "&").replace("  ", " ").strip()
                            title_norm = title.lower().replace("and", "&").replace("  ", " ").strip()
                            if stem_norm == title_norm or stem_norm in title_norm or title_norm in stem_norm:
                                matched_local = loc
                                break

                    # Priority 3: Identity matches icon_id
                    if not matched_local and icon_id:
                        for loc in local_icons:
                            if loc["identity"].lower().strip() == icon_id.lower().strip():
                                matched_local = loc
                                break

                    if matched_local:
                        update_tasks.append({
                            "user_type": current_user_type,
                            "display_title": title,
                            "icon_id": icon_id,
                            "row_index": idx,
                            "local_icon": matched_local
                        })
                    else:
                        logger.info(f"No matching local icon for row {idx}: Title='{title}', ID='{icon_id}'")

            logger.info(f"Found {len(update_tasks)} icons to update.")

            # Perform the updates
            successful = 0
            failed = 0

            # Re-locate function to find the row dynamically to prevent staleness and shifting
            def find_target_row(driver, user_type, title, icon_id):
                try:
                    table = driver.find_element(By.TAG_NAME, "table")
                    current_rows = table.find_elements(By.TAG_NAME, "tr")
                    current_ut = "All"
                    for r_idx, r in enumerate(current_rows):
                        cells = r.find_elements(By.TAG_NAME, "td")
                        if len(cells) == 1:
                            hdr_text = cells[0].text.strip()
                            match = re.search(r'^([a-zA-Z\s]+?)\s+\d+', hdr_text)
                            if match:
                                current_ut = match.group(1).strip().title()
                            else:
                                current_ut = hdr_text.title()
                            continue
                        if len(cells) >= 6 and current_ut.lower() == user_type.lower():
                            cell_text = cells[1].text.strip().replace("\n", " ")
                            if f"ID: {icon_id}" in cell_text or f"ID:{icon_id}" in cell_text or title.lower() in cell_text.lower():
                                return r, r_idx
                except Exception:
                    pass
                return None, -1

            for idx_task, task in enumerate(update_tasks, 1):
                user_type = task["user_type"]
                title = task["display_title"]
                icon_id = task["icon_id"]
                loc = task["local_icon"]

                logger.info(f"\n[{idx_task}/{len(update_tasks)}] Updating: [{user_type}] '{title}' (ID: '{icon_id}') with '{loc['stem']}'")

                try:
                    # Dynamically re-locate the target row on every step to prevent stale/shifted elements
                    target_row, current_row_idx = find_target_row(automation.driver, user_type, title, icon_id)
                    if not target_row:
                        logger.error(f"  ✗ Could not find row for [{user_type}] '{title}' (ID: '{icon_id}') on page.")
                        failed += 1
                        continue

                    cells = target_row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 6:
                        logger.error(f"  ✗ Target row is invalid.")
                        failed += 1
                        continue

                    # Click action button in the last cell of this row
                    last_cell = cells[-1]
                    action_btn = last_cell.find_element(By.XPATH, ".//button[contains(., 'Actions')]")
                    automation.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", action_btn)
                    time.sleep(0.5)
                    automation.driver.execute_script("arguments[0].click();", action_btn)

                    # Wait for Edit Config button and click it
                    edit_btn = WebDriverWait(automation.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[text()='Edit Config']/ancestor::button"))
                    )
                    automation.driver.execute_script("arguments[0].click();", edit_btn)

                    # Wait for Modal and name input field
                    name_input = WebDriverWait(automation.driver, 10).until(
                        EC.element_to_be_clickable((By.NAME, "Name"))
                    )
                    # Clear value using javascript to be extremely robust
                    automation.driver.execute_script("arguments[0].value = '';", name_input)
                    name_input.send_keys(loc["stem"])
                    logger.info(f"  → Set display title to: {loc['stem']}")

                    # Enter Icon Color if present
                    hex_color = loc.get("color")
                    if hex_color:
                        try:
                            # Sync color picker visually
                            color_inputs = automation.driver.find_elements(By.NAME, "IconColor")
                            color_picker = None
                            color_text = None
                            for ci in color_inputs:
                                if ci.get_attribute("type") == "color":
                                    color_picker = ci
                                elif ci.get_attribute("type") == "text":
                                    color_text = ci
                            
                            if color_picker:
                                automation.driver.execute_script(
                                    """
                                    var setter = Object.getOwnPropertyDescriptor(
                                        window.HTMLInputElement.prototype, 'value').set;
                                    setter.call(arguments[0], arguments[1]);
                                    arguments[0].dispatchEvent(new Event('input',  {bubbles:true}));
                                    arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
                                    """,
                                    color_picker,
                                    hex_color,
                                )
                            
                            if color_text:
                                from selenium.webdriver.common.keys import Keys
                                color_text.click()
                                time.sleep(0.1)
                                color_text.send_keys(Keys.CONTROL + "a")
                                color_text.send_keys(Keys.DELETE)
                                color_text.send_keys(hex_color)
                                time.sleep(0.1)
                                automation.driver.execute_script("arguments[0].blur()", color_text)
                            logger.info(f"  → Set icon color to: {hex_color}")
                        except Exception as ce:
                            logger.warning(f"  ⚠ Could not set icon color: {ce}")

                    # Upload processed image
                    img_path = str(Path(loc["processed_path"]).absolute())
                    file_input = WebDriverWait(automation.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
                    )
                    file_input.send_keys(img_path)
                    logger.info(f"  → Uploaded image: {loc['filename']}")
                    time.sleep(2) # Let preview load

                    # Click submit button
                    submit_btn = WebDriverWait(automation.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'p-5')]//button[contains(@class,'bg-indigo-600')]"))
                    )
                    automation.driver.execute_script("arguments[0].click();", submit_btn)
                    logger.info("  → Edit form submitted.")

                    # Wait for modal to close (submit button becomes invisible)
                    WebDriverWait(automation.driver, 15).until(
                        EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class,'p-5')]//button[contains(@class,'bg-indigo-600')]"))
                    )
                    automation._wait_toast_gone()
                    time.sleep(1)
                    logger.info(f"  ✓ Successfully updated: {title} -> {loc['stem']}")
                    successful += 1

                except Exception as ex:
                    logger.error(f"  ✗ Failed to update row ({title}): {ex}")
                    try:
                        discard = automation.driver.find_element(By.XPATH, "//button[contains(text(),'Cancel') or contains(text(),'Discard')]")
                        automation.driver.execute_script("arguments[0].click();", discard)
                        time.sleep(1)
                    except Exception:
                        pass
                    failed += 1

            logger.info("=" * 60)
            logger.info(f"UPDATE ACCOUNT SUMMARY: {email}")
            logger.info(f"✓ Succeeded: {successful}")
            logger.info(f"✗ Failed: {failed}")
            logger.info("=" * 60)
            return failed == 0

    except Exception as e:
        logger.error(f"Error updating icons for {email}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_dashboard_icons_sheet_update(target_user_type=None, target_icon_id=None) -> bool:
    """Download credentials from sheet and run updates for each."""
    credentials = download_sheet_credentials()
    if not credentials:
        print("  ❌ No credentials found or downloaded from sheet.")
        return False
        
    print(f"\n  Found {len(credentials)} companies in Google Sheet.")
    for idx, cred in enumerate(credentials, 1):
        print(f"  {idx}. {cred['company']} ({cred['email']})")
    
    confirm = input("\n  Do you want to proceed with all these accounts? (y/n): ").strip().lower()
    if confirm != 'y':
        print("  Cancelled.")
        return False

    overall_success = True
    failed_logins = []    # accounts that could not log in at all
    failed_updates = []   # accounts that logged in but had update errors

    for idx, cred in enumerate(credentials, 1):
        logger.info(f"\n>>> Starting update [{idx}/{len(credentials)}] for {cred['company']}...")
        try:
            res = run_single_update(
                cred['email'],
                cred['password'],
                target_user_type=target_user_type,
                target_icon_id=target_icon_id
            )
        except Exception as exc:
            logger.error(f"  ✗ Unexpected error for {cred['company']} ({cred['email']}): {exc}")
            res = False

        if res == "login_failed":
            overall_success = False
            failed_logins.append({
                "company": cred["company"],
                "email":   cred["email"]
            })
            logger.warning(
                f"  ⚠ LOGIN FAILED for {cred['company']} ({cred['email']}) — skipping to next account"
            )
        elif not res:
            overall_success = False
            failed_updates.append({
                "company": cred["company"],
                "email":   cred["email"]
            })
            logger.error(f"  ✗ Update errors for {cred['company']} ({cred['email']})")
        else:
            logger.info(f"  ✓ Completed update for {cred['company']}")

    # ── Final Summary ────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("BATCH UPDATE — FINAL SUMMARY")
    logger.info("=" * 60)
    total = len(credentials)
    ok = total - len(failed_logins) - len(failed_updates)
    logger.info(f"  Total accounts  : {total}")
    logger.info(f"  ✓ Succeeded     : {ok}")
    logger.info(f"  ✗ Login failed  : {len(failed_logins)}")
    logger.info(f"  ✗ Update errors : {len(failed_updates)}")

    if failed_logins:
        logger.warning("\n  ─── ACCOUNTS THAT COULD NOT LOG IN ───")
        print()
        print("  ┌─────────────────────────────────────────────────────────┐")
        print("  │         FAILED LOGINS (credentials incorrect?)          │")
        print("  ├─────────────────────────────────────────────────────────┤")
        for fl in failed_logins:
            line = f"  {fl['company']} ({fl['email']})"
            print(f"  │  ✗ {line:<55}│")
            logger.warning(f"    ✗ {line}")
        print("  └─────────────────────────────────────────────────────────┘")

    if failed_updates:
        logger.warning("\n  ─── ACCOUNTS WITH UPDATE ERRORS ───")
        print()
        print("  ┌─────────────────────────────────────────────────────────┐")
        print("  │         FAILED UPDATES (logged in, but errors)          │")
        print("  ├─────────────────────────────────────────────────────────┤")
        for fu in failed_updates:
            line = f"  {fu['company']} ({fu['email']})"
            print(f"  │  ✗ {line:<55}│")
            logger.warning(f"    ✗ {line}")
        print("  └─────────────────────────────────────────────────────────┘")

    if not failed_logins and not failed_updates:
        print()
        print("  ✅ All accounts updated successfully!")

    logger.info("=" * 60)
    return overall_success


def run_dashboard_icons_special_five_update(email, password, target_user_type=None) -> bool:
    """
    Specifically update/add the following 5 icons for the specified user types:
    1. Wallet (ID: wallet) -> My Wallet.png
    2. Code Details (ID: codedetails) -> Scan Activity.png
    3. Scan History (ID: history) -> Scan History.png
    4. Contact Us (ID: contactus) -> Support.png
    5. About Us (ID: aboutus) -> aboutus.png
    """
    logger.info("=" * 60)
    logger.info(f"UPDATING/ADDING 5 SPECIFIC ICONS FOR: {email}")
    if target_user_type:
        logger.info(f"Filter -> User Type: {target_user_type}")
    logger.info("=" * 60)

    # 1. Process local images first
    input_dir = str(Path(__file__).resolve().parent.parent / "dashboardicons")
    output_dir = "automation/processed_images"

    logger.info("Processing images from dashboardicons/...")
    processor = ImageProcessor(input_dir, output_dir)
    processed_images = processor.process_all_images()

    if not processed_images:
        logger.error("No images processed. Aborting update.")
        return False

    logger.info(f"✓ {len(processed_images)} images processed.")

    # Define the 5 target icons config
    targets_def = [
        {
            "identity": "wallet",
            "stem": "My Wallet",
            "display_title": "My Wallet",
            "filename": "My Wallet.png",
            "toggle_option": "both",
            "match_ids": ["wallet"],
            "match_titles": ["my wallet", "wallet"]
        },
        {
            "identity": "codedetails",
            "stem": "Scan Activity",
            "display_title": "Scan Activity",
            "filename": "Scan Activity.png",
            "toggle_option": "dashboard only",
            "match_ids": ["codedetails"],
            "match_titles": ["scan activity", "code details"]
        },
        {
            "identity": "history",
            "stem": "Scan History",
            "display_title": "Scan History",
            "filename": "Scan History.png",
            "toggle_option": "dashboard only",
            "match_ids": ["history"],
            "match_titles": ["scan history", "history"]
        },
        {
            "identity": "contactus",
            "stem": "Support",
            "display_title": "Contact Us",
            "filename": "Support.png",
            "toggle_option": "dashboard only",
            "match_ids": ["contactus", "help"],
            "match_titles": ["support", "help", "contact us", "contactus"]
        },
        {
            "identity": "aboutus",
            "stem": "aboutus",
            "display_title": "About Us",
            "filename": "aboutus.png",
            "toggle_option": "side menu",
            "match_ids": ["aboutus"],
            "match_titles": ["about us", "aboutus"]
        }
    ]

    # Resolve processed paths and colors
    targets = []
    for t in targets_def:
        # Find matched processed image
        matched_filename, processed_path = find_matching_processed_image(t["stem"], processed_images)
        if not processed_path:
            # Try matching by filename
            matched_filename, processed_path = find_matching_processed_image(t["filename"], processed_images)
        
        if not processed_path:
            logger.error(f"Could not find processed image for '{t['stem']}' (filename: {t['filename']}). Aborting.")
            return False
            
        targets.append({
            "identity": t["identity"],
            "display_title": t["display_title"],
            "processed_path": processed_path,
            "filename": matched_filename,
            "toggle_option": t["toggle_option"],
            "color": extract_dominant_color(processed_path),
            "match_ids": t["match_ids"],
            "match_titles": t["match_titles"]
        })

    # 3. Launch browser
    try:
        import re
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        with VendorPortalAutomation(email, password, headless=False) as automation:
            if not automation.login():
                logger.error("✗ Login failed.")
                return "login_failed"

            time.sleep(2)

            # Navigate to Dashboard Icons
            logger.info("Navigating to dashboard icons section...")
            if not automation.navigate_to_dashboard_icons():
                logger.error("✗ Navigation failed.")
                return False

            # Get all available user types in dropdown to ensure we can check and add if missing
            logger.info("Reading all available user types from dropdown...")
            available_user_types = automation.get_available_user_types()
            if not available_user_types:
                logger.warning("No user types retrieved from dropdown.")
            
            # Map available user types
            utypes_to_process = []
            for val, text in available_user_types:
                text_clean = text.strip()
                if target_user_type and text_clean.lower() != target_user_type.lower():
                    continue
                utypes_to_process.append((val, text_clean))

            if not utypes_to_process:
                logger.error(f"No user types matched filter: '{target_user_type}'")
                return False

            logger.info(f"User types to process: {[t[1] for t in utypes_to_process]}")

            # Retrieve configured icons table to find existing ones
            try:
                table = WebDriverWait(automation.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                rows = table.find_elements(By.TAG_NAME, "tr")
            except Exception:
                logger.warning("Table not found on page. Assuming no configured icons exist yet.")
                rows = []

            # Parse configured rows
            # We group them by user type
            # key: user type name (lower), value: list of row dicts
            existing_by_user_type = {}
            current_user_type = "All"
            
            for idx, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) == 1:
                    hdr_text = cells[0].text.strip()
                    match = re.search(r'^([a-zA-Z\s]+?)\s+\d+', hdr_text)
                    if match:
                        current_user_type = match.group(1).strip().title()
                    else:
                        current_user_type = hdr_text.title()
                    continue

                if len(cells) >= 6:
                    cell_1_text = cells[1].text.strip().replace("\n", " ")
                    color_match = re.search(r'(#[A-Fa-f0-9]{6})', cell_1_text)
                    id_match = re.search(r'ID:\s*([a-zA-Z0-9_\-]+)', cell_1_text)

                    icon_id = id_match.group(1) if id_match else ""
                    title = cell_1_text
                    if color_match:
                        title = title.split(color_match.group(1))[0].strip()
                    elif "ID:" in title:
                        title = title.split("ID:")[0].strip()
                    title = title.replace("", "").strip(" •-")

                    existing_by_user_type.setdefault(current_user_type.lower().strip(), []).append({
                        "title": title,
                        "icon_id": icon_id,
                        "row_index": idx
                    })

            # For each user type, determine update tasks (edit row) and add tasks (create new)
            tasks_to_run = []
            
            for utype_val, utype_text in utypes_to_process:
                ut_key = utype_text.lower().strip()
                existing_list = existing_by_user_type.get(ut_key, [])
                
                # We need to map each of our 4 targets to either an edit task or an add task
                for target in targets:
                    matched_row = None
                    
                    # 1. Match by ID
                    for row_data in existing_list:
                        if row_data["icon_id"].lower().strip() in target["match_ids"]:
                            matched_row = row_data
                            break
                            
                    # 2. Match by Title (if not matched by ID)
                    if not matched_row:
                        for row_data in existing_list:
                            if row_data["title"].lower().strip() in target["match_titles"]:
                                matched_row = row_data
                                break
                                
                    if matched_row:
                        tasks_to_run.append({
                            "action": "edit",
                            "user_type_val": utype_val,
                            "user_type_text": utype_text,
                            "title_on_page": matched_row["title"],
                            "icon_id_on_page": matched_row["icon_id"],
                            "target": target
                        })
                    else:
                        tasks_to_run.append({
                            "action": "add",
                            "user_type_val": utype_val,
                            "user_type_text": utype_text,
                            "target": target
                        })

            logger.info(f"Planned tasks: {len(tasks_to_run)}")
            for t in tasks_to_run:
                logger.info(f"  - [{t['user_type_text']}] {t['action'].upper()} -> {t['target']['display_title']} (ID: {t['target']['identity']})")

            # Re-locate function to find the row dynamically to prevent staleness and shifting during Edits
            def find_target_row(driver, user_type, title, icon_id):
                try:
                    table = driver.find_element(By.TAG_NAME, "table")
                    current_rows = table.find_elements(By.TAG_NAME, "tr")
                    current_ut = "All"
                    for r_idx, r in enumerate(current_rows):
                        cells = r.find_elements(By.TAG_NAME, "td")
                        if len(cells) == 1:
                            hdr_text = cells[0].text.strip()
                            match = re.search(r'^([a-zA-Z\s]+?)\s+\d+', hdr_text)
                            if match:
                                current_ut = match.group(1).strip().title()
                            else:
                                current_ut = hdr_text.title()
                            continue
                        if len(cells) >= 6 and current_ut.lower() == user_type.lower():
                            cell_text = cells[1].text.strip().replace("\n", " ")
                            if f"ID: {icon_id}" in cell_text or f"ID:{icon_id}" in cell_text or title.lower() in cell_text.lower():
                                return r, r_idx
                except Exception:
                    pass
                return None, -1

            successful = 0
            failed = 0

            for idx_task, task in enumerate(tasks_to_run, 1):
                action = task["action"]
                ut_text = task["user_type_text"]
                ut_val = task["user_type_val"]
                target = task["target"]
                
                logger.info(f"\n[{idx_task}/{len(tasks_to_run)}] {action.upper()}: [{ut_text}] {target['display_title']} (ID: {target['identity']})")
                
                if action == "edit":
                    # Edit existing row
                    title_on_page = task["title_on_page"]
                    icon_id_on_page = task["icon_id_on_page"]
                    try:
                        # Re-locate row
                        target_row, current_row_idx = find_target_row(automation.driver, ut_text, title_on_page, icon_id_on_page)
                        if not target_row:
                            logger.error(f"  ✗ Could not find row on page.")
                            failed += 1
                            continue
                            
                        cells = target_row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 6:
                            logger.error(f"  ✗ Target row is invalid.")
                            failed += 1
                            continue

                        # Click action button in the last cell of this row
                        last_cell = cells[-1]
                        action_btn = last_cell.find_element(By.XPATH, ".//button[contains(., 'Actions')]")
                        automation.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", action_btn)
                        time.sleep(0.5)
                        automation.driver.execute_script("arguments[0].click();", action_btn)

                        # Wait for Edit Config button and click it
                        edit_btn = WebDriverWait(automation.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//span[text()='Edit Config']/ancestor::button"))
                        )
                        automation.driver.execute_script("arguments[0].click();", edit_btn)

                        # Wait for Modal and name input field
                        name_input = WebDriverWait(automation.driver, 10).until(
                            EC.element_to_be_clickable((By.NAME, "Name"))
                        )
                        # Clear value using javascript to be extremely robust
                        automation.driver.execute_script("arguments[0].value = '';", name_input)
                        name_input.send_keys(target["display_title"])
                        logger.info(f"  → Set display title to: {target['display_title']}")

                        # Enter Icon Color if present
                        hex_color = target.get("color")
                        if hex_color:
                            try:
                                color_inputs = automation.driver.find_elements(By.NAME, "IconColor")
                                color_picker = None
                                color_text = None
                                for ci in color_inputs:
                                    if ci.get_attribute("type") == "color":
                                        color_picker = ci
                                    elif ci.get_attribute("type") == "text":
                                        color_text = ci
                                
                                if color_picker:
                                    automation.driver.execute_script(
                                        """
                                        var setter = Object.getOwnPropertyDescriptor(
                                            window.HTMLInputElement.prototype, 'value').set;
                                        setter.call(arguments[0], arguments[1]);
                                        arguments[0].dispatchEvent(new Event('input',  {bubbles:true}));
                                        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
                                        """,
                                        color_picker,
                                        hex_color,
                                    )
                                
                                if color_text:
                                    from selenium.webdriver.common.keys import Keys
                                    color_text.click()
                                    time.sleep(0.1)
                                    color_text.send_keys(Keys.CONTROL + "a")
                                    color_text.send_keys(Keys.DELETE)
                                    color_text.send_keys(hex_color)
                                    time.sleep(0.1)
                                    automation.driver.execute_script("arguments[0].blur()", color_text)
                                logger.info(f"  → Set icon color to: {hex_color}")
                            except Exception as ce:
                                logger.warning(f"  ⚠ Could not set icon color: {ce}")

                        # Upload processed image
                        img_path = str(Path(target["processed_path"]).absolute())
                        file_input = WebDriverWait(automation.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
                        )
                        file_input.send_keys(img_path)
                        logger.info(f"  → Uploaded image: {target['filename']}")
                        time.sleep(2) # Let preview load

                        # Click submit button
                        submit_btn = WebDriverWait(automation.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'p-5')]//button[contains(@class,'bg-indigo-600')]"))
                        )
                        automation.driver.execute_script("arguments[0].click();", submit_btn)
                        logger.info("  → Edit form submitted.")

                        # Wait for modal to close
                        WebDriverWait(automation.driver, 15).until(
                            EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class,'p-5')]//button[contains(@class,'bg-indigo-600')]"))
                        )
                        automation._wait_toast_gone()
                        time.sleep(1)
                        logger.info(f"  ✓ Successfully updated: {title_on_page} -> {target['display_title']}")
                        successful += 1

                    except Exception as ex:
                        logger.error(f"  ✗ Failed to update row: {ex}")
                        try:
                            discard = automation.driver.find_element(By.XPATH, "//button[contains(text(),'Cancel') or contains(text(),'Discard')]")
                            automation.driver.execute_script("arguments[0].click();", discard)
                            time.sleep(1)
                        except Exception:
                            pass
                        failed += 1
                        
                elif action == "add":
                    # Add as new icon
                    add_data = {
                        "user_type": ut_val,
                        "icon_identity": target["identity"],
                        "display_title": target["display_title"],
                        "image_path": target["processed_path"],
                        "toggle_option": target["toggle_option"],
                        "icon_color": target["color"]
                    }
                    if automation.add_icon(add_data):
                        successful += 1
                    else:
                        failed += 1
                        
                time.sleep(1)

            logger.info("=" * 60)
            logger.info(f"UPDATE ACCOUNT SUMMARY: {email}")
            logger.info(f"✓ Succeeded: {successful}")
            logger.info(f"✗ Failed: {failed}")
            logger.info("=" * 60)
            return failed == 0

    except Exception as e:
        logger.error(f"Error updating specific icons for {email}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_dashboard_icons_special_five_sheet_update(target_user_type=None) -> bool:
    """Download credentials from sheet and run specific updates for each."""
    credentials = download_sheet_credentials()
    if not credentials:
        print("  ❌ No credentials found or downloaded from sheet.")
        return False
        
    print(f"\n  Found {len(credentials)} companies in Google Sheet.")
    for idx, cred in enumerate(credentials, 1):
        print(f"  {idx}. {cred['company']} ({cred['email']})")
    
    confirm = input("\n  Do you want to proceed with all these accounts? (y/n): ").strip().lower()
    if confirm != 'y':
        print("  Cancelled.")
        return False

    overall_success = True
    failed_logins = []
    failed_updates = []

    for idx, cred in enumerate(credentials, 1):
        logger.info(f"\n>>> Starting specific 5 icons update [{idx}/{len(credentials)}] for {cred['company']}...")
        try:
            res = run_dashboard_icons_special_five_update(
                cred['email'],
                cred['password'],
                target_user_type=target_user_type
            )
        except Exception as exc:
            logger.error(f"  ✗ Unexpected error for {cred['company']} ({cred['email']}): {exc}")
            res = False

        if res == "login_failed":
            overall_success = False
            failed_logins.append({
                "company": cred["company"],
                "email":   cred["email"]
            })
            logger.warning(
                f"  ⚠ LOGIN FAILED for {cred['company']} ({cred['email']}) — skipping to next account"
            )
        elif not res:
            overall_success = False
            failed_updates.append({
                "company": cred["company"],
                "email":   cred["email"]
            })
            logger.error(f"  ✗ Update errors for {cred['company']} ({cred['email']})")
        else:
            logger.info(f"  ✓ Completed update for {cred['company']}")

    # ── Final Summary ────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("BATCH UPDATE — FINAL SUMMARY (SPECIAL 5 ICONS)")
    logger.info("=" * 60)
    total = len(credentials)
    ok = total - len(failed_logins) - len(failed_updates)
    logger.info(f"  Total accounts  : {total}")
    logger.info(f"  ✓ Succeeded     : {ok}")
    logger.info(f"  ✗ Login failed  : {len(failed_logins)}")
    logger.info(f"  ✗ Update errors : {len(failed_updates)}")

    if failed_logins:
        logger.warning("\n  ─── ACCOUNTS THAT COULD NOT LOG IN ───")
        print()
        print("  ┌─────────────────────────────────────────────────────────┐")
        print("  │         FAILED LOGINS (credentials incorrect?)          │")
        print("  ├─────────────────────────────────────────────────────────┤")
        for fl in failed_logins:
            line = f"  {fl['company']} ({fl['email']})"
            print(f"  │  ✗ {line:<55}│")
            logger.warning(f"    ✗ {line}")
        print("  └─────────────────────────────────────────────────────────┘")

    if failed_updates:
        logger.warning("\n  ─── ACCOUNTS WITH UPDATE ERRORS ───")
        print()
        print("  ┌─────────────────────────────────────────────────────────┐")
        print("  │         FAILED UPDATES (logged in, but errors)          │")
        print("  ├─────────────────────────────────────────────────────────┤")
        for fu in failed_updates:
            line = f"  {fu['company']} ({fu['email']})"
            print(f"  │  ✗ {line:<55}│")
            logger.warning(f"    ✗ {line}")
        print("  └─────────────────────────────────────────────────────────┘")

    if not failed_logins and not failed_updates:
        print()
        print("  ✅ All accounts updated successfully!")

    logger.info("=" * 60)
    return overall_success


def run_missing_icons_upload(email, password) -> bool:
    """
    Check all user types' dashboard icons.
    For any icon present in local dashboardicons/ folder, if it is missing
    on the website for a user type, upload it.
    """
    logger.info("=" * 60)
    logger.info("UPLOAD MISSING DASHBOARD ICONS FOR ALL USER TYPES (Option 20)")
    logger.info("=" * 60)

    # 1. Process local images first
    input_dir = str(Path(__file__).resolve().parent.parent / "dashboardicons")
    output_dir = "automation/processed_images"

    logger.info("Processing images from dashboardicons/...")
    processor = ImageProcessor(input_dir, output_dir)
    processed_images = processor.process_all_images()

    if not processed_images:
        logger.error("No images processed from 'dashboardicons/'. Aborting.")
        return False

    logger.info(f"v {len(processed_images)} images processed.")

    # 2. Build local files list with stems and identities
    local_icons = []
    for filename, processed_path in processed_images.items():
        stem = Path(filename).stem
        display_title = stem
        icon_identity = get_icon_identity(stem)
        icon_color = extract_dominant_color(processed_path)
        toggle_option = get_toggle_option(stem)
        
        local_icons.append({
            "filename": filename,
            "processed_path": processed_path,
            "stem": stem,
            "display_title": display_title,
            "icon_identity": icon_identity,
            "icon_color": icon_color,
            "toggle_option": toggle_option
        })

    # 3. Launch browser
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import re

        with VendorPortalAutomation(email, password, headless=False) as automation:
            if not automation.login():
                logger.error("x Login failed.")
                return False

            time.sleep(2)

            # Navigate to Dashboard Icons
            logger.info("Navigating to dashboard icons section...")
            if not automation.navigate_to_dashboard_icons():
                logger.error("x Navigation failed.")
                return False

            # Get all available user types in dropdown to ensure we cover all of them
            # even if they are not in the table.
            logger.info("Reading all available user types from dropdown...")
            available_user_types = automation.get_available_user_types()
            if not available_user_types:
                logger.warning("No user types retrieved from dropdown.")
            
            # Map clean lowercased dropdown names to original dropdown name/value
            utype_dropdown_map = {}
            for val, text in available_user_types:
                utype_dropdown_map[text.lower().strip()] = {
                    "value": val,
                    "text": text
                }

            # Wait for table to load
            try:
                table = WebDriverWait(automation.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                rows = table.find_elements(By.TAG_NAME, "tr")
                logger.info(f"Total rows found in configured icons table: {len(rows)}")
            except Exception:
                logger.warning("x Table not found on dashboard icons page. It might be empty.")
                rows = []

            # Group configured icons by user type
            # key: cleaned user type name (lower, strip), value: set of icon_identities
            configured_by_user_type = {}
            
            # Initialize configured sets for all user types from dropdown
            for text_lower in utype_dropdown_map:
                configured_by_user_type[text_lower] = set()

            current_user_type = "all"
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) == 1:
                    hdr_text = cells[0].text.strip()
                    # Example: "Dealer 13 Icons Configured"
                    match = re.search(r'^([a-zA-Z\s\-\_]+?)\s+\d+', hdr_text)
                    if match:
                        current_user_type = match.group(1).strip().lower()
                    else:
                        current_user_type = hdr_text.strip().lower()
                    
                    if current_user_type not in configured_by_user_type:
                        configured_by_user_type[current_user_type] = set()
                    continue

                if len(cells) >= 6:
                    cell_1_text = cells[1].text.strip().replace("\n", " ")
                    id_match = re.search(r'ID:\s*([a-zA-Z0-9_\-]+)', cell_1_text)
                    if id_match:
                        icon_id = id_match.group(1).strip()
                        configured_by_user_type[current_user_type.strip()].add(icon_id)

            # Let's log what we found
            logger.info("Currently configured icons per user type:")
            for ut, icons in configured_by_user_type.items():
                logger.info(f"  {ut}: {list(icons)}")

            # Calculate missing icons for each user type
            missing_tasks = []
            for ut_clean, configured_set in configured_by_user_type.items():
                if ut_clean in utype_dropdown_map:
                    target_ut_name = utype_dropdown_map[ut_clean]["text"]
                else:
                    target_ut_name = ut_clean.title()
                
                # Keep track of identities we've already planned to upload for this user type in this run,
                # to avoid duplicate uploads if there are multiple local files mapping to the same identity
                planned_identities = set()

                for loc in local_icons:
                    identity = loc["icon_identity"]
                    if identity not in configured_set and identity not in planned_identities:
                        missing_tasks.append({
                            "user_type": target_ut_name,
                            "icon_identity": identity,
                            "display_title": loc["display_title"],
                            "image_path": loc["processed_path"],
                            "toggle_option": loc["toggle_option"],
                            "icon_color": loc["icon_color"],
                            "filename": loc["filename"]
                        })
                        planned_identities.add(identity)

            if not missing_tasks:
                logger.info("No missing icons found! All local icons are already configured for all user types.")
                print("\n  No missing icons found! All local icons are already configured for all user types.\n")
                return True

            logger.info(f"Found {len(missing_tasks)} missing icon uploads:")
            for task in missing_tasks:
                logger.info(f"  - [{task['user_type']}] {task['display_title']} (ID: {task['icon_identity']}) from {task['filename']}")

            print(f"\n  Found {len(missing_tasks)} missing icons to upload.")
            confirm = input("  Do you want to proceed with uploading these missing icons? (y/n): ").strip().lower()
            if confirm != 'y':
                print("  Cancelled.")
                return False

            # Upload missing icons
            successful = 0
            failed = 0
            for idx_task, task in enumerate(missing_tasks, 1):
                logger.info(f"\n[{idx_task}/{len(missing_tasks)}] Uploading missing icon for {task['user_type']}: {task['display_title']}")
                if automation.add_icon(task):
                    successful += 1
                else:
                    failed += 1
                time.sleep(1)

            # Final summary
            logger.info("\n" + "=" * 60)
            logger.info("MISSING ICONS UPLOAD SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Successful uploads: {successful}")
            logger.info(f"Failed uploads: {failed}")
            logger.info(f"Total processed: {len(missing_tasks)}")
            logger.info("=" * 60)

            return failed == 0

    except Exception as e:
        logger.error(f"Unexpected error during missing icons upload: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def parse_sequence_string(seq_str: str):
    """
    Parse a sequence string like '4.6' or '6' into (prefix, relative_order).
    '4.6' -> ('4', '6')
    '6'   -> (None, '6')
    """
    seq_str = seq_str.strip()
    if '.' in seq_str:
        parts = seq_str.split('.')
        if len(parts) >= 2:
            return parts[0], '.'.join(parts[1:])
    return None, seq_str


def run_copy_dashboard_sequence(email, password) -> bool:
    """
    Copy sequence of dashboard icons from a user-specified Source User Type
    and apply that sequence to all other User Types in the vendor portal.
    """
    logger.info("=" * 60)
    logger.info("COPY DASHBOARD ICONS SEQUENCE (Option 23)")
    logger.info("=" * 60)

    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import re

        with VendorPortalAutomation(email, password, headless=False) as automation:
            if not automation.login():
                logger.error("✗ Login failed.")
                return False

            time.sleep(2)

            # Navigate to Dashboard Icons
            logger.info("Navigating to dashboard icons section...")
            if not automation.navigate_to_dashboard_icons():
                logger.error("✗ Navigation failed.")
                return False

            # Wait for table to load
            try:
                table = WebDriverWait(automation.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                rows = table.find_elements(By.TAG_NAME, "tr")
                logger.info(f"Total rows found in configured icons table: {len(rows)}")
            except Exception:
                logger.error("✗ Table not found on dashboard icons page.")
                print("\n  ❌ Table not found on dashboard icons page.\n")
                return False

            # Scan the table to find available user types and their prefixes
            user_types_on_page = []
            user_type_prefixes = {}
            current_ut = "All"
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) == 1:
                    hdr_text = cells[0].text.strip()
                    # Match pattern: e.g. "Customer 12" -> "Customer"
                    match = re.search(r'^([a-zA-Z\s\-\_]+?)\s+\d+', hdr_text)
                    ut_name = match.group(1).strip() if match else hdr_text.strip()
                    ut_name_tidy = ut_name.title()
                    if ut_name_tidy not in user_types_on_page:
                        user_types_on_page.append(ut_name_tidy)
                    current_ut = ut_name_tidy
                    continue

                if len(cells) >= 6:
                    seq_val = cells[0].text.strip()
                    prefix, _ = parse_sequence_string(seq_val)
                    if prefix and current_ut not in user_type_prefixes:
                        user_type_prefixes[current_ut] = prefix
                        logger.info(f"Detected sequence prefix for '{current_ut}': '{prefix}'")

            if not user_types_on_page:
                logger.error("No user types with configured dashboard icons found on page.")
                print("\n  ❌ No user types with configured dashboard icons found on page.\n")
                return False

            print("\n  Available User Types with configured icons on the page:")
            for idx, ut in enumerate(user_types_on_page, 1):
                pref_suffix = f" (Prefix: {user_type_prefixes.get(ut)})" if user_type_prefixes.get(ut) else ""
                print(f"    {idx}. {ut}{pref_suffix}")
            print()

            # Prompt the user to select the source user type
            source_user_type = ""
            while True:
                src_input = input("  Enter the index or name of the Source User Type (to copy sequence from): ").strip()
                if not src_input:
                    continue
                # Check if index is entered
                if src_input.isdigit():
                    idx_val = int(src_input) - 1
                    if 0 <= idx_val < len(user_types_on_page):
                        source_user_type = user_types_on_page[idx_val]
                        break
                # Check if direct name match (or unique substring)
                matched_ut = [ut for ut in user_types_on_page if ut.lower() == src_input.lower()]
                if not matched_ut:
                    matched_ut = [ut for ut in user_types_on_page if src_input.lower() in ut.lower()]
                
                if len(matched_ut) == 1:
                    source_user_type = matched_ut[0]
                    break
                elif len(matched_ut) > 1:
                    print(f"  ⚠ Ambiguous input. Matches: {matched_ut}. Please be more specific.")
                else:
                    print("  ❌ Invalid choice. Please select from the list above.")

            logger.info(f"Source User Type selected: {source_user_type}")

            # Retrieve rows again to build the sequence map
            table = automation.driver.find_element(By.TAG_NAME, "table")
            rows = table.find_elements(By.TAG_NAME, "tr")

            relative_sequence_map = {}
            current_ut = "All"
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) == 1:
                    hdr_text = cells[0].text.strip()
                    match = re.search(r'^([a-zA-Z\s\-\_]+?)\s+\d+', hdr_text)
                    current_ut = match.group(1).strip().title() if match else hdr_text.strip().title()
                    continue

                if len(cells) >= 6 and current_ut.lower() == source_user_type.lower():
                    # Get sequence
                    seq_val = cells[0].text.strip()
                    _, relative_order = parse_sequence_string(seq_val)
                    
                    # Get icon identity & title
                    cell_1_text = cells[1].text.strip().replace("\n", " ")
                    id_match = re.search(r'ID:\s*([a-zA-Z0-9_\-]+)', cell_1_text)
                    icon_id = id_match.group(1).strip() if id_match else ""
                    
                    title = cell_1_text
                    color_match = re.search(r'(#[A-Fa-f0-9]{6})', cell_1_text)
                    if color_match:
                        title = title.split(color_match.group(1))[0].strip()
                    elif "ID:" in title:
                        title = title.split("ID:")[0].strip()
                    title = title.replace("", "").strip(" •-")

                    if icon_id:
                        relative_sequence_map[icon_id] = relative_order
                    elif title:
                        relative_sequence_map[title.lower()] = relative_order

            if not relative_sequence_map:
                logger.error(f"No icons found for source user type '{source_user_type}' to copy sequence.")
                print(f"\n  ❌ No icons found for source user type '{source_user_type}'.\n")
                return False

            logger.info(f"Copied relative sequence map: {relative_sequence_map}")
            print(f"\n  Copied {len(relative_sequence_map)} icon sequences from '{source_user_type}':")
            for identity, seq_num in relative_sequence_map.items():
                print(f"    - {identity}: Relative Order = {seq_num}")
            print()

            confirm = input(f"  Do you want to apply this sequence to all other user types? (y/n): ").strip().lower()
            if confirm != 'y':
                print("  Cancelled.")
                return False

            # Keep a count of failures per (user_type, icon_id/title) to avoid infinite loops
            fail_counts = {}

            # Function to find the next row that needs sequencing
            def find_next_out_of_order():
                try:
                    tbl = automation.driver.find_element(By.TAG_NAME, "table")
                    current_rows = tbl.find_elements(By.TAG_NAME, "tr")
                    curr_ut = "All"
                    for r_idx, r in enumerate(current_rows):
                        cells = r.find_elements(By.TAG_NAME, "td")
                        if len(cells) == 1:
                            hdr_text = cells[0].text.strip()
                            match = re.search(r'^([a-zA-Z\s\-\_]+?)\s+\d+', hdr_text)
                            curr_ut = match.group(1).strip().title() if match else hdr_text.strip().title()
                            continue
                        if len(cells) >= 6 and curr_ut.lower() != source_user_type.lower():
                            current_seq = cells[0].text.strip()
                            cell_1_text = cells[1].text.strip().replace("\n", " ")
                            id_match = re.search(r'ID:\s*([a-zA-Z0-9_\-]+)', cell_1_text)
                            icon_id = id_match.group(1).strip() if id_match else ""
                            
                            title = cell_1_text
                            color_match = re.search(r'(#[A-Fa-f0-9]{6})', cell_1_text)
                            if color_match:
                                title = title.split(color_match.group(1))[0].strip()
                            elif "ID:" in title:
                                title = title.split("ID:")[0].strip()
                            title = title.replace("", "").strip(" •-")

                            # Skip if this icon has failed repeatedly
                            task_key = (curr_ut, icon_id if icon_id else title.lower())
                            if fail_counts.get(task_key, 0) >= 3:
                                continue

                            rel_order = None
                            if icon_id and icon_id in relative_sequence_map:
                                rel_order = relative_sequence_map[icon_id]
                            elif title.lower() in relative_sequence_map:
                                rel_order = relative_sequence_map[title.lower()]

                            if rel_order is not None:
                                prefix = user_type_prefixes.get(curr_ut)
                                if prefix:
                                    target_seq = f"{prefix}.{rel_order}"
                                else:
                                    target_seq = rel_order

                                if current_seq != target_seq:
                                    return {
                                        "row_index": r_idx,
                                        "user_type": curr_ut,
                                        "title": title,
                                        "icon_id": icon_id,
                                        "current_seq": current_seq,
                                        "target_seq": target_seq
                                    }
                except Exception as e:
                    logger.debug(f"Error scanning table: {e}")
                return None

            max_updates = 100
            updates_count = 0
            successful_updates = 0
            failed_updates = 0

            while updates_count < max_updates:
                task = find_next_out_of_order()
                if not task:
                    logger.info("All dashboard icons are in the correct sequence order!")
                    break

                utype = task["user_type"]
                title = task["title"]
                icon_id = task["icon_id"]
                current_seq = task["current_seq"]
                target_seq = task["target_seq"]
                row_idx = task["row_index"]

                task_key = (utype, icon_id if icon_id else title.lower())
                logger.info(f"Updating: [{utype}] '{title}' (ID: '{icon_id}') from sequence {current_seq} -> {target_seq}")
                updates_count += 1

                try:
                    # Retrieve the rows again to ensure we get the fresh element reference
                    tbl = automation.driver.find_element(By.TAG_NAME, "table")
                    current_rows = tbl.find_elements(By.TAG_NAME, "tr")
                    target_row = current_rows[row_idx]
                    
                    # Verify it's the correct row just in case
                    cells = target_row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 6:
                        logger.error("Target row shifted or became invalid.")
                        continue

                    # Click actions button
                    last_cell = cells[-1]
                    action_btn = last_cell.find_element(By.XPATH, ".//button[contains(., 'Actions')]")
                    automation.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", action_btn)
                    time.sleep(0.5)
                    automation.driver.execute_script("arguments[0].click();", action_btn)

                    # Wait for Edit Config button and click it
                    edit_btn = WebDriverWait(automation.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[text()='Edit Config']/ancestor::button"))
                    )
                    automation.driver.execute_script("arguments[0].click();", edit_btn)

                    # Wait for Modal and the Order input field
                    order_input = WebDriverWait(automation.driver, 10).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//input[@id='Order' or @name='Order' or @id='order' or @name='order' or contains(@placeholder, 'Order')]"
                        ))
                    )
                    
                    # Clear and send keys
                    automation.driver.execute_script("arguments[0].value = '';", order_input)
                    order_input.send_keys(target_seq)
                    logger.info(f"  → Set order sequence to: {target_seq}")

                    # Click Save Changes / Submit button
                    submit_btn = WebDriverWait(automation.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'p-5')]//button[contains(@class,'bg-indigo-600')]"))
                    )
                    automation.driver.execute_script("arguments[0].click();", submit_btn)
                    logger.info("  → Sequence form submitted.")

                    # Wait for modal to close (submit button becomes invisible)
                    WebDriverWait(automation.driver, 15).until(
                        EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class,'p-5')]//button[contains(@class,'bg-indigo-600')]"))
                    )
                    automation._wait_toast_gone()
                    time.sleep(1.5)
                    
                    logger.info(f"  ✓ Successfully updated sequence order for [{utype}] '{title}' -> {target_seq}")
                    successful_updates += 1

                except Exception as ex:
                    logger.error(f"  ✗ Failed to update sequence for [{utype}] '{title}': {ex}")
                    fail_counts[task_key] = fail_counts.get(task_key, 0) + 1
                    try:
                        discard = automation.driver.find_element(By.XPATH, "//button[contains(text(),'Cancel') or contains(text(),'Discard')]")
                        automation.driver.execute_script("arguments[0].click();", discard)
                        time.sleep(1)
                    except Exception:
                        pass
                    failed_updates += 1

            # Final summary
            logger.info("\n" + "=" * 60)
            logger.info("SEQUENCE UPDATE SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ Successful sequence updates: {successful_updates}")
            logger.info(f"✗ Failed sequence updates: {failed_updates}")
            logger.info(f"Total actions attempted: {updates_count}")
            logger.info("=" * 60)

            return failed_updates == 0

    except Exception as e:
        logger.error(f"Unexpected error during sequence copying automation: {str(e)}")
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
    print("║   Press 15: Migrate Gifts from Old Dashboard                 ║")
    print("║   Press 16: Update Dashboard Icons (Google Sheet / Test)     ║")
    print("║   Press 16.1: Update Wallet, Scan Activity/History, Support  ║")
    print("║   Press 17: Analyze App Settings (Identity, Support & Icons) ║")
    print("║   Press 18: Product Management Image Upload                  ║")
    print("║   Press 20: Upload Missing Dashboard Icons (All User Types)  ║")
    print("║   Press 21: Ambica Cable Product Catalogue                   ║")
    print("║   Press 22: Ambica Cable Existing Product Images             ║")
    print("║   Press 23: Copy Dashboard Icons Sequence (Source to Others) ║")
    print("║   Press 0 : Exit                                             ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    return input("  Enter your choice: ").strip()


if __name__ == "__main__":
    try:
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
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
            elif choice not in {"1", "2", "3", "4", "5", "6", "7", "8", "9", "11", "12", "13", "14", "15", "16", "16.1", "17", "18", "20", "21", "22", "23"}:
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
                gift_folder = Path(__file__).resolve().parent.parent / "gift"
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

            elif choice == "15":
                logger.info("User selected: Migrate Gifts from Old Dashboard")
                success = run_old_dashboard_gift_migration(email, password)

            elif choice == "16":
                logger.info("User selected: Update Dashboard Icons (Option 16)")
                print("\n  ─── Update Dashboard Icons Options ───")
                print("  Press 1 : Update All (Google Sheet)")
                print("  Press 2 : Update All (Test Mode - mahesh@vcqru.com)")
                print("  Press 3 : Specific Update (Google Sheet)")
                print("  Press 4 : Specific Update (Test Mode - mahesh@vcqru.com)")
                print("  Press 0 : Cancel")
                print()
                sub_choice = input("  Select mode: ").strip()
                if sub_choice == "0":
                    print("\n  Cancelled.")
                    continue

                target_user_type = None
                target_icon_id = None

                if sub_choice in ("3", "4"):
                    print("\n  ─── Enter specific filters ───")
                    target_user_type = input("  Target User Type (e.g. Retailer, or leave blank for any): ").strip()
                    target_icon_id = input("  Target Icon Identity/ID (e.g. claimhistory, or leave blank for any): ").strip()
                    if not target_user_type:
                        target_user_type = None
                    if not target_icon_id:
                        target_icon_id = None

                if sub_choice in ("1", "3"):
                    success = run_dashboard_icons_sheet_update(
                        target_user_type=target_user_type,
                        target_icon_id=target_icon_id
                    )
                elif sub_choice in ("2", "4"):
                    success = run_single_update(
                        "mahesh@vcqru.com",
                        "ZNX2026",
                        target_user_type=target_user_type,
                        target_icon_id=target_icon_id
                    )
                else:
                    print("\n  ❌ Invalid sub-choice.")
                    continue

            elif choice == "16.1":
                logger.info("User selected: Update Wallet, Scan Activity, Scan History, Support, AboutUs (Option 16.1)")
                print("\n  ─── Update Specific 5 Icons Options ───")
                print("  Press 1 : Update Google Sheet Accounts")
                print("  Press 2 : Update Test Account (mahesh@vcqru.com)")
                print("  Press 3 : Update Current Logged-in Account")
                print("  Press 0 : Cancel")
                print()
                sub_choice = input("  Select mode: ").strip()
                if sub_choice == "0":
                    print("\n  Cancelled.")
                    continue

                target_user_type = input("\n  Target User Type (e.g. Retailer, or leave blank for all): ").strip()
                if not target_user_type:
                    target_user_type = None

                if sub_choice == "1":
                    success = run_dashboard_icons_special_five_sheet_update(
                        target_user_type=target_user_type
                    )
                elif sub_choice == "2":
                    success = run_dashboard_icons_special_five_update(
                        "mahesh@vcqru.com",
                        "ZNX2026",
                        target_user_type=target_user_type
                    )
                elif sub_choice == "3":
                    success = run_dashboard_icons_special_five_update(
                        email,
                        password,
                        target_user_type=target_user_type
                    )
                else:
                    print("\n  ❌ Invalid sub-choice.")
                    continue

            elif choice == "17":
                logger.info("User selected: Analyze App Settings (Identity, Support & Icons)")
                success = run_app_settings_analysis(email, password)

            elif choice == "18":
                logger.info("User selected: Product Management Image Upload")
                success = run_product_management_upload(email, password)

            elif choice == "20":
                logger.info("User selected: Upload Missing Dashboard Icons (All User Types)")
                success = run_missing_icons_upload(email, password)

            elif choice == "21":
                logger.info("User selected: Ambica Cable Product Catalogue")
                success = run_ambica_product_upload(email, password)

            elif choice == "22":
                logger.info("User selected: Ambica Cable Existing Product Images")
                success = run_ambica_image_updater(email, password)

            elif choice == "23":
                logger.info("User selected: Copy Dashboard Icons Sequence (Source to Others)")
                success = run_copy_dashboard_sequence(email, password)

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
