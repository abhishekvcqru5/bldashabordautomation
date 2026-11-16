import fitz
import os
import json
import csv
import re
from PIL import Image
from catalog_manifest import PRODUCTS, BASE_DIR

def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '_', text)

doc = fitz.open("HI_CHOICE_CATALOGUE.pdf")

final_records = []

for idx, p in enumerate(PRODUCTS):
    cat_slug = slugify(p["category"])
    cat_dir = BASE_DIR / cat_slug
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    prod_slug = slugify(p["name"])
    img_filename = f"{prod_slug}.jpg"
    img_path = cat_dir / img_filename
    
    page_num = p["page"]
    page = doc[page_num - 1]
    
    # 1. Image extraction / crop
    if p["xref"] is not None:
        # Extract embedded image directly
        base = doc.extract_image(p["xref"])
        img_bytes = base["image"]
        with open(img_path, "wb") as f:
            f.write(img_bytes)
    elif p["crop_box"] is not None:
        # Crop from rendered page
        # crop_box is (x0, y0, x1, y1) in page coordinate points
        x0, y0, x1, y1 = p["crop_box"]
        # Render high-dpi rect
        rect = fitz.Rect(x0, y0, x1, y1)
        pix = page.get_pixmap(dpi=200, clip=rect)
        pix.save(str(img_path))
    else:
        # Fallback render full page
        pix = page.get_pixmap(dpi=150)
        pix.save(str(img_path))
        
    # Verify image saved
    if img_path.exists():
        # Check size with PIL
        try:
            with Image.open(img_path) as im:
                # convert RGBA to RGB if needed
                if im.mode in ("RGBA", "P"):
                    im = im.convert("RGB")
                    im.save(str(img_path), "JPEG", quality=95)
        except Exception as e:
            print(f"PIL process error on {img_path}: {e}")

    # Build record matching VendorPortal fields exactly
    record = {
        "id": idx + 1,
        "product name": p["name"],
        "category name": p["category"],
        "sub-classification": p["sub_category"],
        "product narrative / description": p["description"],
        "listing price (₹)": str(p["listing_price"]),
        "offer price (₹)": str(p["offer_price"]),
        "unit inventory": "50",
        "loyalty yield": str(p["offer_price"]),
        "image_path": str(img_path.resolve())
    }
    final_records.append(record)
    print(f"[{idx+1}/{len(PRODUCTS)}] Extracted: {p['name']} -> {img_path.name}")

# Save master JSON
json_path = BASE_DIR / "hi_choice_products.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(final_records, f, indent=2, ensure_ascii=False)

# Save master CSV
csv_path = BASE_DIR / "hi_choice_products.csv"
fieldnames = [
    "id",
    "product name",
    "category name",
    "sub-classification",
    "product narrative / description",
    "listing price (₹)",
    "offer price (₹)",
    "unit inventory",
    "loyalty yield",
    "image_path"
]
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(final_records)

print(f"\nAll {len(final_records)} products extracted successfully!")
print(f"Master files saved:\n  - {json_path}\n  - {csv_path}")
