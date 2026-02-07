# Smart Deduplication for Notion Database

## Overview

The smart deduplication feature automatically finds and merges duplicate entries in your Notion database based on Instagram URLs. When duplicates are found (e.g., same URL with different usernames like "coolbrand" and "1."), it intelligently picks the best username and archives the duplicates.

## How It Works

### 1. Duplicate Detection
The deduplicator scans your entire Notion database and groups entries by their Instagram URL. Any URL that appears more than once is considered a duplicate group.

### 2. Smart Username Scoring
For each duplicate group, all usernames are scored based on quality:

**Scoring Criteria:**
- ❌ **Heavy penalty** for malformed usernames like "1.", "2.", "123"
- ❌ **Penalty** for starting with numbers
- ✅ **Reward** for starting with letters
- ✅ **Reward** for having mostly alphabetic characters
- ✅ **Reward** for reasonable length (3-30 characters)
- ✅ **Small reward** for lowercase (Instagram standard)

**Example Scoring:**
```
Username "1."         → Score: -1000 (malformed)
Username "123brand"   → Score:  45 (starts with number)
Username "coolbrand"  → Score: 215 (perfect!)
```

### 3. Merge Process
- The username with the **highest score** is kept
- All other duplicates are **archived** (moved to trash, not permanently deleted)
- You can restore archived entries from Notion's trash if needed

## Usage

### Automatic Deduplication (Default)
By default, deduplication runs automatically after Notion sync:

```bash
extract-usernames --notion-sync
```

This will:
1. ✅ Extract usernames from screenshots
2. ✅ Sync to Notion
3. ✅ Auto-deduplicate duplicate entries

### Skip Deduplication
```bash
extract-usernames --notion-sync --no-deduplicate
```

### Preview Without Removing (Dry Run)
To see what would be merged without actually removing anything:

```bash
extract-usernames --notion-sync --dry-run-dedup
```

This shows:
- Which duplicates were found
- Which usernames would be kept
- Which usernames would be removed
- The scores for each username

## Example Output

### Duplicate Group Found
```
🔍 Scanning database for duplicates...

📍 Found 3 duplicates for: https://instagram.com/coolbrand
   ✅ Keeping: 'coolbrand' (score: 215)
   🗑️  Removed: '1.' (score: -1000)
   🗑️  Removed: 'cool' (score: 105)

📍 Found 2 duplicates for: https://instagram.com/awesomeshop  
   ✅ Keeping: 'awesomeshop' (score: 248)
   🗑️  Removed: '2.' (score: -1000)

✅ Deduplication Complete:
   Duplicate groups: 2
   Duplicates removed: 3
```

### Dry Run Output
```
🔍 Scanning database for duplicates...

📍 Found 2 duplicates for: https://instagram.com/coolbrand
   ✅ Keeping: 'coolbrand' (score: 215)
   🗑️  Would remove: '1.' (score: -1000)

📊 Deduplication Preview (Dry Run):
   Duplicate groups found: 1
   Total duplicates: 1
   💡 Run without --dry-run-dedup to remove duplicates
```

## When to Use

### You Should Use Deduplication When:
- ✅ You have duplicate entries with different usernames
- ✅ Some usernames are malformed ("1.", "2.", etc.)
- ✅ You want to clean up your database after bulk imports
- ✅ You accidentally synced the same data multiple times

### You Don't Need It When:
- ❌ Your database has no duplicates
- ❌ You want to keep multiple entries for the same URL intentionally
- ❌ All usernames are already correct

## Safety Features

### Soft Delete
Entries are **archived**, not permanently deleted. You can restore them from Notion's trash:
1. Open Notion
2. Click "Trash" in sidebar
3. Find the archived pages
4. Click "Restore"

### Dry Run Mode
Always test with `--dry-run-dedup` first to preview changes:
```bash
extract-usernames --notion-sync --dry-run-dedup
```

### Smart Scoring
The scoring algorithm is conservative:
- It heavily penalizes obviously wrong entries ("1.", "2.")
- It rewards proper Instagram usernames
- It keeps the most complete/correct username

## Troubleshooting

### "No duplicates found"
✅ This is good! Your database is clean.

### "Failed to archive page"
- Check your Notion integration has write permissions
- Ensure the page hasn't been deleted already
- Verify your Notion token is valid

### "Wrong username was kept"
If the scoring picked the wrong username:
1. Restore the archived entry from trash
2. Manually update the username in Notion
3. Delete the unwanted entry
4. Report the issue so we can improve the scoring algorithm!

## Configuration

The deduplication feature requires:
- ✅ Notion integration configured
- ✅ Database ID set
- ✅ Data source ID (auto-detected)
- ✅ Property names (auto-detected)

No additional configuration needed!

## API Reference

### Python API
```python
from extract_usernames.integrations.notion_deduplicator import run_deduplication

stats = run_deduplication(
    token="your_notion_token",
    database_id="your_database_id",
    data_source_id="your_data_source_id",
    property_names={
        'title': 'Brand Name',
        'url': 'Social Media Account'
    },
    dry_run=True  # Preview only
)

print(f"Duplicates found: {stats['duplicates_found']}")
print(f"Duplicates removed: {stats['duplicates_removed']}")
```

### Return Statistics
```python
{
    'total_entries': 0,
    'duplicate_groups': 2,
    'duplicates_found': 3,
    'duplicates_removed': 3,
    'errors': 0
}
```

## Technical Details

### Rate Limiting
- Enforces 350ms delay between API calls
- Prevents hitting Notion's rate limits
- Safe for large databases

### Batch Processing
- Queries database in pages of 100 entries
- Handles databases of any size
- Efficient memory usage

### Property Detection
- Auto-detects title and URL property names
- Works with custom property names
- Handles multi-source databases

## Related

- [Notion Integration Setup](./NOTION_SETUP.md)
- [CLI Reference](./CLI_REFERENCE.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
