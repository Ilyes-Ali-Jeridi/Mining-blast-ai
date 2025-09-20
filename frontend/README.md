# Drill-Blast System Frontend

This is the React TypeScript frontend for the Automated Drill-and-Blast System.

## Technology Stack

- **React 19** with TypeScript
- **Vite** for build tooling and development server
- **Material-UI (MUI)** for UI components
- **React Router** for client-side routing
- **Redux Toolkit** for state management
- **Leaflet** for interactive maps
- **Chart.js** for data visualization
- **Axios** for API communication

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- The backend API server running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── components/          # Reusable UI components
│   └── Layout/         # Layout components
├── pages/              # Page components
├── services/           # API services
├── store/              # Redux store and slices
├── types/              # TypeScript type definitions
├── App.tsx             # Main application component
└── main.tsx           # Application entry point
```

## Features Implemented

### Task 8.1: React Application Setup ✅

- ✅ React project with Vite build system
- ✅ TypeScript configuration and type definitions
- ✅ React Router for routing
- ✅ Redux Toolkit for state management
- ✅ Material-UI component library
- ✅ Basic application layout and navigation
- ✅ API service layer with Axios
- ✅ Environment configuration

### Next Steps

The following tasks will be implemented in subsequent development phases:

- **Task 8.2**: Input forms and validation
- **Task 8.3**: Interactive blast plan visualization with Leaflet
- **Task 8.4**: Optimization interface and progress tracking
- **Task 8.5**: Results review and export interface

## Development Guidelines

1. **Component Structure**: Use functional components with hooks
2. **State Management**: Use Redux Toolkit for global state, local state for component-specific data
3. **Styling**: Use MUI's sx prop and theme system
4. **API Calls**: Use the centralized API service in `src/services/api.ts`
5. **Type Safety**: Define proper TypeScript interfaces in `src/types/`

## API Integration

The frontend is configured to communicate with the backend API:

- **Base URL**: `http://localhost:8000/api`
- **WebSocket**: `ws://localhost:8000` for real-time updates
- **Authentication**: JWT tokens stored in localStorage

## Environment Variables

- `VITE_API_BASE_URL`: Backend API base URL
- `VITE_WS_BASE_URL`: WebSocket base URL
- `VITE_APP_NAME`: Application name
- `VITE_APP_VERSION`: Application version