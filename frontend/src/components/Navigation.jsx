import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  Security as SecurityIcon,
  Settings as SettingsIcon,
  BugReport as FindingsIcon,
  AccountTree as BloodHoundIcon,
  Schedule as ScheduleIcon,
  MenuBook as MethodologyIcon,
  Assessment as ReportsIcon,
  Logout as LogoutIcon,
  Dns as AssetsIcon,
  Business as ProjectsIcon,
} from '@mui/icons-material'

function Navigation() {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    { path: '/', label: 'Dashboard', icon: <DashboardIcon /> },
    { path: '/projects', label: 'Projects', icon: <ProjectsIcon /> },
    { path: '/scans', label: 'Scans', icon: <SecurityIcon /> },
    { path: '/assets', label: 'Assets', icon: <AssetsIcon /> },
    { path: '/findings', label: 'Findings', icon: <FindingsIcon /> },
    { path: '/reports', label: 'Reports', icon: <ReportsIcon /> },
    { path: '/bloodhound', label: 'BloodHound', icon: <BloodHoundIcon /> },
    { path: '/schedules', label: 'Schedules', icon: <ScheduleIcon /> },
    { path: '/methodology', label: 'Methodology', icon: <MethodologyIcon /> },
    { path: '/configuration', label: 'Config', icon: <SettingsIcon /> },
  ]

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('tokenType')
    localStorage.removeItem('user')
    navigate('/login')
  }

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ mr: 4 }}>
          Pentest Platform
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5, flexGrow: 1 }}>
          {menuItems.map((item) => (
            <Button
              key={item.path}
              color="inherit"
              size="small"
              startIcon={item.icon}
              onClick={() => navigate(item.path)}
              variant={location.pathname === item.path ? 'outlined' : 'text'}
              sx={{ minWidth: 'auto', px: 1.5 }}
            >
              {item.label}
            </Button>
          ))}
        </Box>
        <Tooltip title="Logout">
          <IconButton color="inherit" onClick={handleLogout}>
            <LogoutIcon />
          </IconButton>
        </Tooltip>
      </Toolbar>
    </AppBar>
  )
}

export default Navigation
