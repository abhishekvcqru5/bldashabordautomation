# Dashboard Icons Automation System

Fully automated solution for uploading dashboard icons to your vendor portal. This system handles:

✅ **Image Processing** - Automatically resizes and compresses images to 512x512px and <50KB  
✅ **Smart Login** - Automated authentication to vendor portal  
✅ **Batch Upload** - Uploads multiple icons in sequence  
✅ **Error Handling** - Continues on failure, logs everything  
✅ **Screenshots** - Captures screenshots for debugging  
✅ **Detailed Logging** - Complete logs of every action  

---

## 📋 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**What you need:**
- Python 3.7+
- pip (Python package manager)
- Chrome browser (Selenium will control it)

### 2. Run the Automation

```bash
cd /home/adminmac/Desktop/newbldashboardproject
python automation/run_automation.py
```

The script will:
1. Process all images in `dashboardicons/` folder
2. Compress them to meet size requirements
3. Log into your vendor account
4. Upload all configured icons
5. Generate logs and screenshots

---

## 🔧 Setup Instructions

### Step 1: Verify Python Installation

```bash
python3 --version
```

Should show Python 3.7 or higher.

### Step 2: Install Requirements

```bash
pip install -r automation/requirements.txt
```

**Packages installed:**
- `selenium` - Browser automation
- `Pillow` - Image processing
- `webdriver-manager` - Automatic ChromeDriver management

### Step 3: Configure Your Icons

Edit `automation/icon_config.json` to add/modify icons:

```json
{
  "icons": [
    {
      "user_type": "customer",
      "icon_identity": "gift",
      "display_title": "Gift",
      "image_path": "automation/processed_images/Gift.png",
      "toggle_option": "both"
    }
  ]
}
```

**Fields:**
- `user_type` - Target user type (customer, vendor, retailer, plumber, etc.)
- `icon_identity` - Icon ID (must match dropdown options)
- `display_title` - Label shown in dashboard
- `image_path` - Path to image file (will be auto-processed)
- `toggle_option` - "both", "side menu", or "dashboard only"

### Step 4: Prepare Your Images

Place your images in `dashboardicons/` folder. The system will:
- Resize to 512x512px (maintains aspect ratio, white padding if needed)
- Compress to <50KB
- Convert to JPEG for optimal compression

**Supported formats:** PNG, JPG, JPEG, GIF, BMP, TIFF

---

## 🚀 Running the Automation

### Basic Usage

```bash
python automation/run_automation.py
```

The browser window will open and you can watch the process. It will:
1. Log in automatically
2. Navigate to dashboard icons
3. Click "Add new item" for each icon
4. Fill all fields
5. Upload image
6. Submit and repeat

### With Environment Variables (Secure)

Instead of hardcoding credentials, use environment variables:

```bash
# Linux/Mac
export VENDOR_EMAIL="mahesh@vcqru.com"
export VENDOR_PASSWORD="180000"
python automation/run_automation.py

# Windows
set VENDOR_EMAIL=mahesh@vcqru.com
set VENDOR_PASSWORD=180000
python automation/run_automation.py
```

### Headless Mode (No Browser Window)

Edit `run_automation.py` and change:
```python
with VendorPortalAutomation(email, password, headless=True) as automation:
```

---

## 📁 File Structure

```
automation/
├── run_automation.py           # Main entry point - RUN THIS
├── dashboard_automation.py     # Selenium automation logic
├── image_processor.py          # Image resizing/compression
├── icon_config.json            # Configuration file (edit this)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── processed_images/           # Auto-generated processed images
├── logs/                       # Auto-generated logs
└── screenshots/                # Auto-generated screenshots
```

---

## 📊 Logs and Reports

After running, check:

```bash
# View logs
cat automation/logs/full_automation_*.log

# View latest log
ls -t automation/logs/ | head -1 | xargs -I {} cat automation/logs/{}

# View screenshots if errors occurred
ls automation/screenshots/
```

Each log file contains:
- Timestamp of every action
- Success/failure status
- File sizes and compression details
- Any errors or warnings
- Final summary with success rate

---

## ⚙️ Customization

### Adding Multiple User Types

```json
{
  "icons": [
    {
      "user_type": "customer",
      "icon_identity": "gift",
      "display_title": "Gift",
      "image_path": "automation/processed_images/Gift.png",
      "toggle_option": "both"
    },
    {
      "user_type": "vendor",
      "icon_identity": "gift",
      "display_title": "Gift",
      "image_path": "automation/processed_images/Gift.png",
      "toggle_option": "both"
    }
  ]
}
```

### Changing Retry Behavior

In `dashboard_automation.py`, adjust:
```python
self.wait_time = 15  # Seconds to wait for element
```

### Changing Image Compression Settings

In `image_processor.py`, adjust:
```python
TARGET_SIZE = (512, 512)
MAX_SIZE_KB = 50
```

---

## 🐛 Troubleshooting

### Issue: Chrome driver not found

**Solution:**
```bash
pip install --upgrade webdriver-manager
```

### Issue: Login fails

**Solutions:**
1. Check credentials are correct
2. Check internet connection
3. Verify website isn't blocking automated logins
4. Check screenshots in `automation/screenshots/`

### Issue: Images won't upload

**Solutions:**
1. Check image is in processed_images folder
2. Verify path in icon_config.json is correct
3. Check image size: should be <50KB and 512x512px
4. Look at logs for specific error message

### Issue: Form fields not found

**Solutions:**
1. Website might have changed HTML structure
2. Check screenshot for what's on screen
3. May need to update XPath selectors in code

---

## 🔐 Security Notes

⚠️ **IMPORTANT:** 
- Never commit `requirements.txt` with credentials
- Use environment variables for credentials
- Keep logs private (they may contain sensitive data)
- Consider using a password manager

To use environment variables instead of hardcoding:

**Linux/Mac:**
```bash
export VENDOR_EMAIL="your-email@example.com"
export VENDOR_PASSWORD="your-password"
```

**Windows:**
```cmd
setx VENDOR_EMAIL "your-email@example.com"
setx VENDOR_PASSWORD "your-password"
```

---

## 📈 Scaling to 100+ Icons

If you need to upload 100+ icons:

1. **Prepare CSV file** with icon data:
   ```csv
   user_type,icon_identity,display_title,image_file
   customer,gift,Gift,Gift.png
   customer,history,History,history.png
   ```

2. **Create icon_config.json from CSV:**
   ```bash
   python automation/generate_config.py config.csv
   ```

3. **Run automation:**
   ```bash
   python automation/run_automation.py
   ```

The system will handle 100+ uploads automatically with proper delays between uploads.

---

## 🎯 What This Automates

**Manual Process (Per Icon):**
- Click "Add new item" ❌ → ✅ Automated
- Select user type from dropdown ❌ → ✅ Automated  
- Select icon identity ❌ → ✅ Automated
- Enter display title ❌ → ✅ Automated
- Select toggle option ❌ → ✅ Automated
- Resize image to 512x512 ❌ → ✅ Automated
- Compress image to <50KB ❌ → ✅ Automated
- Upload image ❌ → ✅ Automated
- Submit form ❌ → ✅ Automated

**Time Saved:**
- Manual: ~2-3 minutes per icon × 100 = **200-300 minutes (3-5 hours)**
- Automated: ~30 seconds per icon × 100 = **50 minutes** (including login)

**Saves: 2-4 hours!**

---

## 📞 Support

If something doesn't work:

1. **Check the logs:** `cat automation/logs/full_automation_*.log`
2. **Check screenshots:** `ls automation/screenshots/`
3. **Check image sizes:** `ls -lh automation/processed_images/`
4. **Verify config:** `cat automation/icon_config.json`

---

## 🎓 Example Workflow

```bash
# 1. Install (first time only)
pip install -r automation/requirements.txt

# 2. Add/edit icons in automation/icon_config.json

# 3. Run automation
cd /home/adminmac/Desktop/newbldashboardproject
python automation/run_automation.py

# 4. Monitor progress in browser window

# 5. Check results
cat automation/logs/full_automation_*.log
```

That's it! ✨

---

## Version Info

- **Python:** 3.7+
- **Selenium:** 4.15.2
- **Pillow:** 10.1.0
- **Created:** 2024
- **Last Updated:** 2024

Enjoy your automated uploads! 🚀
