import React, { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  Paper,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import {
  Security as SecurityIcon,
  BugReport as FindingsIcon,
  Computer as AssetIcon,
  TrendingUp as TrendingIcon,
} from '@mui/icons-material'
import api from '../services/api'

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const loadStats = async () => {
    try {
      const response = await api.get('/dashboard/stats')
      setStats(response.data)
      setLoading(false)
    } catch (error) {
      console.error('Failed to load dashboard stats:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Container>
        <LinearProgress />
        <Typography>Loading dashboard...</Typography>
      </Container>
    )
  }

  if (!stats) {
    return (
      <Container>
        <Typography>Failed to load dashboard</Typography>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Dashboard
        </Typography>

        <Grid container spacing={3}>
          {/* Scan Statistics */}
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <SecurityIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6">Scans</Typography>
                </Box>
                <Typography variant="h4">{stats.total_scans}</Typography>
                <Typography color="text.secondary">
                  {stats.running_scans} running, {stats.completed_scans} completed
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Findings Statistics */}
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <FindingsIcon sx={{ mr: 1, color: 'error.main' }} />
                  <Typography variant="h6">Findings</Typography>
                </Box>
                <Typography variant="h4">{stats.total_findings}</Typography>
                <Typography color="text.secondary">
                  {stats.critical_findings} critical, {stats.high_findings} high
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Assets Statistics */}
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AssetIcon sx={{ mr: 1, color: 'success.main' }} />
                  <Typography variant="h6">Assets</Typography>
                </Box>
                <Typography variant="h4">{stats.total_assets}</Typography>
                <Typography color="text.secondary">Discovered assets</Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Severity Breakdown */}
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <TrendingIcon sx={{ mr: 1, color: 'warning.main' }} />
                  <Typography variant="h6">Severity</Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="error">
                    Critical: {stats.critical_findings}
                  </Typography>
                  <Typography variant="body2" color="error.light">
                    High: {stats.high_findings}
                  </Typography>
                  <Typography variant="body2" color="warning.main">
                    Medium: {stats.medium_findings}
                  </Typography>
                  <Typography variant="body2" color="info.main">
                    Low: {stats.low_findings}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Recent Scans */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Recent Scans
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Findings</TableCell>
                        <TableCell>Created</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {stats.recent_scans.map((scan) => (
                        <TableRow key={scan.id}>
                          <TableCell>{scan.name}</TableCell>
                          <TableCell>{scan.status}</TableCell>
                          <TableCell>{scan.findings_count}</TableCell>
                          <TableCell>
                            {new Date(scan.created_at).toLocaleDateString()}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>

          {/* Top Vulnerabilities */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Top Vulnerabilities
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>CVE</TableCell>
                        <TableCell align="right">Count</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {stats.top_vulnerabilities.map((vuln, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{vuln.cve_id}</TableCell>
                          <TableCell align="right">{vuln.count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Container>
  )
}

export default Dashboard
