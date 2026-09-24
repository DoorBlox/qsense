# Q-SENSE

**Queue Sensing and Evaluation System**

Q-SENSE is an IoT and computer-vision proof of concept for monitoring cafeteria queues in a boarding-school environment. It combines an ESP32-S3 camera node, local computer vision, Supabase, and a public Next.js dashboard.

> Current proof of concept: one physical camera node.  
> Database and dashboard architecture: ready for two independent physical queue nodes.

## What Q-SENSE Measures

### Live operational metrics
- Queue count
- Queue entry
- Service completion
- Abandonment
- Waiting time
- Throughput

### Session analytics
- Peak queue
- Mean queue
- Median queue
- Congestion duration
- Queue burden
- Meals served

### Menu analytics
- Menu demand
- Menu acceptance

**Important:** menu acceptance cannot be inferred from camera behavior alone. In the current presentation build, acceptance values are synthetic placeholders for a future independent acceptance instrument.

## Architecture

```text
ESP32-S3 N16R8 + OV5640
          |
          | Wi-Fi MJPEG
          v
Laptop / Local Processing
YOLO person detection
ByteTrack temporary IDs
Queue + service-line logic
          |
          | numerical metrics
          v
Supabase
          |
          v
Next.js + Vercel Dashboard
```

## Hardware

Current camera node:

- ESP32-S3 CAM N16R8
- OV5640 camera
- USB-C cable for programming
- 5 V USB power source for standalone use
- Wi-Fi network

## Standalone Power

The ESP32 does **not** need to stay connected to the laptop by USB after the firmware is uploaded.

Power it from either:

- a normal **5 V USB phone charger**, or
- a **USB power bank**

A stable **5 V / 2 A** USB supply is recommended.

Do not connect raw 18650 cells directly unless a suitable protected battery-management and voltage-regulation system is used.

## Network Requirement

For the current architecture, the ESP32 camera and laptop need to be reachable on the same local network.

Example:

```text
Wi-Fi: R-103

Laptop
  10.10.10.25

ESP32
  10.10.10.113
```

Python reads:

```text
http://10.10.10.113/stream
```

### Client isolation

Some school, hotel, or guest Wi-Fi networks prevent devices on the same SSID from communicating.

If both devices are on the same Wi-Fi but the stream does not open, the network may use AP/client isolation.

A presentation backup is to use:

- a tested personal hotspot, or
- Windows Mobile Hotspot from the laptop

and connect the ESP32 to that network.

The laptop still needs internet access for live Supabase/Vercel use.

## Configurable ESP32 Wi-Fi

Firmware:

```text
esp32/qsense_camera_configurable.ino
```

The firmware stores Wi-Fi settings in ESP32 non-volatile memory.

### Normal startup

1. Power the ESP32.
2. It loads saved Wi-Fi settings.
3. It connects automatically.
4. The camera server starts automatically.

Arduino IDE does not need to stay open.

### Change Wi-Fi without reflashing

1. Hold **BOOT**.
2. Press and release **RESET**.
3. Release **BOOT**.
4. Connect a laptop/phone to:

```text
SSID: Q-SENSE-CAM
Password: qsense123
```

5. Open:

```text
http://192.168.4.1
```

6. Select or type the new Wi-Fi SSID.
7. Enter the password.
8. For an open network, leave the password blank.
9. Press **Save & Restart**.
10. Reconnect the laptop to the same Wi-Fi network.

If the saved Wi-Fi cannot be reached during normal boot, the ESP enters configuration mode automatically.

## Camera URLs

Serial Monitor at **115200 baud** prints the current IP.

Example:

```text
IP address: 10.10.10.113
Browser: http://10.10.10.113
Stream:  http://10.10.10.113/stream
```

The firmware also attempts:

```text
http://qsense-cam.local
http://qsense-cam.local/stream
```

`.local` may not work on every network, so the printed IP remains the reliable fallback.

## Local Python Configuration

Main tracker:

```text
qsense_research_supabase.py
```

Configuration lives in:

```text
.env
```

Example:

```env
QSENSE_SECTION=male
QSENSE_CAMERA_SOURCE=http://10.10.10.113/stream
QSENSE_ROI_FILE=queue_zone_male.json
QSENSE_SERVICE_FILE=service_line_male.json
QSENSE_TEST_MODE=true
```

Never commit the real `.env`.

### Easy configuration helper

Run:

```powershell
python configure_qsense.py
```

It updates only `QSENSE_*` values and leaves Supabase credentials unchanged.

## Running Q-SENSE

### 1. Power the ESP32

Use a USB charger or power bank.

### 2. Check the camera

Open in Edge:

```text
http://ESP-IP
```

### 3. Start the tracker

```powershell
python qsense_research_supabase.py
```

or:

```powershell
.\run_qsense.ps1
```

### 4. Open the dashboard

Use the deployed Vercel URL in Microsoft Edge.

No `npm run dev` is required for the deployed site.

## Calibration

Current male-node files:

```text
queue_zone_male.json
service_line_male.json
```

If the camera is physically moved, recalibrate the queue zone and service line.

The AI model does not need retraining merely because the camera position changes.

## Privacy

Q-SENSE is designed without identity recognition:

- no facial recognition
- no student names
- no gender inference from images
- temporary ByteTrack IDs only
- numerical queue/event metrics are stored
- public dashboard does not need the camera stream

For two physical queues, each camera is assigned to its physical queue.

## Dashboard

Technology:

- Next.js
- TypeScript
- Tailwind CSS
- Recharts
- Lucide icons
- Supabase
- Vercel

Tabs:

- Overview
- Queue Analytics
- Menu Lab
- Validation
- System

The Overview includes a live moving queue graph.

## Demo / Synthetic Data

The presentation build contains synthetic historical data so that the analysis workflow can be demonstrated before full field data collection.

Synthetic/demo where applicable:

- historical queue curves
- side dishes not supplied by cafeteria records
- validation observations
- menu demand scores
- menu acceptance scores

Live camera status and live queue-event counters come from the working prototype.

## Supabase Tables

```text
live_status
queue_snapshots
queue_events
meal_log
manual_validation
session_metrics
```

`queue_events` should not be publicly exposed because it includes temporary track identifiers.

Frontend should use only:

```text
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
```

Never put the Supabase service-role key in frontend code.

## Git Safety

Before committing:

```powershell
git status
```

Make sure these are not committed:

```text
.env
web/.env.local
```

## Presentation Quick Start

```text
1. Power ESP32 camera
2. Confirm ESP32 IP
3. Confirm browser stream
4. Confirm laptop and ESP are on the same LAN
5. Update camera URL if IP changed
6. Run qsense_research_supabase.py
7. Open Vercel dashboard in Edge
8. Test ENTER
9. Test SERVED
10. Test ABANDONED
```

## Troubleshooting

### Camera page does not open
Check:
- ESP32 has power
- current ESP32 IP
- laptop and ESP32 are on the same local network
- network does not use client isolation

### ESP cannot connect to Wi-Fi
Enter configuration mode:

```text
Hold BOOT → press RESET → release BOOT
```

Then connect to:

```text
Q-SENSE-CAM
```

and open:

```text
http://192.168.4.1
```

### ESP IP changed

Run:

```powershell
python configure_qsense.py
```

and update the camera URL.

### Firefox shows React/SVG permission errors

Use Microsoft Edge for the presentation.

## Project Name

**Q-SENSE**  
**Queue Sensing and Evaluation System**
