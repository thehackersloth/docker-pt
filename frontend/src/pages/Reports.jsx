import React, { useState, useEffect } from 'react'
import {
  Container,
  Box,
  Paper,
  Typography,
  Grid,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Alert,
  CircularProgress,
  Tooltip,
  FormControlLabel,
  Checkbox
} from '@mui/material'
import {
  Add,
  Download,
  Delete,
  Refresh,
  PictureAsPdf,
  Code,
  Description,
  Email,
  CameraAlt
} from '@mui/icons-material'
import api from '../services/api'

const formatIcons = {
  pdf: <PictureAsPdf />,
  json: <Code />,
  html: <Description />,
  csv: <Description />,
  word: <Description />
}

const reportTypes = [
  { value: 'executive', label: 'Executive Summary' },
  { value: 'technical', label: 'Technical Report' },
  { value: 'compliance', label: 'Compliance Report' },
  { value: 'full', label: 'Full Report' }
]

const reportFormats = [
  { value: 'pdf', label: 'PDF' },
  { value: 'html', label: 'HTML' },
  { value: 'json', label: 'JSON' },
  { value: 'csv', label: 'CSV' }
]

function Reports() {
  const [reports, setReports] = useState([])
  const [scans, setScans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [newReport, setNewReport] = useState({
    scan_id: '',
    report_type: 'technical',
    format: 'pdf',
    name: '',
    capture_screenshots: true
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [reportsRes, scansRes] = await Promise.all([
        api.get('/reports'),
        api.get('/scans?status=completed&limit=50')
      ])
      setReports(reportsRes.data.items || reportsRes.data || [])
      setScans(scansRes.data.items || scansRes.data || [])
      setError('')
    } catch (err) {
      console.error('Failed to load data:', err)
      setError('Failed to load reports')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    if (!newReport.scan_id) {
      setError('Please select a scan')
      return
    }

    setGenerating(true)
    try {
      const response = await api.post('/reports/generate', {
        scan_id: newReport.scan_id,
        report_type: newReport.report_type,
        format: newReport.format,
        name: newReport.name || `Report - ${new Date().toLocaleDateString()}`,
        capture_screenshots: newReport.capture_screenshots
      })

      setReports([response.data, ...reports])
      setDialogOpen(false)
      setNewReport({
        scan_id: '',
        report_type: 'technical',
        format: 'pdf',
        name: '',
        capture_screenshots: true
      })
    } catch (err) {
      setError('Failed to generate report')
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = async (report) => {
    try {
      const response = await api.get(`/reports/${report.id}/download`, {
        responseType: 'blob'
      })

      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${report.name}.${report.format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err) {
      setError('Failed to download report')
    }
  }

  const handleDelete = async (reportId) => {
    if (!window.confirm('Are you sure you want to delete this report?')) return

    try {
      await api.delete(`/reports/${reportId}`)
      setReports(reports.filter(r => r.id !== reportId))
    } catch (err) {
      setError('Failed to delete report')
    }
  }

  const handleEmailReport = async (report) => {
    const email = window.prompt('Enter email address to send report:')
    if (!email) return

    try {
      await api.post(`/reports/${report.id}/email`, { email })
      alert('Report sent successfully!')
    } catch (err) {
      setError('Failed to send report')
    }
  }

  if (loading) {
    return (
      <Container maxWidth="xl">
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      </Container>
    )
  }

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4">Reports</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton onClick={fetchData}>
              <Refresh />
            </IconButton>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setDialogOpen(true)}
            >
              Generate Report
            </Button>
          </Box>
        </Box>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {/* Reports Table */}
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Format</TableCell>
                <TableCell>Scan</TableCell>
                <TableCell>Generated</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {reports.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <Typography color="text.secondary">No reports generated yet</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                reports.map((report) => (
                  <TableRow key={report.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {formatIcons[report.format] || <Description />}
                        {report.name}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={report.report_type?.replace('_', ' ').toUpperCase()}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip label={report.format?.toUpperCase()} size="small" />
                    </TableCell>
                    <TableCell>{report.scan_id?.substring(0, 8)}...</TableCell>
                    <TableCell>
                      {report.generated_at
                        ? new Date(report.generated_at).toLocaleString()
                        : 'N/A'}
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Download">
                        <IconButton onClick={() => handleDownload(report)} size="small">
                          <Download />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Email">
                        <IconButton onClick={() => handleEmailReport(report)} size="small">
                          <Email />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton onClick={() => handleDelete(report.id)} size="small" color="error">
                          <Delete />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* Generate Report Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Generate Report</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth required>
                <InputLabel>Select Scan</InputLabel>
                <Select
                  value={newReport.scan_id}
                  onChange={(e) => setNewReport({ ...newReport, scan_id: e.target.value })}
                  label="Select Scan"
                >
                  {scans.map((scan) => (
                    <MenuItem key={scan.id} value={scan.id}>
                      {scan.name} - {scan.targets?.join(', ')}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Report Name"
                value={newReport.name}
                onChange={(e) => setNewReport({ ...newReport, name: e.target.value })}
                placeholder="Leave empty for auto-generated name"
              />
            </Grid>
            <Grid item xs={6}>
              <FormControl fullWidth>
                <InputLabel>Report Type</InputLabel>
                <Select
                  value={newReport.report_type}
                  onChange={(e) => setNewReport({ ...newReport, report_type: e.target.value })}
                  label="Report Type"
                >
                  {reportTypes.map((type) => (
                    <MenuItem key={type.value} value={type.value}>{type.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={6}>
              <FormControl fullWidth>
                <InputLabel>Format</InputLabel>
                <Select
                  value={newReport.format}
                  onChange={(e) => setNewReport({ ...newReport, format: e.target.value })}
                  label="Format"
                >
                  {reportFormats.map((format) => (
                    <MenuItem key={format.value} value={format.value}>{format.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={newReport.capture_screenshots}
                    onChange={(e) => setNewReport({ ...newReport, capture_screenshots: e.target.checked })}
                    icon={<CameraAlt />}
                    checkedIcon={<CameraAlt color="primary" />}
                  />
                }
                label="Capture screenshots (web pages + terminal output for PDF/HTML reports)"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleGenerateReport}
            disabled={generating || !newReport.scan_id}
          >
            {generating ? <CircularProgress size={24} /> : 'Generate'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default Reports
