---
name: feishu-gateway
description: Configure and troubleshoot Feishu (Lark) gateway integration for Hermes Agent. Covers App ID/Secret setup, error code 1000040345 resolution, user pairing, and common connection issues.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [feishu, lark, gateway, messaging, troubleshooting, 飞书]
    related_skills: [hermes-agent]
---

# Feishu (Lark) Gateway Configuration

Complete guide for integrating Hermes Agent with Feishu (飞书/Lark) messaging platform.

## Prerequisites

1. A Feishu/Lark account
2. Access to [Feishu Open Platform](https://open.feishu.cn/)
3. A created custom app with bot capability enabled

## Setup Steps

### 1. Create Feishu App

1. Go to [Feishu Open Platform](https://open.feishu.cn/app)
2. Click "Create App" → "Custom App"
3. Fill in app name and description
4. Enable "Bot" capability in app features

### 2. Get Credentials

In your app settings, go to **"Credentials & Basic Info"**:

```
App ID:     cli_xxxxxxxxxxxxxxxx       (e.g., cli_a9562cb27bb95ccb)
App Secret: cli_xxxxxxxxxxxxxxxxxxxx   (starts with cli_, ~36 chars)
```

**Important**: App Secret must start with `cli_`. If you see a different format (like `JoXYFjFZMsj...`), it might be:
- Verification Token (not App Secret)
- Encrypt Key
- Wrong credential type

### 3. Configure Hermes

Add to `~/.hermes/.env`:

```bash
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=cli_xxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_DOMAIN=feishu              # or "lark" for international version
FEISHU_CONNECTION_MODE=websocket  # or "webhook"
FEISHU_ALLOW_ALL_USERS=false      # set true to allow all users
FEISHU_ALLOWED_USERS=             # comma-separated user IDs if not allowing all
FEISHU_GROUP_POLICY=open          # "open", "closed", or "approval"
```

### 4. Start Gateway

```bash
hermes gateway run        # Foreground mode (for testing)
hermes gateway start      # Background service mode
```

## Troubleshooting

### Using OpenClaw Feishu Plugin Diagnostics

If you're using the OpenClaw Feishu plugin, run these diagnostic commands:

```bash
# Check plugin installation and basic connectivity
npx @larksuite/openclaw-lark info

# Detailed configuration check
npx @larksuite/openclaw-lark info --all

# Run full diagnostic
npx @larksuite/openclaw-lark doctor
```

### Error: Gateway shows "connected" but messages don't send

**Symptoms**: `hermes gateway status` shows feishu as `connected`, but attempting to send messages fails or messages never arrive.

**Root Cause**: The `lark_oapi` Python package is not installed in the Hermes virtual environment. The gateway status only checks the connection state file, not whether the required dependencies are present.

**Verification**:
```bash
# Check if lark_oapi is installed
cd ~/.hermes/hermes-agent
source venv/bin/activate
pip list | grep lark

# If empty, the package is missing
```

**Solution**:
```bash
cd ~/.hermes/hermes-agent
source venv/bin/activate
pip install lark-oapi aiohttp websockets
hermes gateway restart
```

**Also check for**:
- `aiohttp` - required for webhook mode
- `websockets` - required for websocket mode

### Error 1000040345: app_id or app_secret is invalid

**Symptoms**: Gateway logs show:
```
ERROR Lark: connect failed, err: 1000040345: app_id or app_secret is invalid
```

**Causes & Solutions**:

1. **Wrong Secret Format**
   - Check: Secret should start with `cli_`
   - Fix: Go to Credentials page and copy the correct "App Secret"

2. **Truncated Secret in .env**
   - Check: `grep FEISHU_APP_SECRET ~/.hermes/.env`
   - Fix: Ensure full secret is present, not truncated with `...`

3. **App Not Published**
   - Check: App status in Feishu console
   - Fix: Either publish the app OR enable test mode and add test users

4. **Wrong Domain**
   - Check: `FEISHU_DOMAIN` setting
   - Fix: Use `feishu` for China version, `lark` for international

### Error 200340: Card Callback Not Configured

**Symptoms**: User clicks a button on a Feishu interactive card (e.g., "Allow Once" for command approval) and sees:
```
出错了，请稍后重试 code: 200340
```

**Root Cause**: 
The Feishu app is not configured with a card callback URL, or the configured URL is invalid. When users click interactive card buttons, Feishu needs to send the click event to a callback endpoint.

**Solution**:

1. **Configure Card Callback in Feishu Console**:
   - Go to [Feishu Open Platform](https://open.feishu.cn/app)
   - Select your app → "Development Configuration" → "Events & Callbacks"
   - Set **Card Callback URL** to your Hermes webhook endpoint:
     ```
     http://your-server:8644/webhook/feishu-bot
     ```
   - **Important**: Create and publish a new app version for changes to take effect

2. **Verify Webhook Configuration**:
   - Check `~/.hermes/webhook_subscriptions.json` exists and contains valid subscription
   - Ensure webhook server is accessible from the internet (Feishu servers need to reach it)

3. **Run Diagnostics** (for OpenClaw plugin users):
   ```bash
   npx @larksuite/openclaw-lark doctor
   ```

**Workaround**: If card callbacks aren't needed, avoid using interactive card formats and use plain text messages instead.

### Debugging Steps

1. **Check Gateway Logs**:
   ```bash
   grep -i "feishu\|1000040345\|lark\|200340" ~/.hermes/logs/gateway.log | tail -20
   ```

2. **Verify Credentials**:
   ```bash
   echo $FEISHU_APP_ID
   echo $FEISHU_APP_SECRET
   ```

3. **Check Configuration Files**:
   ```bash
   grep -E "FEISHU_|webhook" ~/.hermes/.env
   grep -E "feishu|webhook" ~/.hermes/config.yaml
   cat ~/.hermes/webhook_subscriptions.json
   cat ~/.hermes/gateway_state.json | grep -A2 feishu
   ```

4. **Test Connection**:
   ```bash
   hermes gateway restart
   hermes gateway status
   ```

5. **Check Gateway State**:
   ```bash
   cat ~/.hermes/gateway_state.json | grep feishu
   ```

### User Pairing

When a new user messages the bot, they need approval:

**User sees**:
```
Hi~ I don't recognize you yet!
Here's your pairing code: 2EDQ2DW8
Ask the bot owner to run:
hermes pairing approve feishu 2EDQ2DW8
```

**Owner runs**:
```bash
hermes pairing approve feishu <code>
```

**Manage Pairings**:
```bash
hermes pairing list              # List all pairings
hermes pairing list feishu       # List Feishu pairings only
hermes pairing remove feishu <user_id>  # Remove a user
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Poll timed out after 600s" | Check network connectivity to Feishu servers |
| Gateway shows connected but no messages | Check bot is added to chat/group |
| User can't message bot | Check user is in allowed list or ALLOW_ALL_USERS=true |
| Duplicate message processing | Check `feishu_seen_message_ids.json` exists |

## Webhook Mode (Alternative)

If websocket doesn't work, use webhook mode:

1. Set `FEISHU_CONNECTION_MODE=webhook`
2. Configure webhook URL in Feishu app settings
3. Point to your Hermes webhook endpoint (e.g., `https://your-server.com/webhooks/feishu`)

## File Locations

| File | Purpose |
|------|---------|
| `~/.hermes/.env` | Feishu credentials |
| `~/.hermes/config.yaml` | Hermes configuration |
| `~/.hermes/gateway_state.json` | Connection status |
| `~/.hermes/logs/gateway.log` | Debug logs |
| `~/.hermes/pairing/feishu-approved.json` | Approved users |
| `~/.hermes/pairing/feishu-pending.json` | Pending approvals |
| `~/.hermes/feishu_seen_message_ids.json` | Message deduplication |
| `~/.hermes/webhook_subscriptions.json` | Webhook subscription config |

## Quick Reference

```bash
# Setup
hermes gateway setup

# Start/Stop/Restart
hermes gateway start
hermes gateway stop
hermes gateway restart

# Check status
hermes gateway status

# View logs
tail -f ~/.hermes/logs/gateway.log

# Approve user
hermes pairing approve feishu <code>

# Update credentials
# Edit ~/.hermes/.env, then restart gateway
```
