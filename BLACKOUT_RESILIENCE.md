# Whitelisting & Blackout Resilience Analysis: GitHub & Vercel in Iran's Network Topology

## 1. Executive Summary & Problem Formulation

During macroscopic network disruptions and state-directed internet shutdowns in Iran, ordinary web browsing to international media outlets (BBC Persian, Radio Farda, Iran International, Euronews, DW) is immediately severed through multiple layered mechanisms: DNS poisoning, Layer 7 (L7) SNI filtering, TCP RST injection, and bandwidth throttling down to sub-dialup speeds (10–50 kbps).

Traditional news delivery channels fail catastrophically under these conditions:
1. **Websites:** Massive payload size (5–12 MB per page load consisting of client-side JavaScript frameworks, analytics beacons, video player engines, and font files) causes TCP connection timeouts under severe latency and throttling.
2. **LLM Summarizers:** Running real-time LLM inference (OpenAI, Anthropic, Gemini) per article is expensive, fragile, dependent on foreign API keys subject to sanctions, and requires constant cloud-to-cloud API transit that can be blocked or throttled.
3. **Proprietary Mobile Apps:** Heavy API dependencies and telemetry that are easily blocked by domain and IP filtering at the Telecommunication Infrastructure Company (TIC / شرکت ارتباطات زیرساخت).

This document analyzes why an **asynchronous, zero-LLM-cost hourly news aggregator hosted on GitHub (`github.com` / `raw.githubusercontent.com`) and mirrored on Vercel (`*.vercel.app`)** exhibits extraordinary resilience during network disruptions, and outlines the precise architectural dynamics of domestic routing, enterprise dependencies, and Deep Packet Inspection (DPI).

---

## 2. Iranian Network Infrastructure & Shutdown Topology

To understand why GitHub and Vercel survive when news websites are blocked, one must inspect the topology of Iran's **National Information Network (NIN / شبکه ملی اطلاعات)** and the border transit hierarchy:

```
+-------------------------------------------------------------------------+
|                  TIC International Border Gateways                      |
|       (E1/STM-1/100G uplinks via Turkey, Armenia, Persian Gulf)         |
+-------------------------------------------------------------------------+
                                    |
+-------------------------------------------------------------------------+
|                    National DPI Filtering Matrix                        |
|       (In-line & passive DPI: Sahab Pardaz, Douran, Huawei)             |
|   - DNS Poisoning (NXDOMAIN / Spoofed 10.10.34.3x IP)                   |
|   - TLS ClientHello SNI Filtering                                       |
|   - Dynamic Bandwidth Throttling & Artificial TCP Packet Loss           |
+-------------------------------------------------------------------------+
                                    |
         +--------------------------+--------------------------+
         |                                                     |
         v                                                     v
+--------------------------------+            +--------------------------------+
| Domestic Datacenters (IXP/NIN) |            |   Domestic Consumer ISPs       |
| (Asiatech, Arvan, Pars Online, |            |   (MCI, Irancell, Shatel,      |
|  Mobarakeh, Afranet)           |            |    Mokhaberat, Rightel)        |
+--------------------------------+            +--------------------------------+
```

### The Three Operational Tiers of Censorship:
1. **Tier 1 — Selective L7 DPI Filtering (Normal / Daily State):**
   - Specific domains, HTTP Host headers, and TLS SNI strings (e.g. `bbc.com`, `radiofarda.com`, `iranintl.com`) are dropped or sent forged TCP RST packets.
2. **Tier 2 — National Intranet Mode / Selective Whitelisting (Severe Disruption):**
   - International internet transit is restricted to an approved whitelist of external IP ranges and domain categories. Commercial banking, flight reservation systems, and critical domestic software services must remain operational to prevent economic paralysis.
3. **Tier 3 — Total Border Gateway Severance (Physical / BGP Severance):**
   - Border BGP sessions are torn down. International transit across all ports is zeroed out.

GitHub and Vercel survive almost universally throughout **Tier 1** and significantly into **Tier 2**.

---

## 3. Why GitHub Survives: The Domestic Dependency Shield

### 3.1 The Domestic Tech Ecosystem Trap (Blast Radius)
The single biggest defense mechanism for GitHub in Iran is **economic and infrastructural collateral damage**:
- **Enterprise Software Dependency:** Iran's largest domestic tech companies (Snapp, Digikala, Divar, Cafe Bazaar, Takhfifan, Torob), fintechs (ZarinPal, Nobitex), private banks, and government IT contractor firms run their core software development workflows on Git, CI/CD, and open-source ecosystems hosted on GitHub.
- **Package Manager Breakage:** Modern software stacks rely on direct git lookups and raw tarball downloads:
  * `npm install` and `yarn` frequently pull Git repositories directly from `github.com`.
  * `go get` fetches source trees hosted on `github.com`.
  * `pip install git+https://github.com/...` is ubiquitous in AI and data science teams across Iranian universities and companies.
  * `cargo` (Rust), `composer` (PHP), and `podman`/`docker` build files reference GitHub release assets.
- **Linux Server Bootstrapping:** Server provisioning scripts, system updates, and container base images throughout domestic datacenters (Asiatech, ArvanCloud) fetch shell scripts, keys, and manifests directly from `raw.githubusercontent.com`.

**The Invariant:** Severing GitHub (`github.com` or `raw.githubusercontent.com`) instantly paralyzes software deployments, bug fixes, and continuous delivery across Iran's commercial and state-sanctioned infrastructure. The political and economic cost of blocking GitHub blanket-style is astronomically higher than blocking a conventional news website.

### 3.2 Anycast Architecture & Fastly CDN Edge Distribution
- `raw.githubusercontent.com` is hosted on **Fastly CDN Anycast IP ranges** (primarily `151.101.0.0/16`).
- Fastly's Anycast IPs do not belong to GitHub exclusively; they are shared multi-tenant edge nodes routing traffic for thousands of global enterprises, financial institutions, media CDNs, and SaaS products.
- Blocking Fastly at Layer 3 (IP blocking) causes widespread indiscriminate collateral breakage across arbitrary international web services.

### 3.3 Deep Packet Inspection (DPI) & Path Encryption Dynamics
Iranian DPI middleboxes inspect traffic at the border:
- Under **TLS 1.2 and TLS 1.3**, the HTTP request path (e.g., `/your-username/news-aggregator/main/news/latest.md`) is **fully encrypted** within the TLS record layer.
- The DPI middlebox can only observe:
  1. The destination IP (`151.101.x.x`).
  2. The TLS `Server Name Indication` (SNI) in the plaintext `ClientHello` (`raw.githubusercontent.com`).
- To block Ali's news feed on `raw.githubusercontent.com`, the censor has only two options:
  1. *Allow `raw.githubusercontent.com`:* In which case Ali's news files pass through unhindered.
  2. *Block `raw.githubusercontent.com` entirely:* In which case tens of thousands of developer build tools and server deploy scripts fail nationwide.

Because path-based URL blocking on HTTPS requires TLS termination (Man-In-The-Middle inspection), which is technically infeasible across standard mobile and desktop operating systems without installing rogue root certificates (which break certificate pinning in Git and browsers), GitHub raw files remain accessible.

### 3.4 Multi-Protocol Accessibility (HTTPS vs. SSH)
GitHub is uniquely accessible over multiple transport protocols:
- **HTTPS (Port 443):** Standard web fetch, raw content, REST API (`api.github.com`).
- **SSH (Port 22):** `git clone git@github.com:...` or `git pull`. SSH traffic uses a completely different cryptographic handshake and protocol structure that bypasses TLS SNI inspection rules entirely. Unless port 22 is blackholed nationwide, news markdown archives can be pulled continuously over SSH.

---

## 4. Why Vercel Survives: The Edge Network & Multi-Tenant Dilution

Vercel (`*.vercel.app` and custom domains) exhibits similar resilience for distinct architectural reasons:

### 4.1 Anycast Edge Infrastructure (AWS Global Accelerator & Cloudflare Peering)
- Vercel's Edge Network is deployed on globally distributed Anycast IP addresses (such as `76.76.21.21`).
- BGP Anycast routes user traffic to the topologically closest healthy edge Point of Presence (PoP), often in Frankfurt, Istanbul, or Dubai.
- TCP handshakes terminate at the edge, meaning Round-Trip Time (RTT) is minimized even when international transit to North America is degraded.

### 4.2 Multi-Tenant IP Dilution
- Millions of web applications, personal portfolios, open-source documentation sites, and indie tools share Vercel's core Anycast IPs.
- Blacklisting Vercel's edge IP addresses breaks legitimate commercial tools, customer sites, and university projects developed by Iranian programmers who use Vercel for free frontend hosting.

### 4.3 Custom Domain Camouflage
- While the wildcard domain `*.vercel.app` can theoretically be added to an SNI filter, Vercel allows binding custom domains (e.g., an unblocked personal domain or a $0.80 numeric `.xyz` domain) with automatic zero-configuration SSL certificates from Let's Encrypt / ZeroSSL.
- A news dashboard hosted on Vercel under an inconspicuous custom domain completely decouples the application from any known domain blacklists.

### 4.4 Static Asset Edge Caching & Bandwidth Footprint
- The news aggregator generates static HTML, CSS, and JSON (< 30 KB total).
- Once deployed, Vercel caches these assets at the edge nodes. Requests do not trigger serverless cold starts or backpressure to origin servers. The response is returned within tens of milliseconds over minimal byte transfers.

---

## 5. Micro-Payload Engineering: The Anti-Throttling Paradigm

When Iranian ISPs implement artificial packet loss and bandwidth throttling (capping lines at 10–64 kbps):

| Channel | Typical Payload Size | Assets per Load | Time on 32 kbps Throttled Uplink | Failure Mode |
|---|---|---|---|---|
| **BBC Persian Webpage** | 4.8 MB | ~110 requests (JS, CSS, fonts, tracking) | ~20 minutes | **Timeout / TCP Connection Drop** |
| **Iran International Web** | 6.2 MB | ~140 requests (video players, ads) | ~26 minutes | **Timeout / Script Crash** |
| **Euronews Persian Web** | 3.9 MB | ~95 requests | ~16 minutes | **Timeout / Incomplete Render** |
| **Ali's Raw Markdown (`news/latest.md`)** | **14 KB** | **1 request (pure text)** | **~3.5 seconds** | **100% Success** |
| **Ali's Static HTML Dashboard** | **24 KB** | **1 request (inlined CSS/JS)** | **~6 seconds** | **100% Success** |

By shedding 99.7% of typical web bloat and stripping all tracking scripts, images, and heavy client frameworks, the pure Markdown and standalone HTML can be retrieved over the most severely degraded, packet-dropped connections in the country.

---

## 6. Access Matrix Across Outage Tiers

```
+-----------------------------------------------------------------------------------------+
| Censorship Severity Level        | Access Method               | Resilient Channel       |
+----------------------------------+-----------------------------+-------------------------+
| Tier 1: Standard SNI Block       | Web Browser                 | Vercel Edge / GH Pages  |
|                                  | Mobile Web                  | raw.githubusercontent   |
+----------------------------------+-----------------------------+-------------------------+
| Tier 2: Severe Intranet / NIN    | Raw Markdown via curl       | raw.githubusercontent   |
| (Whitelisted Enterprise Mode)    | Git CLI over HTTPS or SSH   | git pull --depth 1      |
|                                  | GitHub Mobile App / API     | api.github.com          |
+----------------------------------+-----------------------------+-------------------------+
| Tier 3: Total Border Gateway Cut | DNS Tunnel (Port 53 UDP)    | MasterDnsVPN / dnstt    |
| (L3/L4 Severance)                | Domestic Messenger Bridge   | Bale / ECIES Stego      |
|                                  | Offline Local Knowledge     | Git Archive / Obsidian  |
+----------------------------------+-----------------------------+-------------------------+
```

---

## 7. Operational Recommendations for Ali

1. **Deploy Dual Frontends:**
   - Primary: GitHub Pages (`https://<username>.github.io/<repo>/`).
   - Mirror: Vercel (`https://<custom-subdomain>.vercel.app`).
2. **Direct Markdown Reading:**
   - Bookmark the raw URL in mobile and desktop browsers:
     `https://raw.githubusercontent.com/<username>/<repo>/main/news/latest.md`
   - In terminal/Termux:
     ```bash
     curl -s https://raw.githubusercontent.com/<username>/<repo>/main/news/latest.md | less
     ```
3. **Local Offline Syncing (The Obsidian Vault Pattern):**
   - Keep the repository cloned inside an Obsidian vault on local devices (MacBook Booris, laptop, phone via Working Copy / Termux).
   - A single-second `git pull` automatically updates the entire offline news archive whenever connectivity briefly flickers back on.
