import React, { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  Button,
} from '@mui/material'
import api from '../services/api'

function Findings() {
  const [findings, setFindings] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    scan_id: '',
    severity: '',
    status: '',
  })

  useEffect(() => {
    loadFindings()
  }, [filters])

  const loadFindings = async () => {
    try {
      const params = new URLSearchParams()
      if (filters.scan_id) params.append('scan_id', filters.scan_id)
      if (filters.severity) params.append('severity', filters.severity)
      if (filters.status) params.append('status', filters.status)

      const response = await api.get(`/findings?${params.toString()}`)
      setFindings(response.data)
      setLoading(false)
    } catch (error) {
      console.error('Failed to load findings:', error)
      setLoading(false)
    }
  }

  const getSeverityColor = (severity) => {
    const colors = {
      critical: 'error',
      high: 'error',
      medium: 'warning',
      low: 'info',
      info: 'default',
    }
    return colors[severity] || 'default'
  }

  const getStatusColor = (status) => {
    const colors = {
      new: 'default',
      confirmed: 'primary',
      false_positive: 'secondary',
      remediated: 'success',
      in_progress: 'warning',
    }
    return colors[status] || 'default'
  }

  if (loading) {
    return (
      <Container>
        <Typography>Loading findings...</Typography>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Findings
        </Typography>

        <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <TextField
            label="Scan ID"
            value={filters.scan_id}
            onChange={(e) => setFilters({ ...filters, scan_id: e.target.value })}
            size="small"
          />
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Severity</InputLabel>
            <Select
              value={filters.severity}
              onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
              label="Severity"
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="critical">Critical</MenuItem>
              <MenuItem value="high">High</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="low">Low</MenuItem>
              <MenuItem value="info">Info</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              label="Status"
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="new">New</MenuItem>
              <MenuItem value="confirmed">Confirmed</MenuItem>
              <MenuItem value="false_positive">False Positive</MenuItem>
              <MenuItem value="remediated">Remediated</MenuItem>
            </Select>
          </FormControl>
          <Button variant="outlined" onClick={loadFindings}>
            Refresh
          </Button>
        </Box>

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Severity</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Target</TableCell>
                <TableCell>Port/Service</TableCell>
                <TableCell>CVE</TableCell>
                <TableCell>Created</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {findings.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    No findings found
                  </TableCell>
                </TableRow>
              ) : (
                findings.map((finding) => (
                  <TableRow key={finding.id} hover>
                    <TableCell>{finding.title}</TableCell>
                    <TableCell>
                      <Chip
                        label={finding.severity}
                        color={getSeverityColor(finding.severity)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={finding.status}
                        color={getStatusColor(finding.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{finding.target}</TableCell>
                    <TableCell>
                      {finding.port && `${finding.port}`}
                      {finding.service && `/${finding.service}`}
                    </TableCell>
                    <TableCell>{finding.cve_id || '-'}</TableCell>
                    <TableCell>
                      {new Date(finding.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Container>
  )
}

export default Findings
