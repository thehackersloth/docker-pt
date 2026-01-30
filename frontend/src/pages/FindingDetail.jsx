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
  Alert,
  Divider,
  IconButton,
  Card,
  CardContent,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Link
} from '@mui/material'
import {
  ArrowBack,
  Edit,
  Save,
  Cancel,
  BugReport,
  Security,
  Computer,
  Link as LinkIcon,
  Code,
  Lightbulb
} from '@mui/icons-material'
import api from '../services/api'

const severityColors = {
  critical: '#d32f2f',
  high: '#f57c00',
  medium: '#fbc02d',
  low: '#4caf50',
  info: '#2196f3'
}

const statusOptions = ['open', 'confirmed', 'false_positive', 'fixed', 'accepted_risk']

function FindingDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [finding, setFinding] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [editedFinding, setEditedFinding] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchFinding()
  }, [id])

  const fetchFinding = async () => {
    try {
      const response = await api.get(`/findings/${id}`)
      setFinding(response.data)
      setEditedFinding(response.data)
      setError('')
    } catch (err) {
      console.error('Failed to load finding:', err)
      setError('Failed to load finding details')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.put(`/findings/${id}`, {
        status: editedFinding.status,
        notes: editedFinding.notes
      })
      setFinding({ ...finding, ...editedFinding })
      setEditing(false)
    } catch (err) {
      setError('Failed to update finding')
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setEditedFinding(finding)
    setEditing(false)
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

  if (error && !finding) {
    return (
      <Container maxWidth="xl">
        <Alert severity="error" sx={{ mt: 4 }}>{error}</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Go Back
        </Button>
      </Container>
    )
  }

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 2 }}>
          <IconButton onClick={() => navigate(-1)}>
            <ArrowBack />
          </IconButton>
          <BugReport sx={{ fontSize: 32, color: severityColors[finding?.severity?.toLowerCase()] }} />
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h5">
              {finding?.title}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Finding ID: {finding?.id}
            </Typography>
          </Box>
          <Chip
            label={finding?.severity?.toUpperCase()}
            sx={{
              bgcolor: severityColors[finding?.severity?.toLowerCase()],
              color: 'white',
              fontWeight: 'bold'
            }}
          />
          {!editing ? (
            <Button variant="outlined" startIcon={<Edit />} onClick={() => setEditing(true)}>
              Edit
            </Button>
          ) : (
            <>
              <Button
                variant="contained"
                startIcon={<Save />}
                onClick={handleSave}
                disabled={saving}
              >
                Save
              </Button>
              <Button variant="outlined" startIcon={<Cancel />} onClick={handleCancel}>
                Cancel
              </Button>
            </>
          )}
        </Box>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Grid container spacing={3}>
          {/* Main Content */}
          <Grid item xs={12} md={8}>
            {/* Description */}
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                <Security sx={{ mr: 1, verticalAlign: 'middle' }} />
                Description
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                {finding?.description || 'No description available'}
              </Typography>
            </Paper>

            {/* Evidence / Proof */}
            {finding?.evidence && (
              <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  <Code sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Evidence
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    bgcolor: '#1e1e1e',
                    color: '#d4d4d4',
                    overflow: 'auto'
                  }}
                >
                  <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '0.85rem' }}>
                    {finding.evidence}
                  </pre>
                </Paper>
              </Paper>
            )}

            {/* Remediation */}
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                <Lightbulb sx={{ mr: 1, verticalAlign: 'middle' }} />
                Remediation
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                {finding?.remediation || 'No remediation guidance available'}
              </Typography>
            </Paper>

            {/* References */}
            {finding?.references && finding.references.length > 0 && (
              <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  <LinkIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  References
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <List dense>
                  {finding.references.map((ref, index) => (
                    <ListItem key={index}>
                      <ListItemText>
                        {ref.startsWith('http') ? (
                          <Link href={ref} target="_blank" rel="noopener noreferrer">
                            {ref}
                          </Link>
                        ) : (
                          ref
                        )}
                      </ListItemText>
                    </ListItem>
                  ))}
                </List>
              </Paper>
            )}

            {/* Notes */}
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>Notes</Typography>
              <Divider sx={{ mb: 2 }} />
              {editing ? (
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  value={editedFinding.notes || ''}
                  onChange={(e) => setEditedFinding({ ...editedFinding, notes: e.target.value })}
                  placeholder="Add notes about this finding..."
                />
              ) : (
                <Typography variant="body1" color={finding?.notes ? 'text.primary' : 'text.secondary'}>
                  {finding?.notes || 'No notes added'}
                </Typography>
              )}
            </Paper>
          </Grid>

          {/* Sidebar */}
          <Grid item xs={12} md={4}>
            {/* Details Card */}
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Details</Typography>
                <Divider sx={{ mb: 2 }} />

                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Status</Typography>
                  {editing ? (
                    <FormControl fullWidth size="small" sx={{ mt: 1 }}>
                      <Select
                        value={editedFinding.status || 'open'}
                        onChange={(e) => setEditedFinding({ ...editedFinding, status: e.target.value })}
                      >
                        {statusOptions.map((status) => (
                          <MenuItem key={status} value={status}>
                            {status.replace('_', ' ').toUpperCase()}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  ) : (
                    <Chip
                      label={(finding?.status || 'open').replace('_', ' ').toUpperCase()}
                      color={finding?.status === 'fixed' ? 'success' : 'default'}
                      size="small"
                      sx={{ mt: 0.5 }}
                    />
                  )}
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Target</Typography>
                  <Typography variant="body2">
                    <Computer sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                    {finding?.target || finding?.host || 'N/A'}
                  </Typography>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Port/Service</Typography>
                  <Typography variant="body2">
                    {finding?.port ? `${finding.port}/${finding.protocol || 'tcp'}` : 'N/A'}
                    {finding?.service && ` (${finding.service})`}
                  </Typography>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">CVSS Score</Typography>
                  <Typography variant="body2">
                    {finding?.cvss_score || finding?.cvss || 'N/A'}
                  </Typography>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">CVE</Typography>
                  <Typography variant="body2">
                    {finding?.cve ? (
                      <Link
                        href={`https://nvd.nist.gov/vuln/detail/${finding.cve}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {finding.cve}
                      </Link>
                    ) : 'N/A'}
                  </Typography>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Tool</Typography>
                  <Typography variant="body2">{finding?.tool || 'N/A'}</Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" color="text.secondary">Discovered</Typography>
                  <Typography variant="body2">
                    {finding?.created_at
                      ? new Date(finding.created_at).toLocaleString()
                      : 'N/A'}
                  </Typography>
                </Box>
              </CardContent>
            </Card>

            {/* Related Scan */}
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Related Scan</Typography>
                <Divider sx={{ mb: 2 }} />
                <Button
                  variant="outlined"
                  fullWidth
                  onClick={() => navigate(`/scans/${finding?.scan_id}`)}
                  disabled={!finding?.scan_id}
                >
                  View Scan Details
                </Button>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Container>
  )
}

export default FindingDetail
