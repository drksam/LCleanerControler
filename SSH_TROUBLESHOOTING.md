# SSH Deployment Troubleshooting Guide

## ⚠️ Note: Manual File Copy is Now Recommended

The LCleaner Controller now uses **manual file copying** as the primary deployment method. This guide is for users who still prefer SSH-based deployment.

**For the recommended manual deployment, see `DEPLOYMENT_GUIDE.md` in the pi-deployment folder.**

## 🔧 SSH Setup Requirements

If you want to use SSH deployment, you need to configure your Raspberry Pi first:

### 1. Enable SSH Service
```bash
# On the Pi (physical access required initially):
sudo systemctl enable ssh
sudo systemctl start ssh
```

### 2. Configure SSH Authentication
```bash
# Edit SSH configuration
sudo nano /etc/ssh/sshd_config

# Ensure these settings:
PasswordAuthentication yes
ChallengeResponseAuthentication yes
UsePAM yes
PubkeyAuthentication yes

# Restart SSH service
sudo systemctl restart ssh
```

### 3. Check Username
Newer Raspberry Pi OS doesn't create a default 'pi' user:
```bash
# Check your actual username
whoami

# Common usernames:
# pi        (older Pi OS)
# your-name (newer Pi OS with custom user)
```

### 4. Test SSH Connection
```bash
# Test from your development machine
ssh your-username@your-pi-ip

# Example:
ssh pi@192.168.1.100
ssh myuser@10.4.2.33
```

## 🐛 Common SSH Issues

### "Permission denied (publickey,password)"
1. **Check password authentication**:
   ```bash
   sudo grep "PasswordAuthentication" /etc/ssh/sshd_config
   # Should show: PasswordAuthentication yes
   ```

2. **Check if user exists**:
   ```bash
   # On the Pi:
   cat /etc/passwd | grep your-username
   ```

3. **Reset user password**:
   ```bash
   # On the Pi:
   sudo passwd your-username
   ```

### "Host key verification failed"
```bash
# Remove old host key and try again
ssh-keygen -R your-pi-ip
```

### "Connection refused" or "No route to host"
1. **Check Pi IP address**:
   ```bash
   # On the Pi:
   ip addr show
   ```

2. **Check SSH service status**:
   ```bash
   # On the Pi:
   sudo systemctl status ssh
   ```

3. **Check firewall**:
   ```bash
   # On the Pi:
   sudo ufw status
   ```

## 🔧 SSH Deployment Scripts (Legacy)

If SSH is working, you can use the legacy deployment scripts:

### Windows PowerShell
```powershell
# Update the target in deploy_to_pi.ps1
.\deploy\deploy_to_pi.ps1 your-username@your-pi-ip
```

### Linux/macOS Bash
```bash
# Update the target in deploy_to_pi.sh
./deploy/deploy_to_pi.sh your-username@your-pi-ip
```

## 🚀 Recommended: Manual Deployment Instead

**Why switch to manual deployment:**
- ✅ No SSH configuration required
- ✅ Works in any network environment
- ✅ More reliable and flexible
- ✅ Choose your preferred transfer method
- ✅ Eliminates permission issues

**Manual deployment steps:**
1. Run `prepare_deployment.bat` on Windows
2. Copy `pi-deployment\LCleanerController\` folder to Pi (USB, network, etc.)
3. On Pi: `cd ~/LCleanerController && ./quick_start.sh`

See `DEPLOYMENT_GUIDE.md` for complete manual deployment instructions.

## 📞 Still Having SSH Issues?

If SSH continues to be problematic:

1. **Use manual deployment** (recommended)
2. **Check Pi documentation** for your specific OS version
3. **Use physical access** to configure SSH properly
4. **Consider using VNC** instead of SSH for remote access

---

**Recommendation**: Use the manual file copy deployment method for better reliability and compatibility.
