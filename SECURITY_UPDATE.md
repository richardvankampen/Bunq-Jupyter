# 🔒 BEVEILIGDE VERSIE - Bunq Dashboard

## ⚠️ BELANGRIJKE WIJZIGINGEN

Deze versie bevat **kritieke beveiligingsverbeteringen** voor veilig gebruik op je Synology NAS.

---

## 🛡️ Beveiligingsverbeteringen

### ✅ 1. Basic Authentication
- **Alle API endpoints** vereisen nu username/password
- Constant-time vergelijking voorkomt timing attacks
- Configureerbaar via `.env` bestand

### ✅ 2. CORS Beperking
- Default CORS policy **uitgeschakeld** (`*` is verwijderd)
- Alleen toegestane origins kunnen API aanroepen
- Configureer je NAS IP-adres in `.env`

### ✅ 3. Rate Limiting
- **30 requests per minuut** per IP-adres
- Voorkomt brute-force aanvallen
- In-memory tracking (reset bij container restart)

### ✅ 4. Debug Mode Uitgeschakeld
- `debug=False` in productie
- Geen internal stack traces zichtbaar
- Beperkte error informatie naar client

### ✅ 5. Geen Credential Logging
- API keys worden **nooit** gelogd (ook geen fragments)
- Alleen succes/failure status in logs
- Beschermt tegen log file leakage

---

## 📁 Bestanden Overzicht

### Nieuwe/Gewijzigde Bestanden:

1. **`api_proxy_secure.py`** - Beveiligde Flask API
   - Basic Authentication decorator
   - Rate limiter class
   - Geen debug mode
   - Geen API key logging

2. **`app_secure.js`** - Frontend met authentication
   - Basic Auth headers in fetch requests
   - Credentials opslag in localStorage
   - Settings UI voor API credentials
   - Fallback naar demo data bij auth failure

3. **`.env.example`** - Complete configuratie template
   - Alle security settings
   - Duidelijke comments
   - Synology-specifieke voorbeelden

---

## 🚀 INSTALLATIE INSTRUCTIES

### Stap 1: Vervang Bestanden

```bash
cd /volume1/docker/bunq-dashboard

# Backup originele bestanden
mv api_proxy.py api_proxy.py.backup
mv app.js app.js.backup

# Kopieer nieuwe beveiligde versies
cp api_proxy_secure.py api_proxy.py
cp app_secure.js app.js
cp .env.example .env
```

### Stap 2: Configureer .env

Open `.env` en configureer de volgende **verplichte** settings:

```bash
# 1. BASIC AUTHENTICATION (VERPLICHT!)
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=KiesEenSterkWachtwoord123!

# 2. CORS ORIGINS (Vervang met je NAS IP!)
ALLOWED_ORIGINS=http://192.168.1.100:8000

# 3. Vaultwarden Credentials (indien gebruikt)
VAULTWARDEN_CLIENT_ID=user.xxxx-xxxx-xxxx
VAULTWARDEN_CLIENT_SECRET=jouw_secret_hier

# 4. Bunq Environment
BUNQ_ENVIRONMENT=PRODUCTION
USE_VAULTWARDEN=true
```

**⚠️ KRITIEK:** Stel een **sterk wachtwoord** in voor `BASIC_AUTH_PASSWORD`!

### Stap 3: Update HTML (optioneel maar aanbevolen)

Voeg credential inputs toe aan je settings modal in `index.html`:

```html
<div class="setting-group">
    <label for="apiUsername">API Username:</label>
    <input type="text" id="apiUsername" value="admin">
</div>

<div class="setting-group">
    <label for="apiPassword">API Password:</label>
    <input type="password" id="apiPassword" placeholder="Voer API wachtwoord in">
</div>

<div class="setting-group">
    <label>
        <input type="checkbox" id="useRealData">
        Gebruik echte Bunq data (vereist credentials)
    </label>
</div>
```

### Stap 4: Rebuild Container

```bash
cd /volume1/docker/bunq-dashboard

# Stop huidige container
sudo docker-compose down

# Rebuild met nieuwe code
sudo docker-compose build --no-cache

# Start met nieuwe configuratie
sudo docker-compose up -d

# Check logs
sudo docker-compose logs -f
```

Je zou moeten zien:
```
🔐 Authentication: ENABLED ✅
🔒 CORS Origins: ['http://192.168.1.100:8000']
⏱️  Rate Limiting: 30 requests/minute per IP
```

### Stap 5: Test Authentication

1. Open dashboard: `http://192.168.1.100:8000`
2. Klik op ⚙️ Settings
3. Vul in:
   - API Username: `admin`
   - API Password: `[jouw wachtwoord uit .env]`
4. Enable "Gebruik echte Bunq data"
5. Save Settings
6. Klik Refresh

Als alles goed is:
- ✅ Browser vraagt om login (bij eerste keer)
- ✅ Data wordt geladen van echte API
- ✅ Logs tonen successful authentication

Als er problemen zijn:
- ❌ 401 Unauthorized → Check wachtwoord
- ❌ 429 Rate Limit → Wacht 1 minuut
- ❌ CORS error → Check ALLOWED_ORIGINS in .env

---

## 🔍 SECURITY CHECKLIST

Controleer de volgende punten:

### ✅ Container
- [ ] `BASIC_AUTH_PASSWORD` is ingesteld in `.env`
- [ ] `ALLOWED_ORIGINS` bevat alleen jouw NAS IP/domein
- [ ] `FLASK_DEBUG=false` in `.env`
- [ ] `USE_VAULTWARDEN=true` (API key niet in .env)
- [ ] Logs tonen "Authentication: ENABLED ✅"

### ✅ Netwerk
- [ ] Firewall blokkeert externe toegang (behalve port 1194)
- [ ] Alleen toegang via VPN voor externe verbindingen
- [ ] Reverse proxy gebruikt HTTPS certificaat
- [ ] Port 5000 en 8000 **niet** direct extern bereikbaar

### ✅ Vaultwarden
- [ ] Vaultwarden signups zijn **disabled** (`SIGNUPS_ALLOWED=false`)
- [ ] Bunq API key staat veilig in Vaultwarden vault
- [ ] Vaultwarden client credentials in `.env`
- [ ] Vaultwarden is alleen bereikbaar via LAN/VPN

### ✅ Backup
- [ ] Hyper Backup geconfigureerd voor:
  - `/volume1/docker/vaultwarden` (vault data)
  - `/volume1/docker/bunq-dashboard/config` (Bunq context)
- [ ] Backup retention: minimaal 30 dagen
- [ ] Test restore procedure minstens 1x

---

## 📊 VERGELIJKING: VOOR vs NA

| Aspect | Voor (Origineel) | Na (Beveiligd) |
|--------|------------------|----------------|
| **API Access** | ❌ Open voor iedereen op LAN | ✅ Basic Auth vereist |
| **CORS** | ❌ `*` (iedereen) | ✅ Specifieke origins |
| **Rate Limiting** | ❌ Geen | ✅ 30 req/min per IP |
| **Debug Mode** | ❌ `debug=True` | ✅ `debug=False` |
| **Key Logging** | ❌ Eerste 10 chars | ✅ Nooit gelogd |
| **Error Details** | ❌ Full stack traces | ✅ Generic errors |
| **Timing Attacks** | ❌ Kwetsbaar | ✅ Constant-time compare |

---

## 🛠️ TROUBLESHOOTING

### Probleem: "Authentication failed"
**Oplossing:**
```bash
# Check of wachtwoord correct is ingesteld
cat /volume1/docker/bunq-dashboard/.env | grep BASIC_AUTH_PASSWORD

# Herstart container
sudo docker-compose restart bunq-dashboard
```

### Probleem: "CORS error"
**Oplossing:**
```bash
# Update ALLOWED_ORIGINS in .env:
ALLOWED_ORIGINS=http://192.168.1.100:8000,https://bunq.jouw-domein.nl

# Rebuild
sudo docker-compose up -d --build
```

### Probleem: "Rate limit exceeded"
**Oplossing:**
- Wacht 60 seconden
- Verminder refresh frequency
- Check of er geen loop in je code zit

### Probleem: Demo data blijft laden
**Oplossing:**
1. Open Settings (⚙️)
2. Vul API credentials in
3. Enable "Gebruik echte Bunq data"
4. Save en Refresh

---

## 📚 AANVULLENDE SECURITY TIPS

### 1. Gebruik Sterke Wachtwoorden
```bash
# Genereer sterk wachtwoord (Linux/Mac):
openssl rand -base64 32

# Of gebruik password manager (Vaultwarden!)
```

### 2. Wissel Credentials Regelmatig
- Bunq API key: 1x per 6 maanden
- Basic Auth password: 1x per 3 maanden
- Vaultwarden master password: 1x per jaar

### 3. Monitor Logs
```bash
# Real-time monitoring:
sudo docker logs -f bunq-dashboard | grep "🚫"

# Check voor unauthorized attempts:
grep "Unauthorized" /volume1/docker/bunq-dashboard/logs/bunq_api.log
```

### 4. Regular Updates
```bash
# Check voor updates:
cd /volume1/docker/bunq-dashboard
git pull

# Rebuild:
sudo docker-compose build --no-cache
sudo docker-compose up -d
```

---

## 🆘 SUPPORT

Bij vragen of problemen:

1. **Check logs eerst:**
   ```bash
   sudo docker-compose logs bunq-dashboard
   ```

2. **Verify configuratie:**
   ```bash
   cat .env  # Check alle settings
   ```

3. **Test health endpoint:**
   ```bash
   curl http://192.168.1.100:5000/api/health
   ```

4. **GitHub Issues:** [Create Issue](https://github.com/richardvankampen/Bunq-dashboard-web/issues)

---

## 📄 LICENSE

MIT License - Zie originele [LICENSE](LICENSE) file

---

**🔐 Security First - Enjoy your protected financial dashboard!**

*Gemaakt met ❤️ voor veiligheid en privacy*
