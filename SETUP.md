# 🚀 Dashboard Icons Automation - SETUP GUIDE

Your automated dashboard icon upload system is ready! Follow these simple steps to get started.

---

## ⏱️ 5-Minute Quick Start

### Step 1: Install Dependencies (2 minutes)

Open Terminal and run:

```bash
cd /home/adminmac/Desktop/newbldashboardproject
bash automation/setup.sh
```

This will:
- Check Python installation ✓
- Install required packages ✓
- Create necessary folders ✓
- Verify everything is ready ✓

### Step 2: Configure Your Icons (1 minute)

Edit this file: `automation/icon_config.json`

The file already has your dashboard icons configured. Review it to make sure it matches your needs.

### Step 3: Run Automation (2 minutes)

```bash
python3 automation/run_automation.py
```

That's it! The browser will open and the automation will:
1. ✅ Log in to your vendor account
2. ✅ Process and compress images
3. ✅ Upload all configured icons
4. ✅ Generate detailed logs

---

## 📋 What You Have

### Files Created:

```
automation/
├── run_automation.py              ← MAIN SCRIPT (RUN THIS)
├── dashboard_automation.py        ← Selenium automation
├── image_processor.py             ← Image resizing/compression
├── icon_config.json              ← Your icon configuration
├── requirements.txt              ← Python dependencies
├── setup.sh                       ← Setup script
├── generate_config.py            ← Bulk config generator
├── README.md                      ← Detailed documentation
├── logs/                          ← (Auto-created) Detailed logs
├── screenshots/                   ← (Auto-created) Error screenshots
└── processed_images/              ← (Auto-created) Optimized images
```

---

## 🎯 How It Works

### The Automation Handles:

| Task | Manual | Automated |
|------|--------|-----------|
| Image Resizing (512x512) | ❌ 30 seconds | ✅ Automatic |
| Image Compression (<50KB) | ❌ 30 seconds | ✅ Automatic |
| Login to portal | ❌ 30 seconds | ✅ Automatic |
| Click "Add new item" | ❌ 5 seconds | ✅ Automatic |
| Select dropdowns | ❌ 10 seconds | ✅ Automatic |
| Enter text fields | ❌ 5 seconds | ✅ Automatic |
| Upload image | ❌ 10 seconds | ✅ Automatic |
| Submit form | ❌ 5 seconds | ✅ Automatic |
| **Total per icon** | **~3 minutes** | **~30 seconds** |
| **For 100 icons** | **~5 hours** | **~50 minutes** |

---

## 🔧 Configuration Guide

### Icon Configuration File

Edit: `automation/icon_config.json`

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

**Field Explanations:**

- **user_type**: The user type this icon is for (e.g., "customer", "vendor", "plumber", "retailer")
- **icon_identity**: The icon's ID in dropdown (e.g., "gift", "history", "wallet")
- **display_title**: The label shown in dashboard (e.g., "Gift", "My History", "My Wallet")
- **image_path**: Path to your processed image (auto-populated from processed_images folder)
- **toggle_option**: Display location - "both", "side menu", or "dashboard only"

### Bulk Import from CSV

If you have 100+ icons, create a CSV file with:

```csv
user_type,icon_identity,display_title,image_file,toggle_option
customer,gift,Gift,Gift.png,both
customer,history,History,history.png,both
vendor,ecommerce,E-Commerce,ecommerce.png,both
vendor,blog,Blog,blog.png,both
```

Then generate config:

```bash
python3 automation/generate_config.py your_icons.csv
```

---

## 🖼️ Image Requirements

Your images are automatically processed to meet these requirements:

- **Size**: 512 × 512 pixels
- **File Size**: Maximum 50 KB
- **Format**: JPEG (auto-converted)
- **Quality**: Optimized for visual quality while staying under size limit

### What the Image Processor Does:

1. **Maintains aspect ratio** - No stretching or distortion
2. **Adds white padding** - If image is smaller than 512x512
3. **Compresses intelligently** - Adjusts quality to stay under 50KB
4. **Handles all formats** - PNG, JPG, GIF, BMP, TIFF, etc.

### Example:

```
Original: Gift.png (150×150px, 25KB)
          ↓
Processed: Gift.png (512×512px, white padding, 35KB) ✓
```

---

## ▶️ Running the Automation

### Basic Usage

```bash
python3 automation/run_automation.py
```

The browser will open and show:
- Login process
- Each icon being added
- Progress in terminal
- Any errors with screenshots

### View Logs

```bash
# View latest log
tail -f automation/logs/full_automation_*.log

# Or open all logs
ls -lt automation/logs/ | head -5
```

### Check Processed Images

```bash
# View all processed images
ls -lh automation/processed_images/

# Check specific image size
ls -lh automation/processed_images/Gift.png
```

---

## 🔐 Security

Your credentials are embedded in the config (don't commit to git!).

### Better Way - Environment Variables:

```bash
# Set once in your terminal
export VENDOR_EMAIL="mahesh@vcqru.com"
export VENDOR_PASSWORD="180000"

# Then run
python3 automation/run_automation.py
```

The script will use these instead of hardcoded values.

---

## 🐛 Troubleshooting

### Issue: "Chrome driver not found"

```bash
pip3 install --upgrade webdriver-manager
python3 automation/run_automation.py
```

### Issue: "Module not found: selenium"

```bash
pip3 install -r automation/requirements.txt
```

### Issue: Login fails

1. Check email and password are correct
2. Verify internet connection
3. Check screenshots: `ls automation/screenshots/`
4. Check logs: `tail automation/logs/full_automation_*.log`

### Issue: Images won't upload

1. Verify images are in `dashboardicons/` folder
2. Check processed images: `ls automation/processed_images/`
3. Verify sizes: `ls -lh automation/processed_images/`
4. Check logs for error message

### Issue: Form elements not found

Website HTML might have changed. Check screenshot and manual run to see current form structure.

---

## 📊 What Gets Logged

Every run creates a detailed log file with:

- ✅ Timestamp of each action
- ✅ Success/failure status for each icon
- ✅ Image sizes and compression details
- ✅ Exact form values being submitted
- ✅ Any errors or warnings
- ✅ Final summary with success rate

Example log output:

```
2024-01-15 10:30:45 - INFO - 🚀 Dashboard Icons Automation Started
2024-01-15 10:30:45 - INFO - STEP 1: Processing and Compressing Images
2024-01-15 10:30:46 - INFO - ✓ Processed: Gift.png | Size: 35.2 KB | Quality: 95
2024-01-15 10:30:47 - INFO - ✓ Login successful
2024-01-15 10:30:48 - INFO - [1/13] Processing icon...
2024-01-15 10:30:49 - INFO - Adding icon: Gift
2024-01-15 10:30:50 - INFO - ✓ Icon added successfully
```

---

## 🎓 Example Workflow

### Scenario: Upload 13 icons every month

**Setup (First Time):**
```bash
cd /home/adminmac/Desktop/newbldashboardproject
bash automation/setup.sh
# ~2 minutes
```

**Monthly Upload:**
```bash
# Edit icon_config.json with new icons if needed
# (already configured with your 13 icons)

python3 automation/run_automation.py
# ~3 minutes for all 13 icons
```

**Check Results:**
```bash
tail automation/logs/full_automation_*.log
```

**Total time: ~5 minutes** (vs ~1-2 hours manual)

---

## 📈 Scaling Up

### For 50+ Icons:

1. Prepare CSV with all icon data
2. Generate config from CSV
3. Run automation once
4. All 50+ icons uploaded in ~30 minutes

### For 100+ Icons:

Same process, will complete in ~1-2 hours (with automatic delays to avoid rate limiting)

---

## 💡 Tips & Tricks

### Batch Different User Types

```json
{
  "icons": [
    {
      "user_type": "customer",
      "icon_identity": "gift",
      ...
    },
    {
      "user_type": "vendor",
      "icon_identity": "gift",
      ...
    }
  ]
}
```

### Test With One Icon First

Edit config to have just one icon, run automation, verify it works.

### Run in Background

```bash
python3 automation/run_automation.py > run.log 2>&1 &
```

### Schedule Daily/Weekly Runs

**Linux/Mac (cron):**
```bash
# Edit crontab
crontab -e

# Add line (runs every Monday at 9 AM)
0 9 * * 1 cd /path/to/project && python3 automation/run_automation.py
```

---

## 📞 Need Help?

Check in this order:

1. **Read the logs:** `automation/logs/full_automation_*.log`
2. **Check screenshots:** `automation/screenshots/`
3. **Review config:** `automation/icon_config.json`
4. **Read full docs:** `automation/README.md`

---

## ✨ You're All Set!

Your automation system is ready to save you hours of repetitive work.

### Next Steps:

1. ✅ Run setup: `bash automation/setup.sh`
2. ✅ Review config: `automation/icon_config.json`
3. ✅ Run automation: `python3 automation/run_automation.py`
4. ✅ Check logs: `tail automation/logs/full_automation_*.log`

**Enjoy your saved time!** 🚀

---

*Created: 2024 | Automation saves ~3-5 hours per 100 icons*
