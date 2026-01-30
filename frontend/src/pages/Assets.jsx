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
  TablePagination,
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
  Checkbox,
  Collapse
} from '@mui/material'
import {
  Add,
  Delete,
  Refresh,
  Edit,
  Computer,
  Language,
  Cloud,
  Api,
  NetworkCheck,
  Upload,
  ExpandMore,
  ExpandLess,
  FilterList,
  Search
} from '@mui/icons-material'
import api from '../services/api'

const assetTypes = [
  { value: 'host', label: 'Host/IP', icon: <Computer /> },
  { value: 'domain', label: 'Domain', icon: <Language /> },
  { value: 'ip_range', label: 'IP Range/CIDR', icon: <NetworkCheck /> },
  { value: 'web_application', label: 'Web Application', icon: <Language /> },
  { value: 'api', label: 'API Endpoint', icon: <Api /> },
  { value: 'cloud_resource', label: 'Cloud Resource', icon: <Cloud /> }
]

const criticalityLevels = [
  { value: 'critical', label: 'Critical', color: 'error' },
  { value: 'high', label: 'High', color: 'warning' },
  { value: 'medium', label: 'Medium', color: 'info' },
  { value: 'low', label: 'Low', color: 'success' },
  { value: 'unknown', label: 'Unknown', color: 'default' }
]

function Assets() {
  const [assets, setAssets] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(25)
  const [total, setTotal] = useState(0)
  const [selected, setSelected] = useState([])

  // Dialogs
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [bulkDialogOpen, setBulkDialogOpen] = useState(false)
  const [editAsset, setEditAsset] = useState(null)
  const [filtersOpen, setFiltersOpen] = useState(false)

  // Filters
  const [filters, setFilters] = useState({
    asset_type: '',
    criticality: '',
    search: ''
  })

  // New asset form
  const [newAsset, setNewAsset] = useState({
    name: '',
    asset_type: 'host',
    identifier: '',
    description: '',
    criticality: 'unknown',
    owner: '',
    department: '',
    location: '',
    tags: ''
  })

  // Bulk import form
  const [bulkImport, setBulkImport] = useState({
    mode: 'cidr', // cidr, domains, list
    input: '',
    default_criticality: 'unknown',
    default_tags: ''
  })

  useEffect(() => {
    fetchData()
  }, [page, pageSize, filters])

  const fetchData = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page + 1,
        page_size: pageSize
      })

      if (filters.asset_type) params.append('asset_type', filters.asset_type)
      if (filters.criticality) params.append('criticality', filters.criticality)
      if (filters.search) params.append('search', filters.search)

      const [assetsRes, statsRes] = await Promise.all([
        api.get(`/assets?${params}`),
        api.get('/assets/stats')
      ])

      setAssets(assetsRes.data.items || [])
      setTotal(assetsRes.data.total || 0)
      setStats(statsRes.data)
      setError('')
    } catch (err) {
      console.error('Failed to load assets:', err)
      setError('Failed to load assets')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateAsset = async () => {
    try {
      const tags = newAsset.tags ? newAsset.tags.split(',').map(t => t.trim()).filter(t => t) : null

      await api.post('/assets', {
        ...newAsset,
        tags
      })

      setSuccess('Asset created successfully')
      setCreateDialogOpen(false)
      setNewAsset({
        name: '',
        asset_type: 'host',
        identifier: '',
        description: '',
        criticality: 'unknown',
        owner: '',
        department: '',
        location: '',
        tags: ''
      })
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create asset')
    }
  }

  const handleBulkImport = async () => {
    try {
      const tags = bulkImport.default_tags
        ? bulkImport.default_tags.split(',').map(t => t.trim()).filter(t => t)
        : null

      const payload = {
        default_criticality: bulkImport.default_criticality,
        default_tags: tags
      }

      if (bulkImport.mode === 'cidr') {
        payload.cidr_ranges = bulkImport.input.split('\n').map(l => l.trim()).filter(l => l)
      } else if (bulkImport.mode === 'domains') {
        payload.domains = bulkImport.input.split('\n').map(l => l.trim()).filter(l => l)
      } else {
        // List mode - parse each line as identifier
        payload.assets = bulkImport.input.split('\n')
          .map(l => l.trim())
          .filter(l => l)
          .map(identifier => ({
            name: identifier,
            asset_type: identifier.includes('.') && !identifier.match(/^\d/) ? 'domain' : 'host',
            identifier
          }))
      }

      const result = await api.post('/assets/bulk', payload)

      setSuccess(`Created ${result.data.created_count} assets. ${result.data.error_count} errors.`)
      setBulkDialogOpen(false)
      setBulkImport({
        mode: 'cidr',
        input: '',
        default_criticality: 'unknown',
        default_tags: ''
      })
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to import assets')
    }
  }

  const handleUpdateAsset = async () => {
    if (!editAsset) return

    try {
      const tags = editAsset.tags
        ? (typeof editAsset.tags === 'string'
            ? editAsset.tags.split(',').map(t => t.trim()).filter(t => t)
            : editAsset.tags)
        : null

      await api.put(`/assets/${editAsset.id}`, {
        ...editAsset,
        tags
      })

      setSuccess('Asset updated successfully')
      setEditAsset(null)
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update asset')
    }
  }

  const handleDelete = async (assetId) => {
    if (!window.confirm('Delete this asset?')) return

    try {
      await api.delete(`/assets/${assetId}`)
      setSuccess('Asset deleted')
      fetchData()
    } catch (err) {
      setError('Failed to delete asset')
    }
  }

  const handleBulkDelete = async () => {
    if (!window.confirm(`Delete ${selected.length} selected assets?`)) return

    try {
      await api.delete('/assets', { data: selected })
      setSuccess(`Deleted ${selected.length} assets`)
      setSelected([])
      fetchData()
    } catch (err) {
      setError('Failed to delete assets')
    }
  }

  const handleSelectAll = (event) => {
    if (event.target.checked) {
      setSelected(assets.map(a => a.id))
    } else {
      setSelected([])
    }
  }

  const handleSelect = (id) => {
    setSelected(prev =>
      prev.includes(id)
        ? prev.filter(s => s !== id)
        : [...prev, id]
    )
  }

  const getCriticalityChip = (criticality) => {
    const level = criticalityLevels.find(l => l.value === criticality)
    return (
      <Chip
        label={level?.label || criticality}
        color={level?.color || 'default'}
        size="small"
      />
    )
  }

  const getAssetIcon = (type) => {
    const assetType = assetTypes.find(t => t.value === type)
    return assetType?.icon || <Computer />
  }

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4">Assets & Targets</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {selected.length > 0 && (
              <Button
                variant="outlined"
                color="error"
                startIcon={<Delete />}
                onClick={handleBulkDelete}
              >
                Delete ({selected.length})
              </Button>
            )}
            <IconButton onClick={fetchData}>
              <Refresh />
            </IconButton>
            <Button
              variant="outlined"
              startIcon={<Upload />}
              onClick={() => setBulkDialogOpen(true)}
            >
              Bulk Import
            </Button>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setCreateDialogOpen(true)}
            >
              Add Asset
            </Button>
          </Box>
        </Box>

        {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
        {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

        {/* Stats Cards */}
        {stats && (
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>Total Assets</Typography>
                  <Typography variant="h4">{stats.total}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>Hosts</Typography>
                  <Typography variant="h4">{stats.by_type?.host || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>Domains</Typography>
                  <Typography variant="h4">{stats.by_type?.domain || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>Critical</Typography>
                  <Typography variant="h4" color="error">{stats.by_criticality?.critical || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>With Vulns</Typography>
                  <Typography variant="h4" color="warning.main">{stats.with_vulnerabilities || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Filters */}
        <Paper sx={{ mb: 2, p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <TextField
              size="small"
              placeholder="Search assets..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
              }}
              sx={{ width: 300 }}
            />
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>Type</InputLabel>
              <Select
                value={filters.asset_type}
                onChange={(e) => setFilters({ ...filters, asset_type: e.target.value })}
                label="Type"
              >
                <MenuItem value="">All Types</MenuItem>
                {assetTypes.map(t => (
                  <MenuItem key={t.value} value={t.value}>{t.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>Criticality</InputLabel>
              <Select
                value={filters.criticality}
                onChange={(e) => setFilters({ ...filters, criticality: e.target.value })}
                label="Criticality"
              >
                <MenuItem value="">All Levels</MenuItem>
                {criticalityLevels.map(c => (
                  <MenuItem key={c.value} value={c.value}>{c.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            {(filters.asset_type || filters.criticality || filters.search) && (
              <Button
                size="small"
                onClick={() => setFilters({ asset_type: '', criticality: '', search: '' })}
              >
                Clear Filters
              </Button>
            )}
          </Box>
        </Paper>

        {/* Assets Table */}
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={selected.length > 0 && selected.length < assets.length}
                    checked={assets.length > 0 && selected.length === assets.length}
                    onChange={handleSelectAll}
                  />
                </TableCell>
                <TableCell>Asset</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Identifier</TableCell>
                <TableCell>Criticality</TableCell>
                <TableCell>Owner</TableCell>
                <TableCell>Findings</TableCell>
                <TableCell>Last Seen</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={9} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : assets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center">
                    <Typography color="text.secondary">No assets found</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                assets.map((asset) => (
                  <TableRow key={asset.id} hover selected={selected.includes(asset.id)}>
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={selected.includes(asset.id)}
                        onChange={() => handleSelect(asset.id)}
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getAssetIcon(asset.asset_type)}
                        <Box>
                          <Typography variant="body2">{asset.name}</Typography>
                          {asset.description && (
                            <Typography variant="caption" color="text.secondary">
                              {asset.description.substring(0, 50)}...
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip label={asset.asset_type} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {asset.identifier}
                      </Typography>
                    </TableCell>
                    <TableCell>{getCriticalityChip(asset.criticality)}</TableCell>
                    <TableCell>{asset.owner || '-'}</TableCell>
                    <TableCell>
                      {asset.findings_count > 0 ? (
                        <Chip label={asset.findings_count} size="small" color="warning" />
                      ) : '-'}
                    </TableCell>
                    <TableCell>
                      {asset.last_seen
                        ? new Date(asset.last_seen).toLocaleDateString()
                        : '-'}
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Edit">
                        <IconButton size="small" onClick={() => setEditAsset(asset)}>
                          <Edit />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton size="small" color="error" onClick={() => handleDelete(asset.id)}>
                          <Delete />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(e, newPage) => setPage(newPage)}
            rowsPerPage={pageSize}
            onRowsPerPageChange={(e) => {
              setPageSize(parseInt(e.target.value, 10))
              setPage(0)
            }}
            rowsPerPageOptions={[10, 25, 50, 100]}
          />
        </TableContainer>
      </Box>

      {/* Create Asset Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add New Asset</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Asset Name"
                value={newAsset.name}
                onChange={(e) => setNewAsset({ ...newAsset, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth required>
                <InputLabel>Asset Type</InputLabel>
                <Select
                  value={newAsset.asset_type}
                  onChange={(e) => setNewAsset({ ...newAsset, asset_type: e.target.value })}
                  label="Asset Type"
                >
                  {assetTypes.map(t => (
                    <MenuItem key={t.value} value={t.value}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {t.icon} {t.label}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Identifier (IP, Domain, URL, CIDR)"
                value={newAsset.identifier}
                onChange={(e) => setNewAsset({ ...newAsset, identifier: e.target.value })}
                placeholder="192.168.1.1, example.com, 10.0.0.0/24"
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={newAsset.description}
                onChange={(e) => setNewAsset({ ...newAsset, description: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>Criticality</InputLabel>
                <Select
                  value={newAsset.criticality}
                  onChange={(e) => setNewAsset({ ...newAsset, criticality: e.target.value })}
                  label="Criticality"
                >
                  {criticalityLevels.map(c => (
                    <MenuItem key={c.value} value={c.value}>{c.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Owner"
                value={newAsset.owner}
                onChange={(e) => setNewAsset({ ...newAsset, owner: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Department"
                value={newAsset.department}
                onChange={(e) => setNewAsset({ ...newAsset, department: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Location"
                value={newAsset.location}
                onChange={(e) => setNewAsset({ ...newAsset, location: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Tags (comma-separated)"
                value={newAsset.tags}
                onChange={(e) => setNewAsset({ ...newAsset, tags: e.target.value })}
                placeholder="production, web-tier, dmz"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreateAsset}
            disabled={!newAsset.name || !newAsset.identifier}
          >
            Create Asset
          </Button>
        </DialogActions>
      </Dialog>

      {/* Bulk Import Dialog */}
      <Dialog open={bulkDialogOpen} onClose={() => setBulkDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Bulk Import Assets</DialogTitle>
        <DialogContent>
          <Tabs
            value={bulkImport.mode}
            onChange={(e, v) => setBulkImport({ ...bulkImport, mode: v })}
            sx={{ mb: 2 }}
          >
            <Tab value="cidr" label="CIDR Ranges" />
            <Tab value="domains" label="Domains" />
            <Tab value="list" label="IP/Host List" />
          </Tabs>

          <TextField
            fullWidth
            multiline
            rows={8}
            label={
              bulkImport.mode === 'cidr'
                ? 'Enter CIDR ranges (one per line)'
                : bulkImport.mode === 'domains'
                ? 'Enter domains (one per line)'
                : 'Enter IPs or hostnames (one per line)'
            }
            value={bulkImport.input}
            onChange={(e) => setBulkImport({ ...bulkImport, input: e.target.value })}
            placeholder={
              bulkImport.mode === 'cidr'
                ? '192.168.1.0/24\n10.0.0.0/24'
                : bulkImport.mode === 'domains'
                ? 'example.com\napi.example.com'
                : '192.168.1.1\n192.168.1.2\nserver.local'
            }
            sx={{ mb: 2 }}
          />

          <Grid container spacing={2}>
            <Grid item xs={6}>
              <FormControl fullWidth>
                <InputLabel>Default Criticality</InputLabel>
                <Select
                  value={bulkImport.default_criticality}
                  onChange={(e) => setBulkImport({ ...bulkImport, default_criticality: e.target.value })}
                  label="Default Criticality"
                >
                  {criticalityLevels.map(c => (
                    <MenuItem key={c.value} value={c.value}>{c.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="Default Tags (comma-separated)"
                value={bulkImport.default_tags}
                onChange={(e) => setBulkImport({ ...bulkImport, default_tags: e.target.value })}
                placeholder="imported, to-scan"
              />
            </Grid>
          </Grid>

          {bulkImport.mode === 'cidr' && (
            <Alert severity="info" sx={{ mt: 2 }}>
              CIDR ranges will be expanded to individual host assets (max /24 network)
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBulkDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleBulkImport}
            disabled={!bulkImport.input.trim()}
          >
            Import Assets
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Asset Dialog */}
      <Dialog open={!!editAsset} onClose={() => setEditAsset(null)} maxWidth="md" fullWidth>
        <DialogTitle>Edit Asset</DialogTitle>
        <DialogContent>
          {editAsset && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Asset Name"
                  value={editAsset.name}
                  onChange={(e) => setEditAsset({ ...editAsset, name: e.target.value })}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Identifier"
                  value={editAsset.identifier}
                  disabled
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Description"
                  value={editAsset.description || ''}
                  onChange={(e) => setEditAsset({ ...editAsset, description: e.target.value })}
                  multiline
                  rows={2}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Criticality</InputLabel>
                  <Select
                    value={editAsset.criticality}
                    onChange={(e) => setEditAsset({ ...editAsset, criticality: e.target.value })}
                    label="Criticality"
                  >
                    {criticalityLevels.map(c => (
                      <MenuItem key={c.value} value={c.value}>{c.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Owner"
                  value={editAsset.owner || ''}
                  onChange={(e) => setEditAsset({ ...editAsset, owner: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Department"
                  value={editAsset.department || ''}
                  onChange={(e) => setEditAsset({ ...editAsset, department: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Location"
                  value={editAsset.location || ''}
                  onChange={(e) => setEditAsset({ ...editAsset, location: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Tags"
                  value={Array.isArray(editAsset.tags) ? editAsset.tags.join(', ') : editAsset.tags || ''}
                  onChange={(e) => setEditAsset({ ...editAsset, tags: e.target.value })}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Notes"
                  value={editAsset.notes || ''}
                  onChange={(e) => setEditAsset({ ...editAsset, notes: e.target.value })}
                  multiline
                  rows={3}
                />
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditAsset(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleUpdateAsset}>
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default Assets
