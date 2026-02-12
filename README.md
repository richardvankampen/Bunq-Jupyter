# 💰 Bunq Financial Dashboard

**Veilige web-based visualisaties van je Bunq transactiedata (Synology-first)**
Read-only dashboard dat data uit de Bunq API haalt en overzichtelijk visualiseert.

⚠️ **IMPORTANT:** Access ONLY via VPN. NEVER forward ports to the internet.

---

## ✨ Belangrijkste Features

- Single-port dashboard (frontend + API) op poort 5000
- Real-time data uit de Bunq API (read-only)
- Vaultwarden-first key management (aanbevolen), met optionele directe fallback
- Lokale history-opslag (SQLite) voor langere-termijn inzichten
- EUR-totalen voor niet-EUR rekeningen (met FX conversie en caching)
- 11+ visualisaties (cashflow, trends, categorieën)
- Caching en pagination voor performance
- Synology‑ready deployment
- Admin maintenance tools in Settings (status, egress IP, Bunq context re-init)

**Visualisaties:**
- KPI Cards (inkomsten/uitgaven/sparen)
- Cashflow timeline
- Sankey diagram (geldstromen)
- Sunburst (categorieën)
- 3D time-space chart
- Heatmap (dag/uur)
- Top merchants
- Ridge plot (distributie)
- Racing bar chart
- Insights (automatisch)
- Custom charts

## 🔒 Security (Kort)

- Session-based auth met HttpOnly cookies en CSRF‑bescherming
- `SESSION_COOKIE_SECURE=true` als veilige default (zet alleen op `false` bij lokale HTTP)
- Secrets via Vaultwarden + Docker Swarm secrets (Vaultwarden is preferred)
- VPN‑only toegang, geen publieke exposure
- Rate limiting op login en API
Meer details: [SECURITY.md](SECURITY.md)

## 🚀 Quick Start (Synology)

1. Installeer **Container Manager** (Package Center)
2. Zorg voor **VPN-only toegang** (geen publieke exposure)
3. Volg de volledige installatieguide: [SYNOLOGY_INSTALL.md](SYNOLOGY_INSTALL.md)
4. Gebruik **Vaultwarden als primaire Bunq API key bron** (`USE_VAULTWARDEN=true`)
5. Gebruik directe `bunq_api_key` alleen als nood-fallback (`USE_VAULTWARDEN=false`)
6. Bij nieuwe Bunq API key of IP-wijziging: run `scripts/register_bunq_ip.sh`

---

## 📄 License

MIT License - See [LICENSE](LICENSE)
