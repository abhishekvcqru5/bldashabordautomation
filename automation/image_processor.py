"""
Image Processor Module
Handles resizing and compression of images for dashboard icons
- Target: 512x512 px, max 50 KB
- Uses PIL/Pillow for smart resizing (maintains aspect ratio)
"""

import os
import logging
from pathlib import Path
from PIL import Image
import shutil

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Process images: resize to 512x512 and compress to <50KB"""

    TARGET_SIZE = (512, 512)
    MAX_SIZE_KB = 50
    MAX_SIZE_BYTES = MAX_SIZE_KB * 1024

    def __init__(self, input_folder, output_folder):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        if self.output_folder.exists():
            for f in self.output_folder.iterdir():
                if f.is_file():
                    try:
                        f.unlink()
                    except Exception as e:
                        logger.warning(f"Could not delete old file {f}: {e}")
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def process_image(self, image_path):
        """
        Process a single image: resize and compress
        Preserves transparent backgrounds for PNGs.

        Args:
            image_path: Path to the image file

        Returns:
            Path to processed image or None if failed
        """
        try:
            img_path = Path(image_path)

            if not img_path.exists():
                logger.error(f"Image not found: {image_path}")
                return None

            # Open image
            img = Image.open(img_path)
            
            is_png = img_path.suffix.lower() == '.png'

            # Force resize to exact target dimensions (512x512!)
            img = img.resize(self.TARGET_SIZE, Image.Resampling.LANCZOS)

            # Save and compress
            output_path = self.output_folder / img_path.name

            if is_png:
                # Save as PNG with transparency preserved
                img.save(output_path, 'PNG', optimize=True)
                file_size = output_path.stat().st_size
                
                # If still too large (> 50KB), convert to palette mode (P) to compress while maintaining transparency
                if file_size > self.MAX_SIZE_BYTES:
                    logger.info(f"PNG {img_path.name} is {file_size / 1024:.1f} KB, compressing via quantize...")
                    quantized_img = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
                    quantized_img.save(output_path, 'PNG', optimize=True)
                    file_size = output_path.stat().st_size
                    
                logger.info(
                    f"✓ Processed PNG: {img_path.name} | "
                    f"Size: {file_size / 1024:.1f} KB"
                )
                return str(output_path)
            else:
                # Convert RGBA to RGB if necessary (for JPEG compression)
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = rgb_img

                # Try different quality levels to meet size requirement
                quality = 95
                while quality >= 10:
                    img.save(output_path, 'JPEG', quality=quality, optimize=True)
                    file_size = output_path.stat().st_size

                    if file_size <= self.MAX_SIZE_BYTES:
                        logger.info(
                            f"✓ Processed JPEG: {img_path.name} | "
                            f"Size: {file_size / 1024:.1f} KB | Quality: {quality}"
                        )
                        return str(output_path)

                    quality -= 5

                # If still too large, force lower quality
                img.save(output_path, 'JPEG', quality=40, optimize=True)
                file_size = output_path.stat().st_size
                logger.info(
                    f"✓ Processed (low quality JPEG): {img_path.name} | "
                    f"Size: {file_size / 1024:.1f} KB"
                )
                return str(output_path)

        except Exception as e:
            logger.error(f"Failed to process {image_path}: {str(e)}")
            return None

    def _resize_with_aspect_ratio(self, img):
        """
        [DEPRECATED] Resize image to 512x512 maintaining aspect ratio
        Pads with white background if needed.
        User now prefers forced resize (no padding).
        """
        return img.resize(self.TARGET_SIZE, Image.Resampling.LANCZOS)

    def process_all_images(self):
        """Process all images in input folder"""
        logger.info(f"Processing images from: {self.input_folder}")
        logger.info(f"Output folder: {self.output_folder}")
        logger.info(f"Target: 512x512 px, max {self.MAX_SIZE_KB} KB\n")

        processed = {}
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}

        for img_file in self.input_folder.iterdir():
            if img_file.suffix.lower() in image_extensions:
                output_path = self.process_image(img_file)
                if output_path:
                    processed[img_file.name] = output_path

        logger.info(f"\n✓ Processed {len(processed)} images successfully\n")
        return processed


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Example usage
    input_dir = "/home/adminmac/Desktop/newbldashboardproject/dashboardicons"
    output_dir = "/home/adminmac/Desktop/newbldashboardproject/automation/processed_images"

    processor = ImageProcessor(input_dir, output_dir)
    processor.process_all_images()
