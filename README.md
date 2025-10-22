# 🗜️ PDF Batch Compressor for Mega

Automatic batch PDF compressor with Mega cloud storage integration and GitHub Actions.

[![Compress PDFs](https://github.com/username/pdf-compressor/actions/workflows/compress-pdfs.yml/badge.svg)](https://github.com/username/pdf-compressor/actions/workflows/compress-pdfs.yml)
[![Manual Compression](https://github.com/username/pdf-compressor/actions/workflows/manual-trigger.yml/badge.svg)](https://github.com/username/pdf-compressor/actions/workflows/manual-trigger.yml)

## ✨ Features

- 🚀 **Automatic compression** of PDF files on schedule
- 🗂️ **Mega integration** - direct work with cloud storage
- 🤖 **GitHub Actions** - completely free automation
- 🎯 **Smart compression** - optimal algorithm selection for each file
- 📊 **Detailed statistics** - reports on space and time savings
- 📱 **Telegram notifications** - receive results on your phone
- 🛡️ **Security** - backup and integrity verification
- ⚙️ **Flexible configuration** - various compression parameters

## 📋 Compression Algorithms

The project uses several compression methods for optimal results:

| Tool | Best for | Typical savings |
|------|----------|-----------------|
| **Ghostscript** | Files with images, scans | 60-90% |
| **QPDF** | Universal compression | 70-85% |
| **Pikepdf** | Files with forms, safe compression | 70-85% |
| **PyPDF** | Simple PDF files | 80-95% |

### Compression Levels

- **🟢 Low**: Minimal quality loss (printer quality)
- **🟡 Medium**: Balance of size and quality (e-books)
- **🔴 High**: Maximum compression (web usage)

## 🚀 Quick Start

### 1. Repository Setup

1. **Fork this repository** or create a new one
2. **Add GitHub Secrets** in repository settings:

```bash
MEGA_EMAIL=your-mega-email@example.com
MEGA_PASSWORD=your-mega-password
TELEGRAM_BOT_TOKEN=your-telegram-bot-token  # (optional)
TELEGRAM_CHAT_ID=your-telegram-chat-id      # (optional)
```

### 2. Setup Folders in Mega

Create the following folders in your Mega account:

```
/PDF/
├── Input/          # Source files for compression
├── Compressed/     # Compressed files
├── Backup/         # Backup copies (optional)
└── Processed/      # Archive of processed files
```

### 3. Configuration Setup

Edit `config/settings.yaml` to your needs:

```yaml
folders:
  input: "/PDF/Input"
  output: "/PDF/Compressed"
  backup: "/PDF/Backup"

compression:
  default_level: "medium"
  
limits:
  max_files_per_run: 50
  max_file_size_mb: 200
```

### 4. Running

After setup, the system works automatically:

- **Automatically**: every day at 2:00 and 14:00 UTC
- **Manually**: through "Actions" tab → "Manual PDF Compression" → "Run workflow"

## 📖 Usage

### Automatic Compression

Simply place PDF files in the `/PDF/Input` folder in your Mega account. The system will automatically:

1. Find new PDF files
2. Download them for processing
3. Apply optimal compression algorithm
4. Upload compressed files to `/PDF/Compressed` folder
5. Delete original files (with backup)
6. Send report to Telegram

### Manual Run

For manual run, go to Actions → Manual PDF Compression and specify parameters:

- **Source folder**: source folder (e.g., `/PDF/Input`)
- **Target folder**: folder for compressed files
- **Compression level**: compression level (low/medium/high)
- **Max files**: maximum number of files at once
- **Dry run**: test mode without changes

### Monitoring

- **GitHub Actions**: view execution logs
- **Artifacts**: download detailed reports
- **Telegram**: receive brief notifications
- **Issues**: automatic creation on errors

## 📊 Statistics

The system maintains detailed statistics:

```json
{
  "processed_files": 25,
  "failed_files": 2,
  "total_size_before": 150000000,
  "total_size_after": 45000000,
  "total_bytes_saved": 105000000,
  "total_percent_saved": 70.0,
  "duration": 245.6,
  "compression_level": "medium"
}
```

## ⚙️ Configuration

### Main Settings

**config/settings.yaml**:

```yaml
# Folders in Mega
folders:
  input: "/PDF/Input"
  output: "/PDF/Compressed"
  backup: "/PDF/Backup"

# Compression levels
compression:
  default_level: "medium"
  levels:
    low:
      ghostscript_preset: "printer"
      image_quality: 85
      image_resolution: 150
    medium:
      ghostscript_preset: "ebook"
      image_quality: 75
      image_resolution: 120
    high:
      ghostscript_preset: "screen"
      image_quality: 60
      image_resolution: 96

# Limits
limits:
  max_files_per_run: 50
  max_file_size_mb: 200
  min_file_size_kb: 100
  timeout_minutes: 60

# File filters
filters:
  skip_patterns:
    - "*compressed*"
    - "*_comp.pdf"
    - "*optimized*"
  min_compression_percent: 5

# Security
safety:
  create_backup: true
  verify_compression: true
  rollback_on_error: true

# Notifications
notifications:
  telegram:
    enabled: true
    on_success: true
    on_error: true
```

### GitHub Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `MEGA_EMAIL` | ✅ | Your Mega account email |
| `MEGA_PASSWORD` | ✅ | Mega account password |
| `TELEGRAM_BOT_TOKEN` | ❌ | Telegram bot token for notifications |
| `TELEGRAM_CHAT_ID` | ❌ | Chat ID for notifications |

### Setting Up Telegram Notifications

1. Create a bot via [@BotFather](https://t.me/botfather)
2. Get bot token
3. Find your Chat ID via [@userinfobot](https://t.me/userinfobot)
4. Add tokens to GitHub Secrets

## 🛠️ Local Development

### Installation

```bash
git clone https://github.com/username/pdf-compressor.git
cd pdf-compressor

# Install dependencies
pip install -r requirements.txt

# System dependencies (Ubuntu/Debian)
sudo apt-get install ghostscript qpdf poppler-utils

# Create .env file
cp .env.example .env
# Edit .env with your credentials
```

### Running

```bash
# Test run
python src/main.py --dry-run

# Normal run
python src/main.py \
  --source "/PDF/Input" \
  --target "/PDF/Compressed" \
  --level medium \
  --max-files 10

# With logging settings
python src/main.py \
  --log-file logs/compression.log \
  --log-level DEBUG
```

### Testing

```bash
# Test compressor
python src/compressor.py

# Test Mega client
python src/mega_client.py

# Test configuration
python src/config.py
```

## 📁 Project Structure

```
pdf-compressor/
├── .github/workflows/       # GitHub Actions
│   ├── compress-pdfs.yml   # Main workflow
│   └── manual-trigger.yml  # Manual trigger
├── src/                     # Source code
│   ├── main.py             # Main script
│   ├── compressor.py       # PDF compression logic
│   ├── mega_client.py      # Mega client
│   ├── config.py           # Configuration management
│   └── utils.py            # Utilities
├── scripts/                 # Helper scripts
│   ├── generate_report.py  # Report generation
│   └── send_notification.py # Telegram notifications
├── config/                  # Configuration
│   └── settings.yaml       # Main settings
├── requirements.txt         # Python dependencies
└── README.md               # Documentation
```

## 🔧 Advanced Features

### File Filtering

Configure which files to process:

```yaml
filters:
  # Skip files by patterns
  skip_patterns:
    - "*compressed*"
    - "*_small.pdf"
    - "temp_*"
  
  # File sizes
  min_file_size_kb: 100
  max_file_size_mb: 200
  
  # Minimum compression percentage to keep
  min_compression_percent: 5
```

### Multiple Folders

Process multiple folders:

```bash
# Via workflow parameters
python src/main.py --source "/PDF/Documents" --target "/PDF/Documents/Compressed"
python src/main.py --source "/PDF/Scans" --target "/PDF/Scans/Compressed"
```

### Schedule Customization

Change schedule in `.github/workflows/compress-pdfs.yml`:

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
    - cron: '0 2 * * 1'    # Every Monday at 2:00
```

## 🐛 Troubleshooting

### Common Errors

**1. Mega Connection Error**
```
❌ Mega connection error: Login failed
```
**Solution**: Check correctness of `MEGA_EMAIL` and `MEGA_PASSWORD`

**2. GitHub Actions Limits Exceeded**
```
❌ Job was cancelled due to timeout
```
**Solution**: Reduce `max_files_per_run` or increase `timeout-minutes`

**3. Compression Error**
```
❌ All compression methods failed
```
**Solution**: File may be corrupted or encrypted

### Debugging

Enable verbose logging:

```yaml
# In workflow
--log-level DEBUG
```

Check workflow artifacts for detailed logs.

## 🤝 Contributing

Improvements are welcome! Please:

1. Fork the repository
2. Create a branch for changes
3. Add tests if needed
4. Create a Pull Request

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [mega.py](https://github.com/richardpenman/mega.py) - Python client for Mega
- [pikepdf](https://github.com/pikepdf/pikepdf) - PDF manipulation in Python
- [Ghostscript](https://www.ghostscript.com/) - Professional PDF compression
- [QPDF](https://github.com/qpdf/qpdf) - PDF tools

---

<div align="center">
  
**🗜️ Save cloud space automatically!**

[🐛 Report Bug](https://github.com/username/pdf-compressor/issues) • [💡 Request Feature](https://github.com/username/pdf-compressor/issues) • [📚 Wiki](https://github.com/username/pdf-compressor/wiki)

</div>

## 📊 Recent Statistics

- **Last run:** 2025-10-22
- **Files processed:** 2
- **Space saved:** 32.8 KB (6.3%)
- **Compression level:** medium

*Statistics updated automatically after each compression job.*