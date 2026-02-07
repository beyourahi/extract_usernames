# Notion Integration Setup Guide

Complete guide for setting up and troubleshooting Notion integration with Instagram Username Extractor.

---

## Quick Setup (5 minutes)

### Step 1: Create a Notion Integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Give it a name (e.g., "Instagram Leads Extractor")
4. Select the workspace where your database is located
5. Click **"Submit"**
6. **Copy the "Internal Integration Token"** (starts with `secret_`)
   - Keep this secure - it's like a password!

### Step 2: Create or Prepare Your Database

#### Option A: Create New Database

1. Create a new database in Notion
2. Add these **required** properties:
   - **Brand Name** (Title) - The Instagram username
   - **Social Media Account** (URL) - Instagram profile link
   - **Status** (Status or Select) - "Didn't Approach", "Approached", etc.

#### Option B: Use Existing Database

Make sure your database has the three required properties above.

### Step 3: Share Database with Integration

**⚠️ THIS IS THE MOST COMMON MISTAKE ⚠️**

1. Open your Notion database
2. Click the **"..."** (three dots) in the top-right corner
3. Select **"Add connections"**
4. Find and select your integration (e.g., "Instagram Leads Extractor")
5. Confirm the connection

**Visual confirmation:** You should see your integration listed under "Connections" when you click the three dots.

### Step 4: Get Database ID

Your database URL looks like:
```
https://www.notion.so/workspace-name/DATABASE-ID?v=VIEW-ID
```

**The DATABASE-ID is what you need.** It's a 32-character string that looks like:
- With dashes: `300472d4-ce51-81aa-83f2-000b8ae958d2`
- Without dashes: `300472d4ce5181aa83f2000b8ae958d2`

Both formats work - the tool will clean it automatically.

### Step 5: Configure the Tool

```bash
extract-usernames --reconfigure
```

When prompted:
1. Choose **"notion"** or **"all"**
2. Enable Notion sync: **Yes**
3. Enter your integration token
4. Enter your database ID
5. Configure other options as needed

---

## Testing Your Connection

After configuration, try a test extraction:

```bash
extract-usernames --notion-sync
```

If successful, you'll see:
```
✅ Connected to Notion database: [Your Database Name]
📤 Syncing to Notion
...
✅ Notion sync complete!
```

---

## Troubleshooting

### Error: "Could not find database with ID"

**This means the integration cannot access your database.**

**Solution:**
1. ✓ **Share the database with your integration** (Step 3 above)
   - This is the #1 cause of this error
   - Open database → Three dots → Add connections
2. ✓ **Verify the database ID is correct**
   - Check the URL: `notion.so/[THIS-PART]?v=...`
   - Run `extract-usernames --show-config` to see current ID
3. ✓ **Make sure you're using the database ID, not a page ID**
   - Database URLs have `?v=` in them
   - Page URLs don't

### Error: "Unauthorized" or "Invalid token"

**Your integration token is incorrect or expired.**

**Solution:**
1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Find your integration
3. Check if it's active
4. Copy the token again (it should start with `secret_`)
5. Run `extract-usernames --reconfigure` and update the token

### Error: "Invalid property"

**Your database is missing required properties or has wrong types.**

**Solution:**
Verify your database has these exact properties:

| Property Name | Type | Notes |
|--------------|------|-------|
| Brand Name | Title | Must be the title property |
| Social Media Account | URL | Must be URL type |
| Status | Status or Select | Case-sensitive options |

If property names are different, you'll need to:
1. Rename them to match exactly, OR
2. Modify the code in `notion_manager.py`

### Connection Works But Nothing Syncs

**Check these:**

1. **Duplicates:** The tool skips usernames already in your database
   - Check if usernames are already present
   - Look in the "Brand Name" column

2. **Validation Failed:** If Instagram validation is enabled, invalid accounts are skipped
   - Try with `--no-notion-sync` to disable validation during testing

3. **Empty Input File:** Make sure `verified_usernames.md` has content
   ```bash
   cat ~/Desktop/leads/verified_usernames.md
   ```

### Rate Limiting

**Notion API has rate limits (3 requests/second).**

The tool handles this automatically, but if you see rate limit errors:
- The tool will automatically retry
- Large batches (100+) will take time
- This is normal and expected

---

## Advanced Configuration

### Skip Instagram Validation

Faster but may add invalid accounts:
```bash
extract-usernames --notion-sync
# During setup, choose: Skip Instagram validation? Yes
```

Or in config:
```json
{
  "notion": {
    "skip_validation": true
  }
}
```

### Custom Validation Delay

Adjust delay between Instagram checks (default: 2 seconds):
```json
{
  "notion": {
    "validation_delay": 3.0
  }
}
```

### Auto-Sync After Extraction

Automatically sync after each extraction:
```json
{
  "notion": {
    "auto_sync": true
  }
}
```

---

## Database ID Formats Supported

The tool automatically handles all these formats:

✅ Raw ID without dashes:
```
300472d4ce5181aa83f2000b8ae958d2
```

✅ Standard ID with dashes:
```
300472d4-ce51-81aa-83f2-000b8ae958d2
```

✅ Full URL:
```
https://notion.so/300472d4ce5181aa83f2000b8ae958d2
```

✅ URL with dashes and view:
```
https://notion.so/workspace/300472d4-ce51-81aa-83f2-000b8ae958d2?v=123
```

All formats are cleaned automatically - just paste what you have!

---

## Checking Your Configuration

View current settings:
```bash
extract-usernames --show-config
```

Output:
```
Current Configuration
============================================================
Input Directory:  /Users/you/Desktop/screenshots
Output Directory: /Users/you/Desktop/leads
VLM Mode:         Enabled
VLM Model:        glm-ocr:bf16
Diagnostics:      Disabled

Notion Integration: Enabled
  Token:          secret_xxx...
  Database ID:    300472d4...
  Auto-sync:      Yes
  Validation:     Enabled
============================================================
```

---

## Security Best Practices

1. **Never share your integration token**
   - It's stored locally in `~/.config/extract-usernames/config.json`
   - Don't commit it to git
   - Don't share screenshots with the token visible

2. **Limit integration capabilities**
   - In Notion settings, only grant necessary permissions
   - Integration only needs access to the specific database

3. **Rotate tokens regularly**
   - If compromised, create a new integration
   - Update configuration with new token

---

## Common Questions

### Q: Can I use multiple databases?
**A:** Currently, one database per configuration. To switch:
```bash
extract-usernames --reconfigure
```

### Q: Can I customize property names?
**A:** Yes, but requires code modification in `notion_manager.py`. Look for the `create_page()` method.

### Q: Does this work with Notion free plan?
**A:** Yes! Integrations work on all Notion plans.

### Q: How do I disable Notion sync?
**A:** Either:
- Use `--no-notion-sync` flag
- Run `extract-usernames --reconfigure` and disable it

### Q: Where are my credentials stored?
**A:** In `~/.config/extract-usernames/config.json`

To view location:
```bash
extract-usernames --show-config
```

---

## Getting Help

If you're still having issues:

1. **Run diagnostics:**
   ```bash
   extract-usernames --diagnostics --notion-sync
   ```

2. **Check the error message** - it now includes step-by-step fixes

3. **Verify all three components:**
   - ✅ Integration created and token copied
   - ✅ Database shared with integration
   - ✅ Database ID is correct

4. **Open an issue:**
   - Visit: https://github.com/beyourahi/extract_usernames/issues
   - Include the error message (remove sensitive tokens first!)

---

## Quick Reference

```bash
# View current config
extract-usernames --show-config

# Reconfigure Notion settings
extract-usernames --reconfigure

# Force sync to Notion
extract-usernames --notion-sync

# Skip Notion sync
extract-usernames --no-notion-sync

# Reset everything
extract-usernames --reset-config
```

---

**Last Updated:** February 2026  
**Questions?** Open an issue on GitHub or check the main README.
