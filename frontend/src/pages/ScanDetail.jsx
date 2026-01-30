import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Alert,
  Tabs,
  Tab,
  Card,
  CardContent,
  Divider,
  IconButton,
  Tooltip,
  CircularProgress
} from '@mui/material'
import {
  ArrowBack,
  Refresh,
  Download,
  Stop,
  PlayArrow,
  BugReport,
  Security,
  Computer,
  Schedule,
  CheckCircle,
  Error as ErrorIcon,
  Warning,
  Info
} from '@mui/icons-material'
import api from '../services/api'

const statusColors = {
  pending: 'default',
  running: 'primary',
  completed: 'success',
  failed: 'error',
  cancelled: 'warning'
}

const severityColors = {
  critical: '#d32f2f',
  high: '#f57c00',
  medium: '#fbc02d',
  low: '#4caf50',
  info: '#2196f3'
}

const severityIcons = {
  critical: <ErrorIcon sx={{ color: severityColors.critical }} />,
  high: <Warning sx={{ color: severityColors.high }} />,
  medium: <Warning sx={{ color: severityColors.medium }} />,
  low: <Info sx={{ color: severityColors.low }} />,
  info: <Info sx={{ color: severityColors.info }} />
}

function TabPanel({ children, value, index, ...other }) {
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

function ScanDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [scan, setScan] = useState(null)
  const [findings, setFindings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tabValue, setTabValue] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const [liveLogs, setLiveLogs] = useState('')
  const terminalRef = React.useRef(null)

  const fetchScan = async () => {
    try {
      const [scanRes, findingsRes] = await Promise.all([
        api.get(`/scans/${id}`),
        api.get(`/findings?scan_id=${id}`)
      ])
      setScan(scanRes.data)
      setFindings(findingsRes.data.items || findingsRes.data || [])
      setError('')
    } catch (err) {
      console.error('Failed to load scan:', err)
      setError('Failed to load scan details')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const fetchLogs = async () => {
    try {
      const logsRes = await api.get(`/scans/${id}/logs`)
      if (logsRes.data.logs) {
        setLiveLogs(logsRes.data.logs)
        // Auto-scroll to bottom
        if (terminalRef.current) {
          terminalRef.current.scrollTop = terminalRef.current.scrollHeight
        }
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    }
  }

  useEffect(() => {
    fetchScan()
    fetchLogs()

    // Auto-refresh for running scans
    let scanInterval
    let logsInterval
    if (scan?.status === 'running') {
      scanInterval = setInterval(fetchScan, 5000)
      logsInterval = setInterval(fetchLogs, 2000)  // Poll logs more frequently
    }
    return () => {
      clearInterval(scanInterval)
      clearInterval(logsInterval)
    }
  }, [id, scan?.status])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchScan()
  }

  const handleCancel = async () => {
    try {
      await api.post(`/scans/${id}/cancel`)
      fetchScan()
    } catch (err) {
      setError('Failed to cancel scan')
    }
  }

  const handleDownloadReport = async (format = 'pdf') => {
    try {
      const response = await api.post('/reports/generate', {
        scan_id: id,
        report_type: 'technical',
        format: format
      })
      // Handle download
      if (response.data.file_path) {
        window.open(`/api/v1/reports/${response.data.id}/download`, '_blank')
      }
    } catch (err) {
      setError('Failed to generate report')
    }
  }

  const getSeverityStats = () => {
    const stats = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
    findings.forEach(f => {
      const sev = f.severity?.toLowerCase() || 'info'
      if (stats[sev] !== undefined) stats[sev]++
    })
    return stats
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

  if (error && !scan) {
    return (
      <Container maxWidth="xl">
        <Alert severity="error" sx={{ mt: 4 }}>{error}</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/scans')} sx={{ mt: 2 }}>
          Back to Scans
        </Button>
      </Container>
    )
  }

  const severityStats = getSeverityStats()

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 2 }}>
          <IconButton onClick={() => navigate('/scans')}>
            <ArrowBack />
          </IconButton>
          <Typography variant="h4" sx={{ flexGrow: 1 }}>
            {scan?.name || 'Scan Details'}
          </Typography>
          <Chip
            label={scan?.status?.toUpperCase()}
            color={statusColors[scan?.status] || 'default'}
          />
          <Tooltip title="Refresh">
            <IconButton onClick={handleRefresh} disabled={refreshing}>
              <Refresh className={refreshing ? 'spinning' : ''} />
            </IconButton>
          </Tooltip>
          {scan?.status === 'running' && (
            <Button variant="outlined" color="error" startIcon={<Stop />} onClick={handleCancel}>
              Cancel
            </Button>
          )}
          {scan?.status === 'completed' && (
            <Button variant="contained" startIcon={<Download />} onClick={() => handleDownloadReport()}>
              Download Report
            </Button>
          )}
        </Box>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {/* Progress bar for running scans */}
        {scan?.status === 'running' && (
          <Box sx={{ mb: 3 }}>
            <LinearProgress
              variant="determinate"
              value={scan.progress_percent || 0}
              sx={{ height: 10, borderRadius: 5 }}
            />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Progress: {scan.progress_percent || 0}%
            </Typography>
          </Box>
        )}

        {/* Summary Cards */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Computer color="primary" />
                  <Typography color="text.secondary">Target</Typography>
                </Box>
                <Typography variant="h6" sx={{ mt: 1 }}>
                  {scan?.targets?.join(', ') || 'N/A'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Security color="primary" />
                  <Typography color="text.secondary">Scan Type</Typography>
                </Box>
                <Typography variant="h6" sx={{ mt: 1 }}>
                  {scan?.scan_type?.replace('_', ' ').toUpperCase() || 'N/A'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <BugReport color="primary" />
                  <Typography color="text.secondary">Findings</Typography>
                </Box>
                <Typography variant="h6" sx={{ mt: 1 }}>
                  {findings.length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Schedule color="primary" />
                  <Typography color="text.secondary">Duration</Typography>
                </Box>
                <Typography variant="h6" sx={{ mt: 1 }}>
                  {scan?.duration_seconds ? `${Math.floor(scan.duration_seconds / 60)}m ${scan.duration_seconds % 60}s` : 'N/A'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Severity Distribution */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>Findings by Severity</Typography>
          <Grid container spacing={2}>
            {Object.entries(severityStats).map(([severity, count]) => (
              <Grid item key={severity}>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    px: 2,
                    py: 1,
                    borderRadius: 1,
                    bgcolor: `${severityColors[severity]}20`
                  }}
                >
                  {severityIcons[severity]}
                  <Typography>
                    {severity.charAt(0).toUpperCase() + severity.slice(1)}: {count}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </Paper>

        {/* Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
            <Tab label="Findings" />
            <Tab label="Scan Details" />
            <Tab label="Raw Output" />
          </Tabs>
          <Divider />

          {/* Findings Tab */}
          <TabPanel value={tabValue} index={0}>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Severity</TableCell>
                    <TableCell>Title</TableCell>
                    <TableCell>Target</TableCell>
                    <TableCell>Port</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {findings.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        <Typography color="text.secondary">
                          {scan?.status === 'running' ? 'Scan in progress...' : 'No findings'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    findings.map((finding) => (
                      <TableRow key={finding.id} hover>
                        <TableCell>
                          <Chip
                            label={finding.severity?.toUpperCase()}
                            size="small"
                            sx={{
                              bgcolor: severityColors[finding.severity?.toLowerCase()] || '#grey',
                              color: 'white'
                            }}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {finding.title}
                          </Typography>
                        </TableCell>
                        <TableCell>{finding.target || finding.host || 'N/A'}</TableCell>
                        <TableCell>{finding.port || 'N/A'}</TableCell>
                        <TableCell>
                          <Chip
                            label={finding.status || 'open'}
                            size="small"
                            color={finding.status === 'fixed' ? 'success' : 'default'}
                          />
                        </TableCell>
                        <TableCell>
                          <Button
                            size="small"
                            onClick={() => navigate(`/findings/${finding.id}`)}
                          >
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </TabPanel>

          {/* Scan Details Tab */}
          <TabPanel value={tabValue} index={1}>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">Scan ID</Typography>
                <Typography variant="body1" gutterBottom>{scan?.id}</Typography>

                <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>Created At</Typography>
                <Typography variant="body1" gutterBottom>
                  {scan?.created_at ? new Date(scan.created_at).toLocaleString() : 'N/A'}
                </Typography>

                <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>Started At</Typography>
                <Typography variant="body1" gutterBottom>
                  {scan?.started_at ? new Date(scan.started_at).toLocaleString() : 'N/A'}
                </Typography>

                <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>Completed At</Typography>
                <Typography variant="body1" gutterBottom>
                  {scan?.completed_at ? new Date(scan.completed_at).toLocaleString() : 'N/A'}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">Targets</Typography>
                <Typography variant="body1" gutterBottom>
                  {scan?.targets?.join(', ') || 'N/A'}
                </Typography>

                <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>Tools Used</Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                  {(scan?.tools_used || scan?.scan_config?.tools || ['nmap']).map((tool, i) => (
                    <Chip key={i} label={tool} size="small" />
                  ))}
                </Box>

                <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>Configuration</Typography>
                <Paper variant="outlined" sx={{ p: 1, mt: 1, bgcolor: 'grey.50' }}>
                  <pre style={{ margin: 0, fontSize: '0.75rem', overflow: 'auto' }}>
                    {JSON.stringify(scan?.scan_config || {}, null, 2)}
                  </pre>
                </Paper>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Raw Output / Terminal Tab */}
          <TabPanel value={tabValue} index={2}>
            {scan?.status === 'running' && (
              <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <CircularProgress size={16} />
                <Typography variant="body2" color="primary">
                  Live output - auto-refreshing every 2 seconds
                </Typography>
              </Box>
            )}
            <Paper
              ref={terminalRef}
              variant="outlined"
              sx={{
                p: 2,
                bgcolor: '#0d1117',
                color: '#c9d1d9',
                maxHeight: 500,
                overflow: 'auto',
                fontFamily: '"Fira Code", "Consolas", monospace',
                border: '1px solid #30363d'
              }}
            >
              {scan?.status === 'running' || liveLogs ? (
                <pre style={{
                  margin: 0,
                  fontFamily: 'inherit',
                  fontSize: '0.85rem',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {liveLogs || 'Waiting for output...'}
                  {scan?.status === 'running' && (
                    <span style={{ animation: 'blink 1s infinite' }}>▌</span>
                  )}
                </pre>
              ) : (
                <pre style={{ margin: 0, fontFamily: 'inherit', fontSize: '0.85rem' }}>
                  {scan?.results?.raw_output ||
                   JSON.stringify(scan?.results || {}, null, 2) ||
                   'No output available'}
                </pre>
              )}
            </Paper>
            <style>{`
              @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0; }
              }
            `}</style>
          </TabPanel>
        </Paper>
      </Box>
    </Container>
  )
}

export default ScanDetail
