# Multi-Agent Telephony, WebRTC Extensions & Inbound Group Routing Guide

**Server**: FreePBX 17 / Asterisk 22 (`voice.bridge.ng` / `sip.bridge.ng` / `webrtc.bridge.ng`)  
**CRM App**: Frappe CRM & `bridge_telephony`  
**DID**: `02016335890` (IPNX Telecoms) & Vapi/ElevenLabs Voice AI  

---

## Table of Contents
1. [Architecture & Attribution Model](#1-architecture--attribution-model)
2. [Agent Extension Numbering Plan](#2-agent-extension-numbering-plan)
3. [Automated FreePBX WebRTC Extension Provisioning](#3-automated-freepbx-webrtc-extension-provisioning)
4. [Frappe CRM Agent Profile Setup (`CRM Telephony Agent`)](#4-frappe-crm-agent-profile-setup)
5. [Inbound Call Distribution: Ring Groups vs. Queues](#5-inbound-call-distribution-ring-groups-vs-queues)
   - [Configuring a Ring Group (e.g. Ext 600 - Sales Team)](#a-configuring-a-ring-group-recommended-for-start)
   - [Configuring a Call Queue (e.g. Ext 700 - Support Queue)](#b-configuring-a-call-queue-advanced)
   - [Connecting Inbound Route (DID 02016335890)](#c-connecting-inbound-route-did-02016335890)
6. [Internal Group Dialing & Call Transfers](#6-internal-group-dialing--call-transfers)
7. [Inbound Screen-Pop & Dialplan Hooks](#7-inbound-screen-pop--dialplan-hooks)
8. [Quick Reference & Feature Codes](#8-quick-reference--feature-codes)

---

## 1. Architecture & Attribution Model

When agents place or receive calls in Frappe CRM, every call record (`CRM Call Log`) is automatically attributed to the agent's User ID and Role:

```mermaid
flowchart TD
    subgraph FreePBX ["FreePBX 17 / Asterisk 22"]
        DID["Inbound DID 02016335890\n(IPNX / Vapi AI)"]
        RG["Ring Group 600\n(Sales Team)"]
        Ext1["PJSIP Ext 2001\n(Kaosiso)"]
        Ext2["PJSIP Ext 2002\n(Victor)"]
        Ext3["PJSIP Ext 2003\n(Computer Village)"]
        Ext4["PJSIP Ext 2004\n(Okechukwu)"]
    end

    subgraph CRM ["Frappe CRM Backend & UI"]
        AgentProfile["CRM Telephony Agent\n(User <-> Extension Mapping)"]
        CallLog["CRM Call Log\n- caller / receiver: User\n- status: Completed\n- recording_url: audio stream"]
        Timeline["Lead / Deal Activity Timeline\n(Avatars, Notes, Tasks, Audio Playback)"]
    end

    DID -->|Routes to| RG
    RG -->|ringall strategy| Ext1
    RG -->|ringall strategy| Ext2
    RG -->|ringall strategy| Ext3
    RG -->|ringall strategy| Ext4

    Ext1 <-->|WSS :8089 (SIP.js)| CRM
    Ext2 <-->|WSS :8089 (SIP.js)| CRM
    Ext3 <-->|WSS :8089 (SIP.js)| CRM
    Ext4 <-->|WSS :8089 (SIP.js)| CRM

    FreePBX -->|Webhook on Hangup| CallLog
    AgentProfile -->|Resolves Extension to User| CallLog
    CallLog -->|Attaches Child Dynamic Link| Timeline
```

### Attribution Rules:
1. **Outbound Call**: The agent clicks *Make Call* on a Lead. Frappe CRM checks `CRM Telephony Agent` for `frappe.session.user`, retrieves their extension (e.g. `2001`), and originates the call. The resulting `CRM Call Log` sets `caller = frappe.session.user`.
2. **Inbound Call**: When a customer calls DID `02016335890`, Ring Group `600` rings all agents. Whichever agent answers (e.g. extension `2002`), Asterisk records `dst = 2002`. The post-call webhook resolves extension `2002` to `victor@edubridge.info` and sets `receiver = victor@edubridge.info`.
3. **Role-Based Visibility**: In Frappe CRM, *Sales Users* see their own call logs, while *Sales Managers* and *System Managers* see all call logs across all extensions in the group.

---

## 2. Agent Extension Numbering Plan

To prevent conflicts between standard softphones, WebRTC browser dialers, and group routing:

| Range | Type | Purpose | Examples |
| :--- | :--- | :--- | :--- |
| **`1001 – 1099`** | PJSIP (UDP/TCP) | Dedicated Desktop Softphones (MicroSIP / Hardphones) | `1001` (Support Desk) |
| **`2001 – 2099`** | PJSIP (WSS + DTLS) | Dedicated Frappe CRM WebRTC Browser / PWA Agents | `2001` (Kaosiso), `2002` (Victor) |
| **`600 – 699`** | Ring Groups | Simultaneous or hunt groups for sales/support | `600` (Sales Group), `601` (Billing) |
| **`700 – 799`** | Call Queues | Queues with hold music, position announcements | `700` (Customer Support Queue) |

---

## 3. Automated FreePBX WebRTC Extension Provisioning

You can create WebRTC extensions for all your CRM users directly on the FreePBX server using this automated PHP script.

### Step 1: Run the Provisioning Script on FreePBX
SSH into the FreePBX server:
```bash
ssh -i ~/.ssh/dokploy_ed25519 azureuser@172.187.235.228
```

Run the following one-liner to create extensions `2001` to `2005` with full WebRTC, DTLS, AVPF, and RTCP-MUX enabled:

```bash
sudo php -r '
require "/etc/freepbx.conf";

$extensions = [
    ["ext" => "2001", "name" => "Kaosiso Anaekwe", "secret" => "BridgeVoice2026!WebRTC"],
    ["ext" => "2002", "name" => "Victor Ego",      "secret" => "BridgeVoice2026!Victor"],
    ["ext" => "2003", "name" => "Computer Village", "secret" => "BridgeVoice2026!CV"],
    ["ext" => "2004", "name" => "Okechukwu Anaekwe","secret" => "BridgeVoice2026!Okey"],
    ["ext" => "2005", "name" => "Accountant",       "secret" => "BridgeVoice2026!Acct"]
];

$defaultCert = \FreePBX::Certman()->getDefaultCertDetails();
$dtls = [
    "certificate" => $defaultCert["cid"],
    "verify" => "fingerprint",
    "setup" => "actpass",
    "rekey" => "0"
];

foreach ($extensions as $agent) {
    $ext = $agent["ext"];
    $name = $agent["name"];
    $secret = $agent["secret"];

    echo "==> Configuring WebRTC Extension $ext ($name)...\n";

    // Clean existing if any
    if (\FreePBX::Core()->getUser($ext)) {
        \FreePBX::Core()->delUser($ext);
    }
    if (\FreePBX::Core()->getDevice($ext)) {
        \FreePBX::Core()->delDevice($ext);
    }

    // 1. Create User
    $user_settings = \FreePBX::Core()->getUser("1001");
    if (!$user_settings) {
        $user_settings = ["ringtimer" => 0, "voicemail" => "novm", "recording" => "force"];
    }
    $user_settings["extension"] = $ext;
    $user_settings["name"] = $name;
    $user_settings["cid_masquerade"] = $ext;
    $user_settings["outboundcid"] = "02016335890";
    \FreePBX::Core()->addUser($ext, $user_settings);

    // 2. Create Device with WebRTC parameters
    $dev = \FreePBX::Core()->generateDefaultDeviceSettings("pjsip", $ext, $name);
    $dev["secret"]["value"] = $secret;
    $dev["webrtc"]["value"] = "yes";
    $dev["avpf"]["value"] = "yes";
    $dev["icesupport"]["value"] = "yes";
    $dev["rtcp_mux"]["value"] = "yes";
    $dev["media_encryption"]["value"] = "dtls";
    $dev["media_use_received_transport"]["value"] = "yes";
    $dev["transport"]["value"] = "0.0.0.0-wss";
    $dev["context"]["value"] = "from-internal";
    $dev["user"]["value"] = $ext;
    $dev["devicetype"]["value"] = "fixed";

    \FreePBX::Core()->addDevice($ext, "pjsip", $dev);

    // 3. Link DTLS Certificate
    \FreePBX::Certman()->addDTLSOptions($ext, $dtls);
}

\FreePBX::Core()->doConfig();
echo "==> Applying Asterisk configuration...\n";
\FreePBX::Framework()->runReload();
echo "==> All WebRTC extensions provisioned successfully!\n";
'
```

---

## 4. Frappe CRM Agent Profile Setup

Once the extensions are in FreePBX, link each CRM user to their extension in Frappe CRM.

### Method A: Automated via Bench Console (Fastest)
From your bench directory (`~/bench/bridge`):

```bash
./env/bin/python -c "
import frappe
frappe.init(site='local.bridge.ng', sites_path='sites')
frappe.connect()

agent_mappings = [
    {'user': 'Administrator',               'ext': '2001', 'medium': 'FreePBX'},
    {'user': 'victor@edubridge.info',       'ext': '2002', 'medium': 'FreePBX'},
    {'user': 'kaosiso@computervillage.ng',  'ext': '2003', 'medium': 'FreePBX'},
    {'user': 'kanaekwe@gmail.com',          'ext': '2004', 'medium': 'FreePBX'},
    {'user': 'kossanah@gmail.com',          'ext': '2005', 'medium': 'FreePBX'}
]

for mapping in agent_mappings:
    user = mapping['user']
    ext = mapping['ext']
    medium = mapping['medium']
    
    if not frappe.db.exists('User', user):
        continue

    if frappe.db.exists('CRM Telephony Agent', user):
        doc = frappe.get_doc('CRM Telephony Agent', user)
        doc.default_medium = medium
        doc.freepbx = 1
        doc.freepbx_extension = ext
        doc.call_receiving_device = 'Computer'
        doc.save(ignore_permissions=True)
        print(f'Updated Telephony Agent: {user} -> Ext {ext}')
    else:
        doc = frappe.get_doc({
            'doctype': 'CRM Telephony Agent',
            'user': user,
            'default_medium': medium,
            'freepbx': 1,
            'freepbx_extension': ext,
            'call_receiving_device': 'Computer'
        }).insert(ignore_permissions=True)
        print(f'Created Telephony Agent: {user} -> Ext {ext}')

frappe.db.commit()
frappe.destroy()
print('Agent provisioning complete!')
"
```

### Method B: Manual Setup in Frappe Desk UI
1. Search for **CRM Telephony Agent** in the Awesome Bar.
2. Select or create an agent profile for each user.
3. Configure:
   - **User**: Select user (e.g. `victor@edubridge.info`)
   - **Default Medium**: `FreePBX`
   - **FreePBX Enabled**: `Checked`
   - **FreePBX Extension**: `2002`
   - **Device**: `Computer` (Browser WebRTC)
4. Click **Save**.

---

## 5. Inbound Call Distribution: Ring Groups vs. Queues

### Comparison: Which should you use?

| Feature | Ring Group (`600`) | Call Queue (`700`) |
| :--- | :--- | :--- |
| **Best For** | Sales teams (< 10 agents), instant simultaneous ringing | Support centers, high inbound volume, call waiting |
| **Ringing Behavior** | Rings all agents at once (`ringall`) or in order (`hunt`) | Round Robin (`rrmemory`), least recent, fewest calls |
| **Hold Music** | Ringing tone (or music while ringing) | Custom hold music (`Call Queue Media`) with wait loop |
| **Queue Position** | No | Yes ("You are caller number 2...") |
| **Agent Login/Logout**| Static extension list | Dynamic (`*45` to log in/out at the start/end of shift) |

---

### A. Configuring a Ring Group (Recommended for Start)

#### In FreePBX GUI:
1. Navigate to **Applications** > **Ring Groups** > **Add Ring Group**.
2. **Ring-Group Number**: `600`
3. **Group Description**: `Sales Team`
4. **Extension List**:
   Enter one extension per line:
   ```text
   2001
   2002
   2003
   2004
   ```
   *(Note: You can also include `1001` if you want softphones to ring alongside browser WebRTC!)*
5. **Ring Strategy**:
   - `ringall`: (Default) Rings all agent extensions simultaneously. The first agent to answer takes the call.
   - `hunt`: Rings extension 2001 for 15s; if no answer, rings 2002 for 15s, etc.
   - `memoryhunt`: Rings 2001; then rings 2001 + 2002; then rings 2001 + 2002 + 2003.
6. **Ring Time (max 300 sec)**: `25` seconds (gives agents ~5 rings to answer).
7. **Destination if no answer**:
   - Option 1: **Custom Destinations** > `Vapi Customer Voice AI` (AI takes a message or assists).
   - Option 2: **Voicemail** > `<2001> (novm)`.
   - Option 3: **Terminating Call** > `Hangup`.
8. Click **Submit** and **Apply Config**.

#### Automated CLI Command for Ring Group `600`:
On the FreePBX server:
```bash
sudo php -r '
require "/etc/freepbx.conf";
$rg = \FreePBX::Ringgroups();
$data = [
    "grpnum" => "600",
    "description" => "Sales Team",
    "grplist" => "2001-2002-2003-2004",
    "strategy" => "ringall",
    "grptime" => "25",
    "postdest" => "ext-local,2001,noanswer"
];
$rg->addRinggroup("600", $data);
\FreePBX::Framework()->runReload();
echo "Ring Group 600 created successfully!\n";
'
```

---

### B. Configuring a Call Queue (Advanced)

If you have higher call volume and want callers to hear hold music and wait in line:

1. Navigate to **Applications** > **Queues** > **Add Queue**.
2. **Queue Number**: `700`
3. **Queue Name**: `Customer Support Queue`
4. **Queue Strategy**: `rrmemory` (Round Robin with Memory — remembers who answered last so calls rotate fairly between agents).
5. **Static Agents**:
   - Put extensions that should always be in the queue:
     ```text
     2001,0
     2002,0
     2003,0
     ```
6. **Music on Hold Class**: Select your preferred MOH class (or default hold music).
7. **Failover Destination**: Choose where the call goes if wait time exceeds 60 seconds (e.g. Ring Group 600 or Vapi AI).
8. Click **Submit** and **Apply Config**.

---

### C. Connecting Inbound Route (DID 02016335890)

Now connect your incoming IPNX phone number to the group:

1. In FreePBX GUI, go to **Connectivity** > **Inbound Routes**.
2. Select your route for `02016335890` (or add a new route):
   - **Description**: `IPNX Inbound to Sales Ring Group`
   - **DID Number**: `02016335890`
   - **Set Destination**: Choose **Ring Groups** > `600 (Sales Team)`.
3. Click **Submit** and **Apply Config**.

#### AI-First Hybrid Inbound Flow:
If you want **Vapi Voice AI** to answer first, screen the caller, and transfer to humans on request:
1. Point Inbound Route `02016335890` to **Custom Destinations** > `Vapi Customer Voice AI`.
2. In your **Vapi Dashboard** > Assistant > **Tools**:
   - Add a **Transfer Call** action.
   - Set Destination SIP URI to:
     ```text
     sip:600@sip.bridge.ng
     ```
   - When a customer says *"I want to speak with sales"*, Vapi sends a SIP REFER to `600`. FreePBX immediately rings Ring Group `600`, and all sales agents' browsers ring simultaneously!

---

## 6. Internal Group Dialing & Call Transfers

### Dialing the Group Internally
Any agent on WebRTC or softphone can dial the group number directly from the dialer:
* Dial **`600`**: Rings the entire Sales Ring Group.
* Dial **`700`**: Calls into the Support Queue.
* Dial **`2002`**: Directly calls Victor's browser extension.

### Transferring Calls between Agents / Groups

During an active WebRTC call in Frappe CRM:
* **Attended Transfer (Consultative)**:
  1. Press `*2` on the dialpad.
  2. Asterisk prompts *"Transfer"*.
  3. Dial the target extension (e.g. `2002`) or group (e.g. `600`).
  4. Speak to the colleague first, then hang up to complete the transfer.
* **Blind Transfer**:
  1. Press `##` on the dialpad.
  2. Asterisk prompts *"Transfer"*.
  3. Dial `2002` or `600` and immediately hang up. The customer is directly connected.

---

## 7. Inbound Screen-Pop & Dialplan Hooks

To ensure the incoming call pop-up appears on all group members' screens:

In `/etc/asterisk/extensions_custom.conf`:
```ini
[from-pstn-custom]
exten => _.,1,NoOp(Frappe CRM Inbound Screen-Pop: Caller=${CALLERID(num)} DID=${EXTEN})
; Broadcast to bridge_telephony webhook (triggers Redis WebSocket to all active agents)
same => n,System(/usr/bin/curl -s -m 2 -X POST -H "Host: local.bridge.ng" http://127.0.0.1:18000/api/method/bridge_telephony.api.freepbx.incoming_call -d "caller=${CALLERID(num)}&did=${EXTEN}&destination=600" >/dev/null 2>&1 &)
same => n,Goto(ext-did-catchall,${EXTEN},1)

[macro-hangupcall-custom]
exten => s,1,NoOp(Frappe CRM Post-Call Hook: UniqueID=${CDR(uniqueid)} Agent=${CDR(dst)})
same => n,System(/usr/bin/curl -s -m 5 -X POST -H "Host: local.bridge.ng" http://127.0.0.1:18000/api/method/bridge_telephony.api.freepbx.webhook -d "uniqueid=${CDR(uniqueid)}&src=${CDR(src)}&dst=${CDR(dst)}&duration=${CDR(duration)}&billsec=${CDR(billsec)}&disposition=${CDR(disposition)}&recording=${CDR(recordingfile)}" >/dev/null 2>&1 &)
same => n,Return()
```

When Agent `2003` answers the ringing group call, Asterisk sets `${CDR(dst)} = 2003`. The hangup webhook queries `CRM Telephony Agent` for extension `2003`, maps it to `kaosiso@computervillage.ng`, and binds the completed call log and recording directly to that agent.

---

## 8. Quick Reference & Feature Codes

| Action | Dial Code / URI |
| :--- | :--- |
| **Sales Ring Group** | `600` |
| **Customer Support Queue** | `700` |
| **Direct WebRTC Extensions** | `2001`, `2002`, `2003`, `2004`, `2005` |
| **Desktop Softphone Extension** | `1001` |
| **Queue Agent Login / Toggle** | `*45` (or `*45700`) |
| **In-Call Attended Transfer** | `*2` |
| **In-Call Blind Transfer** | `##` |
| **Call Pickup (Any Ringing Phone)**| `*8` |
| **Directed Call Pickup** | `**<Extension>` (e.g. `**2002` to answer Victor's ringing phone) |
| **WebRTC WSS Endpoint** | `wss://webrtc.bridge.ng:8089/ws` *(or `wss://sip.bridge.ng:8089/ws`)* |
