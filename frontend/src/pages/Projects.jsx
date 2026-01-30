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
  Card,
  CardContent,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider
} from '@mui/material'
import {
  Add,
  Delete,
  Edit,
  Refresh,
  Business,
  Assignment,
  PlayArrow,
  Pause,
  CheckCircle,
  Archive
} from '@mui/icons-material'
import api from '../services/api'

const engagementTypes = [
  { value: 'external_pentest', label: 'External Pentest' },
  { value: 'internal_pentest', label: 'Internal Pentest' },
  { value: 'web_app_pentest', label: 'Web Application Pentest' },
  { value: 'mobile_app_pentest', label: 'Mobile App Pentest' },
  { value: 'api_pentest', label: 'API Pentest' },
  { value: 'wireless_pentest', label: 'Wireless Pentest' },
  { value: 'social_engineering', label: 'Social Engineering' },
  { value: 'red_team', label: 'Red Team' },
  { value: 'purple_team', label: 'Purple Team' },
  { value: 'vulnerability_assessment', label: 'Vulnerability Assessment' },
  { value: 'compliance_audit', label: 'Compliance Audit' }
]

const statusColors = {
  planning: 'default',
  active: 'success',
  on_hold: 'warning',
  completed: 'info',
  archived: 'default'
}

const complianceFrameworks = [
  'PCI-DSS',
  'HIPAA',
  'NIST-CSF',
  'SOC2',
  'ISO27001',
  'OWASP'
]

function Projects() {
  const [tab, setTab] = useState(0)
  const [projects, setProjects] = useState([])
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Dialogs
  const [projectDialogOpen, setProjectDialogOpen] = useState(false)
  const [clientDialogOpen, setClientDialogOpen] = useState(false)

  // Forms
  const [newProject, setNewProject] = useState({
    name: '',
    client_id: '',
    engagement_type: 'external_pentest',
    description: '',
    scope: '',
    start_date: '',
    end_date: '',
    lead_tester: '',
    compliance_frameworks: []
  })

  const [newClient, setNewClient] = useState({
    name: '',
    industry: '',
    contact_name: '',
    contact_email: '',
    website: ''
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [projectsRes, clientsRes] = await Promise.all([
        api.get('/projects').catch(() => ({ data: [] })),
        api.get('/projects/clients').catch(() => ({ data: [] }))
      ])
      setProjects(projectsRes.data || [])
      setClients(clientsRes.data || [])
      setError('')
    } catch (err) {
      console.error('Failed to load data:', err)
      setError('Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProject = async () => {
    try {
      const scope = newProject.scope
        ? newProject.scope.split('\n').filter(s => s.trim())
        : null

      await api.post('/projects', {
        ...newProject,
        scope,
        compliance_frameworks: newProject.compliance_frameworks.length > 0
          ? newProject.compliance_frameworks
          : null
      })

      setSuccess('Project created successfully')
      setProjectDialogOpen(false)
      setNewProject({
        name: '',
        client_id: '',
        engagement_type: 'external_pentest',
        description: '',
        scope: '',
        start_date: '',
        end_date: '',
        lead_tester: '',
        compliance_frameworks: []
      })
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create project')
    }
  }

  const handleCreateClient = async () => {
    try {
      await api.post('/projects/clients', newClient)
      setSuccess('Client created successfully')
      setClientDialogOpen(false)
      setNewClient({
        name: '',
        industry: '',
        contact_name: '',
        contact_email: '',
        website: ''
      })
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create client')
    }
  }

  const handleUpdateStatus = async (projectId, newStatus) => {
    try {
      await api.put(`/projects/${projectId}/status?new_status=${newStatus}`)
      setSuccess('Status updated')
      fetchData()
    } catch (err) {
      setError('Failed to update status')
    }
  }

  const handleDeleteProject = async (projectId) => {
    if (!window.confirm('Delete this project?')) return
    try {
      await api.delete(`/projects/${projectId}`)
      setSuccess('Project deleted')
      fetchData()
    } catch (err) {
      setError('Failed to delete project')
    }
  }

  const handleDeleteClient = async (clientId) => {
    if (!window.confirm('Delete this client?')) return
    try {
      await api.delete(`/projects/clients/${clientId}`)
      setSuccess('Client deleted')
      fetchData()
    } catch (err) {
      setError('Failed to delete client')
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
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4">Projects & Clients</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton onClick={fetchData}><Refresh /></IconButton>
            <Button
              variant="outlined"
              startIcon={<Business />}
              onClick={() => setClientDialogOpen(true)}
            >
              Add Client
            </Button>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setProjectDialogOpen(true)}
            >
              New Project
            </Button>
          </Box>
        </Box>

        {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
        {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

        {/* Stats */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Total Projects</Typography>
                <Typography variant="h4">{projects.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Active</Typography>
                <Typography variant="h4" color="success.main">
                  {projects.filter(p => p.status === 'active').length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Clients</Typography>
                <Typography variant="h4">{clients.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Completed</Typography>
                <Typography variant="h4">
                  {projects.filter(p => p.status === 'completed').length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 2 }}>
          <Tab label="Projects" icon={<Assignment />} iconPosition="start" />
          <Tab label="Clients" icon={<Business />} iconPosition="start" />
        </Tabs>

        {tab === 0 && (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Project Name</TableCell>
                  <TableCell>Client</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Compliance</TableCell>
                  <TableCell>Dates</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {projects.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography color="text.secondary">No projects yet</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  projects.map((project) => (
                    <TableRow key={project.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">{project.name}</Typography>
                        {project.description && (
                          <Typography variant="caption" color="text.secondary">
                            {project.description.substring(0, 50)}...
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>{project.client_name || '-'}</TableCell>
                      <TableCell>
                        <Chip
                          label={project.engagement_type?.replace(/_/g, ' ')}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={project.status}
                          size="small"
                          color={statusColors[project.status] || 'default'}
                        />
                      </TableCell>
                      <TableCell>
                        {project.compliance_frameworks?.map((fw) => (
                          <Chip key={fw} label={fw} size="small" sx={{ mr: 0.5 }} />
                        )) || '-'}
                      </TableCell>
                      <TableCell>
                        {project.start_date
                          ? new Date(project.start_date).toLocaleDateString()
                          : 'Not set'}
                      </TableCell>
                      <TableCell>
                        {project.status === 'planning' && (
                          <Tooltip title="Start">
                            <IconButton size="small" onClick={() => handleUpdateStatus(project.id, 'active')}>
                              <PlayArrow color="success" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {project.status === 'active' && (
                          <>
                            <Tooltip title="Complete">
                              <IconButton size="small" onClick={() => handleUpdateStatus(project.id, 'completed')}>
                                <CheckCircle color="info" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Hold">
                              <IconButton size="small" onClick={() => handleUpdateStatus(project.id, 'on_hold')}>
                                <Pause color="warning" />
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                        <Tooltip title="Delete">
                          <IconButton size="small" color="error" onClick={() => handleDeleteProject(project.id)}>
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
        )}

        {tab === 1 && (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Client Name</TableCell>
                  <TableCell>Industry</TableCell>
                  <TableCell>Contact</TableCell>
                  <TableCell>Projects</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {clients.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary">No clients yet</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  clients.map((client) => (
                    <TableRow key={client.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">{client.name}</Typography>
                      </TableCell>
                      <TableCell>{client.industry || '-'}</TableCell>
                      <TableCell>
                        {client.contact_name && <Typography variant="body2">{client.contact_name}</Typography>}
                        {client.contact_email && (
                          <Typography variant="caption" color="text.secondary">{client.contact_email}</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip label={client.project_count || 0} size="small" />
                      </TableCell>
                      <TableCell>
                        <Tooltip title="Delete">
                          <IconButton size="small" color="error" onClick={() => handleDeleteClient(client.id)}>
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
        )}
      </Box>

      {/* New Project Dialog */}
      <Dialog open={projectDialogOpen} onClose={() => setProjectDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Project</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                required
                label="Project Name"
                value={newProject.name}
                onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Client</InputLabel>
                <Select
                  value={newProject.client_id}
                  onChange={(e) => setNewProject({ ...newProject, client_id: e.target.value })}
                  label="Client"
                >
                  <MenuItem value="">No Client</MenuItem>
                  {clients.map((c) => (
                    <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth required>
                <InputLabel>Engagement Type</InputLabel>
                <Select
                  value={newProject.engagement_type}
                  onChange={(e) => setNewProject({ ...newProject, engagement_type: e.target.value })}
                  label="Engagement Type"
                >
                  {engagementTypes.map((t) => (
                    <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Lead Tester"
                value={newProject.lead_tester}
                onChange={(e) => setNewProject({ ...newProject, lead_tester: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={newProject.description}
                onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Scope (one target per line)"
                value={newProject.scope}
                onChange={(e) => setNewProject({ ...newProject, scope: e.target.value })}
                multiline
                rows={3}
                placeholder="192.168.1.0/24&#10;example.com&#10;api.example.com"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Start Date"
                type="date"
                value={newProject.start_date}
                onChange={(e) => setNewProject({ ...newProject, start_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="End Date"
                type="date"
                value={newProject.end_date}
                onChange={(e) => setNewProject({ ...newProject, end_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Compliance Frameworks</InputLabel>
                <Select
                  multiple
                  value={newProject.compliance_frameworks}
                  onChange={(e) => setNewProject({ ...newProject, compliance_frameworks: e.target.value })}
                  label="Compliance Frameworks"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      {selected.map((v) => <Chip key={v} label={v} size="small" />)}
                    </Box>
                  )}
                >
                  {complianceFrameworks.map((fw) => (
                    <MenuItem key={fw} value={fw}>{fw}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setProjectDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateProject} disabled={!newProject.name}>
            Create Project
          </Button>
        </DialogActions>
      </Dialog>

      {/* New Client Dialog */}
      <Dialog open={clientDialogOpen} onClose={() => setClientDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Client</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                required
                label="Client Name"
                value={newClient.name}
                onChange={(e) => setNewClient({ ...newClient, name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Industry"
                value={newClient.industry}
                onChange={(e) => setNewClient({ ...newClient, industry: e.target.value })}
                placeholder="e.g., Healthcare, Finance, Technology"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Contact Name"
                value={newClient.contact_name}
                onChange={(e) => setNewClient({ ...newClient, contact_name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Contact Email"
                type="email"
                value={newClient.contact_email}
                onChange={(e) => setNewClient({ ...newClient, contact_email: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Website"
                value={newClient.website}
                onChange={(e) => setNewClient({ ...newClient, website: e.target.value })}
                placeholder="https://example.com"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClientDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateClient} disabled={!newClient.name}>
            Add Client
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default Projects
