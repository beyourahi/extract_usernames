# Notion Integration Setup Guide

Complete walkthrough for setting up the Instagram to Notion sync workflow.

## Prerequisites

- ✅ Notion account (free or paid)
- ✅ "Client Hunt" database created in Notion
- ✅ Python 3.9+ with dependencies installed
- ✅ Instagram Username Extractor working

## Step 1: Create Notion Integration

1. Visit [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Configure the integration:
   - **Name**: `Instagram Lead Extractor` (or any name you prefer)
   - **Associated workspace**: Select your workspace
   - **Type**: Internal integration
   - **Capabilities**: ✓ Read content, ✓ Update content, ✓ Insert content
4. Click **"Submit"**
5. **Copy the Integration Token** (starts with `secret_...`)
   - ⚠️ Keep this secret! Never share or commit to Git

## Step 2: Share Database with Integration

Your integration needs explicit permission to access your database.

1. Open your **"Client Hunt"** database in Notion
2. Click the **⋮** (three dots) menu in the top-right corner
3. Select **"Add connections"** or **"Connect to"**
4. Search for **"Instagram Lead Extractor"** (your integration name)
5. Click **"Confirm"** to grant access

✅ You should see your integration listed in the database connections.

## Step 3: Get Database ID

You need the unique ID of your "Client Hunt" database.

### Method 1: From Browser URL (Easiest)

1. Open your "Client Hunt" database in Notion
2. Copy the URL from your browser address bar
3. The URL looks like:
   ```
   https://www.notion.so/workspace-name/300472d4ce5181a4af1fc68082b64113?v=...
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                         This is your database ID (32 characters)
   ```
4. Copy the 32-character ID (with or without dashes)

### Method 2: From Share Link

1. Click **"Share"** button in your database
2. Click **"Copy link"**
3. Extract the 32-character ID from the link

### Method 3: From Database Settings

1. Click **⋮** menu → **"View database"**
2. Database ID is in the URL

## Step 4: Configure Environment Variables

1. Navigate to your `extract_usernames` project directory:
   ```bash
   cd /path/to/extract_usernames
   ```

2. Create `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your favorite text editor:
   ```bash
   nano .env
   # or
   code .env
   ```

4. Add your credentials:
   ```env
   NOTION_TOKEN=secret_your_actual_integration_token_here
   NOTION_DATABASE_ID=300472d4ce5181a4af1fc68082b64113
   ```

5. Save and close the file

⚠️ **Security Notes:**
- Never commit `.env` to Git (already in `.gitignore`)
- Don't share your integration token
- Rotate token immediately if compromised

## Step 5: Install Dependencies

Install the additional packages needed for Notion integration:

```bash
pip install -r requirements.txt
```

This installs:
- `notion-client` - Official Notion Python SDK
- `requests` - Instagram HTTP validation
- `python-dotenv` - Environment variable management
- `tenacity` - Retry logic with exponential backoff

### Verify Installation

```bash
python -c "import notion_client; import requests; import dotenv; import tenacity; print('✓ All dependencies installed')"
```

## Step 6: Test the Connection

Run a dry-run to verify everything is configured correctly:

```bash
python leads_to_notion.py --dry-run
```

### Expected Output (Success)

```
====================================================================
Instagram to Notion Sync
====================================================================

📂 Loaded X username(s)
🗄️  Connected to: Client Hunt
✨ Processing X new username(s)
...
[DRY RUN] Would add X account(s) to Notion
```

### Troubleshooting Connection Issues

#### Error: "Missing environment variables"
- ✓ Check `.env` file exists in project root
- ✓ Verify variable names are exactly: `NOTION_TOKEN` and `NOTION_DATABASE_ID`
- ✓ No extra spaces or quotes around values

#### Error: "Could not find database with ID"
- ✓ Database ID is correct (32 characters)
- ✓ Database is shared with your integration (Step 2)
- ✓ Integration has proper permissions (read + write)

#### Error: "Unauthorized" or "Invalid token"
- ✓ Integration token is correct and starts with `secret_`
- ✓ Token hasn't been revoked or regenerated
- ✓ Copy token again from integration settings

#### Error: "Module not found"
- ✓ Run `pip install -r requirements.txt` again
- ✓ Use correct Python environment (virtual env if applicable)

## Step 7: Run Your First Sync

Now you're ready to sync your first batch of leads!

### 1. Extract Usernames (if not already done)

```bash
python extract_usernames.py my_instagram_screenshots/
```

Output: `~/Desktop/leads/verified_usernames.md`

### 2. Sync to Notion

```bash
python leads_to_notion.py
```

### 3. Check Notion Database

Open your "Client Hunt" database in Notion to see the new entries!

## Understanding the Database Schema

The sync script populates these fields automatically:

| Field | Type | Auto-filled | Value |
|-------|------|-------------|-------|
| **Brand Name** | Title | ✅ Yes | Instagram username |
| **Social Media Account** | URL | ✅ Yes | https://instagram.com/{username} |
| **Status** | Status | ✅ Yes | "Didn't Approach" |
| **Business Type** | Multi-select | ❌ No | (Fill manually) |
| **Payment System** | Status | ❌ No | (Fill manually) |
| **Amount** | Number | ❌ No | (Fill manually) |

### Workflow Example

1. Script adds: `@nike` with status "Didn't Approach"
2. You research the brand and add Business Type: "Clothing", "Shoes"
3. You reach out → Update status to "No Reply"
4. They respond → Update status to "On Hold"
5. You agree on terms → Set Payment System: "One Time Fee", Amount: 5000
6. Project done → Update status to "Closed 🚀"

## CLI Usage Reference

### Basic Commands

```bash
# Standard workflow
python leads_to_notion.py

# Custom input file
python leads_to_notion.py --input /path/to/usernames.txt

# Preview changes (no modifications)
python leads_to_notion.py --dry-run

# Skip Instagram validation (faster)
python leads_to_notion.py --skip-validation

# Verbose output with debug info
python leads_to_notion.py --verbose
```

### Advanced Options

```bash
# Change Instagram request delay (default: 2 seconds)
python leads_to_notion.py --delay 3.0

# Only validate, don't sync to Notion
python leads_to_notion.py --skip-notion

# Skip duplicate checks (dangerous!)
python leads_to_notion.py --force-add

# Custom output directory
python leads_to_notion.py --output ./my_results
```

### Help

```bash
python leads_to_notion.py --help
```

## Output Files

After each sync, you'll find:

### 1. Validation Results (JSON)
**Location:** `validation_results/validation_results_{timestamp}.json`

Contains detailed validation data:
```json
[
  {
    "username": "nike",
    "exists": true,
    "url": "https://instagram.com/nike",
    "status_code": 200,
    "error": null
  },
  ...
]
```

### 2. Sync Report (Markdown)
**Location:** `~/Desktop/leads/notion_sync_report.md`

Human-readable summary with:
- Total statistics
- Duplicate counts
- Validation results
- Sync status
- Errors (if any)

### 3. Log Files
**Location:** `validation_results/sync_{timestamp}.log`

Debug logs for troubleshooting.

## Common Workflows

### Workflow 1: Daily Lead Extraction

```bash
# Extract new screenshots
python extract_usernames.py ~/Desktop/today_screenshots/

# Sync to Notion (duplicates automatically skipped)
python leads_to_notion.py

# Review in Notion and categorize
```

### Workflow 2: Bulk Import from List

```bash
# Create a text file with usernames (one per line)
echo "nike" > bulk_list.txt
echo "adidas" >> bulk_list.txt
echo "puma" >> bulk_list.txt

# Import to Notion
python leads_to_notion.py --input bulk_list.txt
```

### Workflow 3: Re-validate Existing List

```bash
# Validate without syncing to Notion
python leads_to_notion.py --input old_list.txt --skip-notion
```

## Rate Limits & Performance

### Instagram Validation
- **Rate**: 1 request per 2 seconds (default)
- **Speed**: ~30 usernames/minute
- **Adjustable**: Use `--delay` flag

```bash
# Faster (more aggressive, higher block risk)
python leads_to_notion.py --delay 1.0

# Slower (safer)
python leads_to_notion.py --delay 3.0
```

### Notion API
- **Rate**: 3 requests/second (automatically enforced)
- **Batch size**: 100 pages per query
- **No manual adjustment needed**

### Processing Time Estimates

| Usernames | Validation Time | Total Time |
|-----------|----------------|------------|
| 10 | ~20 seconds | ~25 seconds |
| 50 | ~2 minutes | ~2.5 minutes |
| 100 | ~4 minutes | ~5 minutes |
| 500 | ~17 minutes | ~18 minutes |

## Security Best Practices

1. ✅ **Never share integration tokens**
   - Tokens give full access to your Notion workspace
   - Treat like passwords

2. ✅ **Don't commit `.env` to Git**
   - Already in `.gitignore`
   - Double-check before pushing

3. ✅ **Use minimal permissions**
   - Integration only needs: Read, Update, Insert
   - Not: Delete, Admin

4. ✅ **Rotate tokens if compromised**
   - Regenerate in integration settings
   - Update `.env` file

5. ✅ **Review Notion audit log**
   - Settings → Workspace → Security & Identity → Audit Log
   - Check for unexpected changes

6. ✅ **Limit integration scope**
   - Only share databases that need access
   - Don't share entire workspace

## Troubleshooting

### Validation Issues

**Problem:** All accounts marked as invalid
- Check internet connection
- Try with known valid username: `python leads_to_notion.py --input <(echo "instagram")`
- Instagram might be rate-limiting, increase `--delay`

**Problem:** Validation very slow
- Decrease delay (but risk blocks): `--delay 1.5`
- Or use `--skip-validation` if you trust extraction

### Notion Sync Issues

**Problem:** Nothing added to Notion
- Check all accounts aren't duplicates
- Verify database permissions
- Check logs in `validation_results/`

**Problem:** Some entries failed to add
- Check `notion_sync_report.md` for error details
- Verify database schema matches expected format
- Check Notion service status: status.notion.so

### Permission Issues

**Problem:** "Integration not found in workspace"
- Re-share database with integration (Step 2)
- Verify integration still exists in settings

**Problem:** "Property X does not exist"
- Database schema changed
- Verify "Brand Name", "Social Media Account", "Status" fields exist
- Check spelling and capitalization

## Getting Help

1. **Check logs:** `validation_results/sync_{timestamp}.log`
2. **Run with verbose:** `python leads_to_notion.py --verbose`
3. **Test connection:** `python leads_to_notion.py --dry-run`
4. **GitHub Issues:** [beyourahi/extract_usernames/issues](https://github.com/beyourahi/extract_usernames/issues)

## FAQ

**Q: Can I sync the same list multiple times?**  
A: Yes! Duplicate detection prevents re-adding existing entries.

**Q: What if Instagram blocks me?**  
A: Increase delay: `--delay 3.0` or use `--skip-validation`

**Q: Can I undo a sync?**  
A: No automated undo. Manually delete entries in Notion if needed.

**Q: Does this work with private accounts?**  
A: No. Private accounts show as "invalid" (requires login).

**Q: Can I add custom fields during sync?**  
A: No. Only Brand Name, URL, and Status are auto-filled. Add others manually.

**Q: How do I update existing entries?**  
A: Script only creates new entries. Update manually in Notion.

**Q: Is my data safe?**  
A: Yes! Everything runs locally. No data sent to third parties.

---

**Setup Complete! 🎉**

You're now ready to automate your Instagram lead workflow. Happy client hunting!
