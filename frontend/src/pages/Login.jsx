import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Box,
  TextField,
  Button,
  Typography,
  Paper,
  Alert,
  CircularProgress,
  InputAdornment,
  IconButton
} from '@mui/material'
import { Visibility, VisibilityOff, Security } from '@mui/icons-material'
import api from '../services/api'

function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [firstBoot, setFirstBoot] = useState(null)

  useEffect(() => {
    api.get('/auth/first-boot')
      .then(res => {
        if (res.data.first_boot) {
          setFirstBoot(res.data)
        }
      })
      .catch(() => {})
  }, [])

  const dismissFirstBoot = () => {
    api.post('/auth/first-boot/dismiss').catch(() => {})
    setFirstBoot(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // JSON login request
      const response = await api.post('/auth/login', {
        username,
        password
      })

      // Store token and user info
      const { access_token, token_type, user } = response.data
      localStorage.setItem('token', access_token)
      localStorage.setItem('tokenType', token_type || 'bearer')
      if (user) {
        localStorage.setItem('user', JSON.stringify(user))
      }

      // Redirect to dashboard
      navigate('/')
    } catch (err) {
      console.error('Login error:', err)
      if (err.response?.status === 401) {
        setError('Invalid username or password')
      } else if (err.response?.status === 403) {
        setError('Account is disabled or locked')
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Login failed. Please check your connection and try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
            <Security sx={{ fontSize: 48, color: 'primary.main' }} />
          </Box>
          <Typography component="h1" variant="h4" align="center" gutterBottom>
            Pentesting Platform
          </Typography>
          <Typography component="h2" variant="body1" align="center" color="text.secondary" gutterBottom>
            Automated Security Assessment
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mt: 2, mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="username"
              label="Username"
              name="username"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type={showPassword ? 'text' : 'password'}
              id="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2, py: 1.5 }}
              disabled={loading || !username || !password}
            >
              {loading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                'Sign In'
              )}
            </Button>
          </Box>

          {firstBoot && (
            <Alert
              severity="info"
              sx={{ mt: 2 }}
              action={
                <Button color="inherit" size="small" onClick={dismissFirstBoot}>
                  Got it
                </Button>
              }
            >
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                First Boot — Your Admin Credentials
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                Username: <strong>{firstBoot.username}</strong><br />
                Password: <strong>{firstBoot.password}</strong>
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                Change this password after first login. Click "Got it" to dismiss permanently.
              </Typography>
            </Alert>
          )}
        </Paper>
      </Box>
    </Container>
  )
}

export default Login
