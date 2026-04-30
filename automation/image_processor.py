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
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def process_image(self, image_path):
        """
        Process a single image: resize and compress

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

            # Convert RGBA to RGB if necessary (for JPEG compression)
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img

            # Resize maintaining aspect ratio with padding if needed
            img = self._resize_with_aspect_ratio(img)

            # Save and compress
            output_path = self.output_folder / img_path.name

            # Try different quality levels to meet size requirement
            quality = 95
            while quality >= 10:
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
                file_size = output_path.stat().st_size

                if file_size <= self.MAX_SIZE_BYTES:
                    logger.info(
                        f"✓ Processed: {img_path.name} | "
                        f"Size: {file_size / 1024:.1f} KB | Quality: {quality}"
                    )
                    return str(output_path)

                quality -= 5

            # If still too large, reduce dimensions
            logger.warning(f"Image {img_path.name} too large even with compression, reducing size...")
            img.thumbnail((450, 450), Image.Resampling.LANCZOS)
            img = self._resize_with_aspect_ratio(img)
            img.save(output_path, 'JPEG', quality=60, optimize=True)

            file_size = output_path.stat().st_size
            logger.info(
                f"✓ Processed (reduced): {img_path.name} | "
                f"Size: {file_size / 1024:.1f} KB"
            )
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to process {image_path}: {str(e)}")
            return None

    def _resize_with_aspect_ratio(self, img):
        """
        Resize image to 512x512 maintaining aspect ratio
        Pads with white background if needed
        """
        # Calculate scaling to fit within 512x512
        width_ratio = self.TARGET_SIZE[0] / img.width
        height_ratio = self.TARGET_SIZE[1] / img.height
        ratio = min(width_ratio, height_ratio)

        # If image is smaller, don't upscale too much
        if ratio > 1:
            ratio = min(ratio, 1.0)

        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Create 512x512 canvas with white background
        canvas = Image.new('RGB', self.TARGET_SIZE, (255, 255, 255))

        # Calculate position to center the image
        x_offset = (self.TARGET_SIZE[0] - img.width) // 2
        y_offset = (self.TARGET_SIZE[1] - img.height) // 2

        canvas.paste(img, (x_offset, y_offset))
        return canvas

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
