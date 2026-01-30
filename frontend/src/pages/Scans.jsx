import React, { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Tabs,
  Tab,
  Checkbox,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Alert,
} from '@mui/material'
import { Add as AddIcon, Computer, Language, NetworkCheck } from '@mui/icons-material'
import api from '../services/api'

function Scans() {
  const [scans, setScans] = useState([])
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(true)
  const [openDialog, setOpenDialog] = useState(false)
  const [targetMode, setTargetMode] = useState('manual') // manual or assets
  const [selectedAssets, setSelectedAssets] = useState([])
  const [newScan, setNewScan] = useState({
    name: '',
    scan_type: 'network',
    targets: '',
    description: '',
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [scansRes, assetsRes] = await Promise.all([
        api.get('/scans'),
        api.get('/assets?page_size=100').catch(() => ({ data: { items: [] } }))
      ])
      setScans(scansRes.data)
      setAssets(assetsRes.data.items || [])
      setLoading(false)
    } catch (error) {
      console.error('Failed to load data:', error)
      setLoading(false)
    }
  }

  const loadScans = loadData

  const handleCreateScan = async () => {
    try {
      let targets
      if (targetMode === 'assets') {
        targets = selectedAssets.map(id => {
          const asset = assets.find(a => a.id === id)
          return asset?.identifier
        }).filter(t => t)
      } else {
        targets = newScan.targets.split(',').map(t => t.trim()).filter(t => t)
      }

      if (targets.length === 0) {
        return
      }

      await api.post('/scans', {
        name: newScan.name,
        scan_type: newScan.scan_type,
        targets: targets,
        description: newScan.description,
      })
      setOpenDialog(false)
      setNewScan({ name: '', scan_type: 'network', targets: '', description: '' })
      setSelectedAssets([])
      setTargetMode('manual')
      loadScans()
    } catch (error) {
      console.error('Failed to create scan:', error)
    }
  }

  const toggleAssetSelection = (assetId) => {
    setSelectedAssets(prev =>
      prev.includes(assetId)
        ? prev.filter(id => id !== assetId)
        : [...prev, assetId]
    )
  }

  const getAssetIcon = (type) => {
    switch (type) {
      case 'host': return <Computer />
      case 'domain': return <Language />
      case 'ip_range': return <NetworkCheck />
      default: return <Computer />
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      pending: 'default',
      running: 'primary',
      completed: 'success',
      failed: 'error',
      cancelled: 'secondary',
    }
    return colors[status] || 'default'
  }

  if (loading) {
    return (
      <Container>
        <Typography>Loading scans...</Typography>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
          <Typography variant="h4" component="h1">
            Scans
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
          >
            New Scan
          </Button>
        </Box>

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Targets</TableCell>
                <TableCell>Progress</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {scans.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    No scans found. Create your first scan!
                  </TableCell>
                </TableRow>
              ) : (
                scans.map((scan) => (
                  <TableRow key={scan.id} hover>
                    <TableCell>{scan.name}</TableCell>
                    <TableCell>{scan.scan_type}</TableCell>
                    <TableCell>
                      <Chip
                        label={scan.status}
                        color={getStatusColor(scan.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {scan.targets.slice(0, 2).join(', ')}
                      {scan.targets.length > 2 && ` +${scan.targets.length - 2} more`}
                    </TableCell>
                    <TableCell>
                      {scan.status === 'running' ? 'In progress...' : '-'}
                    </TableCell>
                    <TableCell>
                      {new Date(scan.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Button size="small" href={`/scans/${scan.id}`}>
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Create Scan Dialog */}
        <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
          <DialogTitle>Create New Scan</DialogTitle>
          <DialogContent>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Scan Name"
                  value={newScan.name}
                  onChange={(e) => setNewScan({ ...newScan, name: e.target.value })}
                  required
                />
              </Grid>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Scan Type</InputLabel>
                  <Select
                    value={newScan.scan_type}
                    onChange={(e) => setNewScan({ ...newScan, scan_type: e.target.value })}
                    label="Scan Type"
                  >
                    <MenuItem value="network">Network Scan</MenuItem>
                    <MenuItem value="web">Web Application</MenuItem>
                    <MenuItem value="ad">Active Directory</MenuItem>
                    <MenuItem value="full">Full Pentest</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>Select Targets</Typography>
                <Tabs
                  value={targetMode}
                  onChange={(e, v) => setTargetMode(v)}
                  sx={{ mb: 2 }}
                >
                  <Tab value="manual" label="Manual Entry" />
                  <Tab value="assets" label={`From Assets (${assets.length})`} />
                </Tabs>

                {targetMode === 'manual' ? (
                  <TextField
                    fullWidth
                    label="Targets (comma-separated)"
                    value={newScan.targets}
                    onChange={(e) => setNewScan({ ...newScan, targets: e.target.value })}
                    placeholder="192.168.1.0/24, example.com, 10.0.0.1"
                    required
                    helperText="Enter IP addresses, ranges, or domains separated by commas"
                  />
                ) : (
                  <Paper variant="outlined" sx={{ maxHeight: 250, overflow: 'auto' }}>
                    {assets.length === 0 ? (
                      <Alert severity="info" sx={{ m: 2 }}>
                        No assets found. Add assets in the Assets page first.
                      </Alert>
                    ) : (
                      <List dense>
                        {assets.map((asset) => (
                          <ListItem
                            key={asset.id}
                            button
                            onClick={() => toggleAssetSelection(asset.id)}
                            selected={selectedAssets.includes(asset.id)}
                          >
                            <ListItemIcon>
                              <Checkbox
                                edge="start"
                                checked={selectedAssets.includes(asset.id)}
                                tabIndex={-1}
                                disableRipple
                              />
                            </ListItemIcon>
                            <ListItemIcon sx={{ minWidth: 36 }}>
                              {getAssetIcon(asset.asset_type)}
                            </ListItemIcon>
                            <ListItemText
                              primary={asset.name}
                              secondary={`${asset.identifier} - ${asset.asset_type}`}
                            />
                            <Chip
                              label={asset.criticality}
                              size="small"
                              color={
                                asset.criticality === 'critical' ? 'error' :
                                asset.criticality === 'high' ? 'warning' :
                                'default'
                              }
                            />
                          </ListItem>
                        ))}
                      </List>
                    )}
                  </Paper>
                )}

                {targetMode === 'assets' && selectedAssets.length > 0 && (
                  <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                    {selectedAssets.length} asset(s) selected
                  </Typography>
                )}
              </Grid>

              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Description"
                  value={newScan.description}
                  onChange={(e) => setNewScan({ ...newScan, description: e.target.value })}
                  multiline
                  rows={3}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
            <Button
              onClick={handleCreateScan}
              variant="contained"
              disabled={
                !newScan.name ||
                (targetMode === 'manual' && !newScan.targets) ||
                (targetMode === 'assets' && selectedAssets.length === 0)
              }
            >
              Create Scan
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Container>
  )
}

export default Scans
