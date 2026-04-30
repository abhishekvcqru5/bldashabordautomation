# ⚡ Quick Reference Card

## 🚀 First Time Setup

```bash
cd /home/adminmac/Desktop/newbldashboardproject
bash automation/setup.sh
```

---

## 📌 Run Automation

```bash
# Main command (shows browser)
python3 automation/run_automation.py

# Background mode (no browser)
python3 automation/run_automation.py > /tmp/run.log 2>&1 &
```

---

## 📝 Edit Configuration

```bash
# Edit icon list
nano automation/icon_config.json

# Or use any text editor
open automation/icon_config.json          # macOS
code automation/icon_config.json          # VS Code
```

---

## 📊 Check Results

```bash
# View latest log
tail -f automation/logs/full_automation_*.log

# Check processed images
ls -lh automation/processed_images/

# View error screenshots
ls automation/screenshots/

# Count uploaded icons
grep "Icon added successfully" automation/logs/*.log | wc -l
```

---

## 🔧 Generate Bulk Config

```bash
# From CSV file
python3 automation/generate_config.py icons.csv

# Specify output file
python3 automation/generate_config.py icons.csv custom_config.json
```

---

## 🔐 Use Environment Variables

```bash
# Set credentials (better security)
export VENDOR_EMAIL="mahesh@vcqru.com"
export VENDOR_PASSWORD="180000"

# Then run
python3 automation/run_automation.py
```

---

## 🐛 Troubleshoot

```bash
# Install/update dependencies
pip3 install -r automation/requirements.txt

# Test image processor
python3 automation/image_processor.py

# Check Python version
python3 --version

# List all dependencies
pip3 list | grep -E "selenium|Pillow"
```

---

## 📁 File Locations

```
automation/
├── run_automation.py       ← MAIN SCRIPT
├── icon_config.json        ← YOUR CONFIG (edit this)
├── logs/                   ← All logs
├── screenshots/            ← Error screenshots
└── processed_images/       ← Processed images
```

---

## 🎯 Common Tasks

### Add Single Icon
Edit `icon_config.json`, add entry, run automation

### Add 100+ Icons
1. Create `icons.csv`
2. Run: `python3 automation/generate_config.py icons.csv`
3. Run: `python3 automation/run_automation.py`

### Test First Icon
1. Keep only one icon in `icon_config.json`
2. Run automation
3. Verify works
4. Add more icons

### View Upload Progress
```bash
# Monitor in real-time
tail -f automation/logs/full_automation_*.log
```

### Check Image Sizes
```bash
ls -lh automation/processed_images/
```

---

## ✅ Checklist Before Running

- [ ] Python 3.7+ installed
- [ ] Dependencies installed: `bash automation/setup.sh`
- [ ] Images in: `dashboardicons/`
- [ ] Config edited: `automation/icon_config.json`
- [ ] Internet connection active
- [ ] Chrome browser installed

---

## 🆘 Quick Fixes

| Problem | Solution |
|---------|----------|
| Module not found | `pip3 install -r automation/requirements.txt` |
| Chrome driver error | `pip3 install --upgrade webdriver-manager` |
| Permission denied | `chmod +x automation/setup.sh` |
| Python not found | Install Python 3.7+ |
| Login fails | Check email/password, check internet |
| Image not uploaded | Check image exists, check size <50KB |

---

## 📞 Where to Look

| Issue | Check |
|-------|-------|
| Upload failed | `automation/logs/full_automation_*.log` |
| Website changed | `automation/screenshots/` |
| Image too large | `ls -lh automation/processed_images/` |
| Missing file | `ls automation/` |

---

**Tip:** Save this file to your desktop or pin it in your terminal for quick access! 🚀

```bash
# Print this file
cat automation/QUICK_REFERENCE.md | less
```
