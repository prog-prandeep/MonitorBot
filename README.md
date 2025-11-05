# Instagram Monitor Bot - Updated with Session Management & Ban Monitoring

A modular Discord bot for monitoring Instagram account recoveries AND bans with session-based authentication.

## 🆕 New Features

### ✨ Session Management
- **Multiple sessions**: Store 5-6 Instagram sessions in `session.json`
- **Sticky sessions**: Use same session until error (400/401/429)
- **Auto-rotation**: Switch to next session on error
- **Fallback session**: Hardcoded backup when all sessions fail
- **Admin controls**: Add/remove sessions via Discord commands

### 🚫 Ban Monitoring
- **New !ban command**: Monitor accounts for bans
- **Separate tracking**: `ban_monitor.json` for ban monitoring
- **Ban detection logic**: 
  - Status 200/404 AND username mismatch = BANNED
  - Notifies with red embed (no screenshot)
- **Independent from unban**: Both can run simultaneously

## 📁 Updated Structure

```
instagram-monitor-bot/
├── shared/
│   ├── config_manager.py
│   ├── data_manager.py             # Unban monitoring data
│   ├── ban_data_manager.py         # ⭐ NEW: Ban monitoring data
│   ├── session_manager.py          # ⭐ NEW: Session rotation
│   ├── instagram_api.py            # ⭐ UPDATED: Uses sessions
│   ├── screenshot_generator.py
│   ├── monitor_service.py          # Unban monitoring
│   ├── ban_monitor_service.py      # ⭐ NEW: Ban monitoring
│   ├── command_handler.py          # ⭐ UPDATED: New commands
│   └── utils.py
│
├── client1/
│   ├── main.py
│   ├── config.json
│   ├── session.json                # ⭐ NEW: Session storage
│   ├── monitoring.json              # Unban monitoring
│   ├── ban_monitor.json            # ⭐ NEW: Ban monitoring
│   └── bot.log
│
└── ... (other clients)
```

## 🔑 Session Setup

### 1. Create `session.json` in each client folder:

```json
{
  "sessions": [
    "12345678%3A1a2b3c4d%3A28%3AAYc1d2e3f4g5h6",
    "87654321%3A9z8y7x6w%3A28%3AAYi9j8k7l6m5n4",
    "11223344%3A5t6u7v8w%3A28%3AAYo3p2q1r0s9t8",
    "99887766%3A1m2n3o4p%3A28%3AAYu7v6w5x4y3z2",
    "55667788%3A9a8b7c6d%3A28%3AAYe5f4g3h2i1j0"
  ]
}
```

### 2. Get Instagram Session ID:

1. Login to Instagram in browser
2. Open DevTools (F12) → Application → Cookies
3. Find `sessionid` cookie
4. Copy the value (looks like: `12345678%3A1a2b3c4d%3A28%3AAYc...`)

### 3. Update Fallback Session:

Edit `session_manager.py`:
```python
FALLBACK_SESSION = "your_real_fallback_sessionid_here"
```

## 📝 New Commands

### **Ban Monitoring Commands**
```
!ban <username>              - Start monitoring for bans
!ban <user1> <user2>         - Monitor multiple accounts
!clearban <username>         - Stop monitoring specific account
!clearban <user1> <user2>    - Stop monitoring multiple
!clearban all                - Stop ALL ban monitoring
```

### **Unban Monitoring Commands** (Renamed)
```
!unban <username>            - Monitor for recovery (unchanged)
!unban <user1> <user2>       - Monitor multiple
!clearunban <username>       - Stop monitoring specific
!clearunban <user1> <user2>  - Stop multiple
!clearunban all              - Stop ALL unban monitoring
```

### **Session Management** (Admin Only)
```
!ads <sessionid>             - Add new session
!rms                         - Show sessions list
!rms <sessionid>             - Remove session
```

### **Other Commands**
```
!list                        - Show all monitored accounts (both types)
!status                      - Show bot status (includes session count)
!test <username>             - Test session & API
!ping                        - Check bot online
!help                        - Show help
```

## 🎯 How It Works

### **Session Rotation**
1. Bot uses **first session** from `session.json`
2. If request gets **400, 401, or 429** → rotate to next session
3. After trying all sessions → use **hardcoded fallback**
4. Session stays active until error (sticky)

### **Ban Detection Logic**
```python
# Account is BANNED if:
1. Status code is 404 (account not found)
   OR
2. Status code is 200 AND response username ≠ requested username
```

### **Unban Detection Logic** (Unchanged)
```python
# Account is UNBANNED if:
Status code is 200 AND response username = requested username
```

## 🚀 Running the Bot

### For Single Client:
```bash
cd client1
python main.py
```

### For Multiple Clients:
```bash
# Terminal 1
cd client1 && python main.py

# Terminal 2
cd client2 && python main.py

# ... etc
```

## 📊 Example Workflow

### Monitor for Ban:
```
User: !ban celebrity_username
Bot: ✅ Ban Monitoring Started
     🔍 Now monitoring @celebrity_username for bans

[Bot checks every 3-7 minutes...]

[When banned detected:]
Bot: 🚫 Account Banned Detected!
     Monitored Username: @celebrity_username
     ⚠️ Username Changed To: @celebrity_backup
     Status: Username changed (likely banned & recreated)
     📊 Stats: Followers: 1.2M | Following: 150 | Posts: 450
     ⏱️ Detection Time: 2h 15m 30s
```

### Monitor for Unban:
```
User: !unban suspended_account
Bot: ✅ Unban Monitoring Started
     🔍 Now monitoring @suspended_account

[When recovered:]
Bot: Account Recovered | @suspended_account 🏆✅
     Followers: 50,000 | Following: 300
     ⏱️ Time Taken: 1 hour 30 minutes 45 seconds
     [Screenshot of profile]
```

## 🔧 Admin Session Management

### Add Session:
```
Admin: !ads 12345678%3A1a2b3c4d%3A28%3AAYc1d2e3f4g5h6
Bot: ✅ Session Added
     Session added successfully!
     Total sessions: 6
```

### Remove Session:
```
Admin: !rms
Bot: 📋 Current Sessions
     1. 12345678%3A1a...g5h6
     2. 87654321%3A9z...m5n4
     3. 11223344%3A5t...s9t8
     
Admin: !rms 12345678%3A1a2b3c4d%3A28%3AAYc1d2e3f4g5h6
Bot: ✅ Session Removed
     Session removed successfully!
     Remaining sessions: 5
```

## 🛠️ Modified Files Summary

### **New Files:**
1. `session_manager.py` - Session rotation logic
2. `ban_data_manager.py` - Ban monitoring data storage
3. `ban_monitor_service.py` - Ban detection logic
4. `session.json` - Session storage

### **Updated Files:**
1. `instagram_api.py` - Now uses sessions instead of proxy-only
2. `command_handler.py` - Added ban commands & session commands
3. `main.py` - Integrated new services

### **Unchanged Files:**
- `config_manager.py`
- `data_manager.py` (for unban)
- `screenshot_generator.py`
- `monitor_service.py` (for unban)
- `utils.py`

## ⚠️ Important Notes

1. **Sessions expire**: Instagram sessions last ~90 days, rotate regularly
2. **Don't share sessions**: Each client should have unique sessions
3. **Fallback is critical**: Always set a valid fallback session
4. **Both monitoring types**: You can monitor same account for BOTH ban & unban
5. **Session rotation**: Happens automatically on errors, no manual intervention

## 🔐 Security

- Never commit `session.json` to Git
- Add to `.gitignore`:
  ```
  session.json
  ban_monitor.json
  ```
- Rotate sessions monthly
- Use different sessions per client

## 📈 Performance

- **5-6 sessions per client**: Reduces rate limiting
- **Sticky sessions**: Minimizes session switches
- **Independent monitoring**: Ban & unban don't interfere
- **Same check intervals**: Configurable 3-7 minutes

## 🎉 That's It!

Your bot now has:
- ✅ Session-based authentication with rotation
- ✅ Automatic error handling & session switching
- ✅ Ban monitoring with separate tracking
- ✅ Unban monitoring (existing feature)
- ✅ Admin session management commands
- ✅ Fallback session for reliability