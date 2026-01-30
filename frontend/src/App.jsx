import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import Navigation from './components/Navigation'
import Dashboard from './pages/Dashboard'
import Scans from './pages/Scans'
import ScanDetail from './pages/ScanDetail'
import Login from './pages/Login'
import Configuration from './pages/Configuration'
import Findings from './pages/Findings'
import FindingDetail from './pages/FindingDetail'
import BloodHound from './pages/BloodHound'
import ScheduleHistory from './pages/ScheduleHistory'
import Methodology from './pages/Methodology'
import Reports from './pages/Reports'
import Assets from './pages/Assets'
import Projects from './pages/Projects'

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
})

// Simple auth check
const isAuthenticated = () => {
  return !!localStorage.getItem('token')
}

// Protected route wrapper
const ProtectedRoute = ({ children }) => {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return children
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={
            <ProtectedRoute>
              <Navigation />
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/projects" element={<Projects />} />
                <Route path="/scans" element={<Scans />} />
                <Route path="/scans/:id" element={<ScanDetail />} />
                <Route path="/assets" element={<Assets />} />
                <Route path="/findings" element={<Findings />} />
                <Route path="/findings/:id" element={<FindingDetail />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/bloodhound" element={<BloodHound />} />
                <Route path="/schedules" element={<ScheduleHistory />} />
                <Route path="/methodology" element={<Methodology />} />
                <Route path="/configuration" element={<Configuration />} />
              </Routes>
            </ProtectedRoute>
          } />
        </Routes>
      </Router>
    </ThemeProvider>
  )
}

export default App
