Hello thank you for checking my profile 😎 

## EUGLOH Course Events Scraper

This repository includes an automated tool that monitors [EUGLOH course registrations](https://www.eugloh.eu/courses-trainings/?openRegistrations=%5Byes%5D), detects new opportunities, and publishes them to an RSS feed.

### Features

- 🔍 Automatically scrapes EUGLOH course pages for new registration opportunities
- 📰 Generates RSS 2.0 feed (`feed.xml`) with newest events first
- 🔔 Optional webhook notifications for new events
- 🔄 Runs automatically every hour via GitHub Actions
- 🎯 Fully configurable CSS selectors for different page structures
- 💾 Deduplicates events using persistent state file

### Setup

#### Local Testing

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the scraper:**
   ```bash
   python check_events.py
   ```
   
   This will:
   - Fetch the target URL and scrape for registration links
   - Extract event titles and dates
   - Create/update `seen.json` (state file) and `feed.xml` (RSS feed)
   - Print new events to console

3. **Test with custom selectors:**
   ```bash
   TITLE_SELECTOR="h3.title" DATE_SELECTOR=".event-date" python check_events.py
   ```

#### GitHub Actions Setup

The workflow runs automatically every hour. To configure:

1. **Enable GitHub Actions** in your repository settings

2. **Configure secrets** (optional, in Settings → Secrets and variables → Actions):
   - `WEBHOOK_URL` - POST endpoint for new event notifications (JSON payload)
   - `TARGET_URL` - Override the default scraping URL
   - `REG_LINK_SELECTOR` - Custom CSS selector for registration links
   - `TITLE_SELECTOR` - Custom CSS selector for event titles
   - `DATE_SELECTOR` - Custom CSS selector for event dates

3. **Commit the workflow file** (already included at `.github/workflows/check-events.yml`)

4. The workflow will automatically commit changes to `seen.json` and `feed.xml`

#### GitHub Pages (RSS Hosting)

To make your RSS feed publicly accessible:

1. Go to **Settings → Pages**
2. Under "Source", select **Deploy from a branch**
3. Choose **main** branch and **/ (root)** folder
4. Click **Save**

Your RSS feed will be available at: `https://[username].github.io/[repository]/feed.xml`

### Configuration

All settings can be customized via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_URL` | EUGLOH open registrations page | URL to scrape |
| `REG_LINK_SELECTOR` | `div.buttons-wrap:nth-child(3) > div:nth-child(1) > p:nth-child(1) > a:nth-child(1)` | CSS selector for registration links |
| `TITLE_SELECTOR` | `h5.headline` | CSS selector for event titles (searches ancestors) |
| `DATE_SELECTOR` | `time, .date` | CSS selector for event dates (searches ancestors) |
| `STATE_FILE` | `seen.json` | File to store seen event IDs |
| `FEED_FILE` | `feed.xml` | RSS feed output file |
| `WEBHOOK_URL` | _(not set)_ | HTTP endpoint for new event notifications |
| `USER_AGENT` | `Mozilla/5.0 (compatible; EUGLOH-Events-Bot/1.0)` | User agent for HTTP requests |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds |

### Customizing Selectors

If event extraction fails or you want to scrape a different website:

1. **Find the right CSS selectors** using browser DevTools:
   - Right-click on the element → Inspect
   - Right-click in DevTools → Copy → Copy selector

2. **Test locally** with custom selectors:
   ```bash
   TARGET_URL="https://example.com/events" \
   REG_LINK_SELECTOR="a.register-button" \
   TITLE_SELECTOR="h2.event-title" \
   DATE_SELECTOR=".event-date" \
   python check_events.py
   ```

3. **Update GitHub secrets** to use in automated runs

**Note:** The script searches ancestor elements for title and date, so selectors don't need to be exact siblings of the registration link.

### Delivery Options

#### RSS Feed

Subscribe to `feed.xml` in any RSS reader:
- If hosted via GitHub Pages: `https://[username].github.io/[repository]/feed.xml`
- Alternatively, use a service like [RSS-Bridge](https://github.com/RSS-Bridge/rss-bridge) to serve it

#### Webhook

Set `WEBHOOK_URL` to receive HTTP POST requests with JSON payload:
```json
{
  "title": "Event Title",
  "link": "https://example.com/register",
  "date": "2024-01-15",
  "timestamp": "2024-01-10T12:00:00Z"
}
```

#### Email (via external service)

Use a webhook-to-email service like:
- [Zapier](https://zapier.com)
- [IFTTT](https://ifttt.com)
- [Pipedream](https://pipedream.com)

Or configure your own SMTP relay that accepts webhook calls.

### Troubleshooting

**No events found:**
- Verify the `TARGET_URL` is accessible
- Check if CSS selectors match the current page structure (use browser DevTools)
- Run locally with debug: `python check_events.py` to see console output

**Title/date extraction fails:**
- The script searches ancestor elements, but you may need to adjust selectors
- Edit `TITLE_SELECTOR` or `DATE_SELECTOR` environment variables
- See inline comments in `check_events.py` marked with `CUSTOMIZE THIS`

**Workflow not committing:**
- Ensure the workflow has `contents: write` permission
- Check Actions logs for error messages
- Verify `seen.json` or `feed.xml` actually changed

### Files

- `check_events.py` - Main scraper script
- `requirements.txt` - Python dependencies
- `.github/workflows/check-events.yml` - Automated hourly checks
- `seen.json` - State file tracking seen events (auto-generated)
- `feed.xml` - RSS 2.0 feed (auto-generated)

---

<!---
chrisilt/chrisilt is a ✨ special ✨ repository because its `README.md` (this file) appears on your GitHub profile.
You can click the Preview link to take a look at your changes.
--->
