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

# Setup logging
log_dir = Path("automation/logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"full_automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
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

            icons_to_add = config.get("icons", [])

            logger.info(f"\n→ Starting batch upload of {len(icons_to_add)} icons...\n")
            successful, failed = automation.process_icons_batch(icons_to_add)

            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("AUTOMATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ Successful uploads: {successful}")
            logger.info(f"✗ Failed uploads: {failed}")
            logger.info(f"Total processed: {len(icons_to_add)}")
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
    print("║   Press 0 : Exit                                             ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    return input("  Enter your choice: ").strip()


if __name__ == "__main__":
    try:
        while True:  # ← keep looping until user quits
            choice = show_menu()

            # ── Exit ──────────────────────────────────────────────────
            if choice == "0":
                print("\n  Goodbye! 👋\n")
                sys.exit(0)

            # ── Invalid ───────────────────────────────────────────────
            elif choice not in {"1", "2", "3", "4"}:
                print(
                    f"\n  ❌ Invalid choice '{choice}'. Please enter a valid option.\n"
                )
                continue  # show menu again immediately

            # ── Ask credentials (shared for every task) ───────────────
            email, password = ask_credentials()
            if not email or not password:
                print("  ❌ Email or password cannot be empty.\n")
                continue  # show menu again

            # ── Run selected task ─────────────────────────────────────
            if choice == "1":
                logger.info("User selected: Dashboard Icons")
                success = main(email=email, password=password)

            elif choice == "2":
                logger.info("User selected: Brand Setting")
                success = run_brand_setting(email, password)

            elif choice == "3":
                logger.info("User selected: Promotion Banners")
                success = run_promotion_banners(email, password)

            elif choice == "4":
                logger.info("User selected: Intro Screens")
                success = run_intro_screens(email, password)

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

            # loop continues → menu shown again automatically

    except KeyboardInterrupt:
        print("\n\n  Interrupted. Goodbye! 👋\n")
        logger.info("Automation cancelled by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
