# Satellite Telemetry Dashboard - Frontend

## Overview
Professional mission control dashboard for real-time satellite telemetry monitoring with AI-powered fault diagnosis. Features a dark theme with cyan accents inspired by aerospace mission control interfaces.

## Tech Stack
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **3D Visualization**: Three.js / React Three Fiber
- **Charts**: Canvas-based real-time telemetry charts
- **HTTP Client**: Axios

## Design Features

### 🎨 Professional Mission Control UI
- **Dark aerospace theme** - Navy/black background (#0a1628, #0d1b2a)
- **Cyan/teal accents** - High-tech look with #06b6d4 primary color
- **Glass-morphism effects** - Backdrop blur and transparency
- **Animated elements** - Pulse effects, smooth transitions
- **Status indicators** - Color-coded health indicators
- **Monospace fonts** - Technical data display

## Setup Instructions

### 1. Install Dependencies
```bash
npm install
```

### 2. Environment Configuration
Create a `.env.local` file:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
npm run dev
```

The app will be available at http://localhost:3000

### 4. Build for Production
```bash
npm run build
npm start
```

## Features

### �️ Left Sidebar Navigation
- Dashboard, Satellites, Telemetry, Fault Diagnosis
- XAI Insights, Data Store, Settings
- System online status indicator
- Professional menu with hover effects

### 📊 Top Stats Cards (4 Key Metrics)
- **Active Satellites**: Fleet status and availability
- **Signal Strength**: Average dB across fleet
- **Active Faults**: Critical and warning count
- **Thermal Status**: Max temperature monitoring

### 📈 Real-time Telemetry Chart
- Canvas-based streaming visualization
- Signal, Power, and Thermal data lines
- Grid overlay with time axis
- Smooth animations and shadow effects

### 🛰️ Satellite Fleet List
- Individual satellite health percentages
- Orbit information (LEO/MEO)
- Color-coded status indicators
- Last update timestamps

### 📡 Live Telemetry Panel
- Real-time monitoring of 6 telemetry channels:
  - Magnetometer X, Y, Z (CADC0872-0874)
  - Photodiodes 1-3 (CADC0875-0877)
- Auto-refreshing data every 2 seconds
- Visual status indicators

### 🔍 Anomaly Detection Panel
- FCNN model analysis results
- Anomaly probability visualization
- Severity indicators (LOW, MEDIUM, HIGH)
- Model accuracy metrics

### 🧠 Knowledge Graph Root Cause Analysis
- Top probable root causes with confidence scores
- Graph statistics (nodes, relationships)
- Affected subsystems display

### 📋 Fault Diagnosis & Explanation
- AI-powered diagnosis with LLM + RAG
- Technical explanations
- Recommended corrective actions
- Severity assessment with confidence levels

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── globals.css          # Global styles with Tailwind
│   │   ├── layout.tsx           # Root layout
│   │   └── page.tsx             # Main dashboard page
│   ├── components/
│   │   ├── AnomalyPanel.tsx     # Anomaly detection display
│   │   ├── DiagnosisPanel.tsx   # Fault diagnosis & explanations
│   │   ├── Header.tsx           # App header with status
│   │   ├── KnowledgeGraphPanel.tsx  # Root cause analysis
│   │   ├── SatelliteViewer.tsx  # 3D satellite visualization
│   │   └── TelemetryPanel.tsx   # Live telemetry data
│   └── store/
│       └── telemetryStore.ts    # Zustand global state
├── .env.local                    # Environment variables
├── next.config.js               # Next.js configuration
├── package.json                 # Dependencies
├── postcss.config.js            # PostCSS config
├── tailwind.config.js           # Tailwind config
└── tsconfig.json                # TypeScript config
```

## API Integration

The frontend connects to the FastAPI backend running on port 8000:

### Endpoints Used:
- `GET /health` - System health check
- `GET /api/v1/stats` - Knowledge graph statistics
- `POST /api/v1/detect` - Anomaly detection
- `POST /api/v1/diagnose` - Complete fault diagnosis

## State Management

Using Zustand for global state:

```typescript
interface TelemetryState {
  isConnected: boolean
  isLoading: boolean
  error: string | null
  telemetryData: TelemetryData[]
  anomalyDetection: AnomalyDetection | null
  rootCauses: RootCause[]
  diagnosis: Diagnosis | null
  systemStatus: any
  kgStats: KnowledgeGraphStats | null
  
  // Actions
  fetchSystemStatus()
  fetchKnowledgeGraphStats()
  detectAnomaly()
  diagnoseFault()
  simulateTelemetry()
}
```

## Styling

Dark theme with blue accents matching satellite/space aesthetic:
- Background: `#0a0a0a` (near black)
- Primary: Blue (`#3b82f6`)
- Secondary: Dark blue-gray
- Cards: Dark with subtle borders

## Development

### Key Commands
```bash
npm run dev          # Start dev server
npm run build        # Production build
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # TypeScript type checking
```

### Adding New Components
1. Create component in `src/components/`
2. Use TypeScript for type safety
3. Import and use Zustand store for state
4. Style with Tailwind classes

## Troubleshooting

### Backend Connection Issues
- Ensure backend is running: `uvicorn src.api.main:app --reload`
- Check API URL in `.env.local`
- Verify CORS settings in backend

### Build Errors
- Run `npm run type-check` to find TypeScript issues
- Clear `.next` folder and rebuild
- Verify all dependencies are installed

### Styling Issues
- Ensure PostCSS config exists
- Run `npm install` to reinstall Tailwind
- Check globals.css is imported in layout.tsx

## Future Enhancements
- [ ] WebSocket for real-time telemetry streaming
- [ ] Historical data visualization with time-series charts
- [ ] Interactive knowledge graph visualization (D3.js/Cytoscape)
- [ ] Alert system with notifications
- [ ] User authentication and roles
- [ ] Export reports functionality
- [ ] Mobile responsive improvements

## License
Part of the Satellite Telemetry Fault Diagnosis System
