# Sealant Detection System - Desktop Application

This is a desktop application built with Electron and React for a sealant detection system. The application includes authentication for workers and admins, and displays camera feeds with real-time status indicators.

## 🚀 Getting Started with Electron

### Prerequisites
- Node.js (v16 or later)
- npm (v7 or later) or Yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repository-url>
   cd <project-directory>
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

### Development

To run the application in development mode:
```bash
npm run dev
```
This will start both the Vite development server and the Electron app.

### Building for Production

To create a production build:

1. **Build the application**
   ```bash
   npm run build
   ```

2. **Package the application**
   - For Windows:
     ```bash
     npm run electron:build -- --win
     ```
   - For macOS:
     ```bash
     npm run electron:build -- --mac
     ```
   - For Linux:
     ```bash
     npm run electron:build -- --linux
     ```

The built application will be available in the `release` directory.

---

# Sealant Detection System - Frontend Prototype

This is a React-based frontend prototype for a sealant detection application. The application includes authentication for workers and admins, and displays camera feeds with real-time status indicators.

## Features

- **Authentication System**: Login with role-based access (Worker/Admin)
- **Worker Dashboard**: Displays 4 camera feeds (2 frontend, 2 backend) with status indicators
- **Real-time Status**: Green "Good" for correct sealant, Red "NG" for missing sealant
- **Admin Dashboard**: Reports & Analytics and Model Retraining controls
- **Modern UI**: Clean, responsive design with smooth animations

## Project Structure

```
src/
├── components/
│   ├── CameraFeed.jsx          # Camera feed component with status
│   └── CameraFeed.css
├── pages/
│   ├── Login.jsx               # Login page with Toyota branding
│   ├── Login.css
│   ├── WorkerDashboard.jsx     # Worker dashboard with camera feeds
│   ├── WorkerDashboard.css
│   ├── AdminDashboard.jsx      # Admin dashboard
│   └── AdminDashboard.css
├── App.jsx                      # Main app with routing
├── App.css
├── main.jsx                     # Entry point
└── index.css                    # Global styles with Toyota colors
```

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
# or
npm run dev
```

3. Open your browser and navigate to `http://localhost:3000`

### Login Credentials

For prototype purposes, use any credentials:
- **Username**: Any value
- **Password**: Any value
- **Role**: Select Worker or Admin

## Page Flow

1. **Login Page** (`/login`)
   - Toyota logo prominently displayed
   - Role selection (Worker/Admin)
   - Username and password input
   - Toyota red gradient background
   - Prototype accepts any credentials

2. **Worker Dashboard** (`/worker-dashboard`)
   - Toyota logo in header with "Corolla Production" subtitle
   - 4 camera feeds (2 frontend, 2 backend cameras)
   - Real-time status indicators (Green for Good, Red for NG)
   - System summary showing good/NG cases count
   - Auto-updates status every 5 seconds (demo)

3. **Admin Dashboard** (`/admin-dashboard`)
   - Toyota branding in header
   - Reports & Analytics panel
   - Model Retraining panel
   - Admin management controls

## Backend Integration (Future)

The frontend is designed to integrate with a Python backend API. You'll need to:

1. Replace camera placeholders with actual video streams
2. Connect to backend API endpoints:
   - POST `/api/login` - Authentication
   - GET `/api/cameras/status` - Camera status data
   - WebSocket or SSE for real-time updates

3. Expected API Response Format:
```json
{
  "frontend1": "good",
  "frontend2": "good",
  "backend1": "ng",
  "backend2": "good"
}
```

## Building for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` folder.

## Technologies Used

- **React 18** - UI framework
- **React Router** - Routing and navigation
- **Vite** - Build tool and dev server
- **CSS3** - Styling with Toyota brand colors

## Next Steps

1. **Backend Integration**: Connect to Python API
2. **Real Camera Feeds**: Implement actual video streaming
3. **Authentication**: Add proper backend authentication
4. **Database**: Store worker data and production records
5. **Real-time Updates**: Implement WebSocket for live status updates
6. **Alert System**: Add notifications for NG cases
7. **Historical Data**: Track and display historical production data

## Notes

- This is a prototype/frontend-only implementation
- Camera feeds are currently placeholders
- Authentication is client-side only (prototype)
- Status changes are simulated with random intervals

