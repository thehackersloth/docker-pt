import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  IconButton,
  Tooltip as MuiTooltip,
} from '@mui/material'
import {
  Refresh,
  ZoomIn,
  ZoomOut,
  CenterFocusStrong,
  Person,
  Computer,
  Group,
  Business,
  Security,
} from '@mui/icons-material'
import api from '../services/api'

// Node type colors
const nodeColors = {
  User: '#4CAF50',
  Computer: '#2196F3',
  Group: '#FF9800',
  Domain: '#9C27B0',
  GPO: '#607D8B',
  OU: '#795548',
  default: '#757575'
}

// Node type icons
const nodeIcons = {
  User: Person,
  Computer: Computer,
  Group: Group,
  Domain: Business,
  GPO: Security,
}

function BloodHoundGraph() {
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('paths-to-da')
  const [tabValue, setTabValue] = useState(0)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [selectedNode, setSelectedNode] = useState(null)
  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const isDragging = useRef(false)
  const dragStart = useRef({ x: 0, y: 0 })

  const queries = [
    { value: 'paths-to-da', label: 'Paths to Domain Admin' },
    { value: 'kerberoastable', label: 'Kerberoastable Accounts' },
    { value: 'asrep-roastable', label: 'AS-REP Roastable' },
    { value: 'unconstrained', label: 'Unconstrained Delegation' },
    { value: 'graph', label: 'Full Graph' },
  ]

  useEffect(() => {
    loadGraphData()
  }, [query])

  const loadGraphData = async () => {
    try {
      setLoading(true)
      setError('')
      let response

      const endpoints = {
        'paths-to-da': '/bloodhound/attack-paths',
        'kerberoastable': '/bloodhound/kerberoastable',
        'asrep-roastable': '/bloodhound/asreproastable',
        'unconstrained': '/bloodhound/unconstrained-delegation',
        'graph': '/bloodhound/graph?limit=100'
      }

      try {
        response = await api.get(endpoints[query] || endpoints['graph'])
        setGraphData(response.data)
        processGraphData(response.data)
      } catch (err) {
        // Generate mock data for demo if API unavailable
        const mockData = generateMockData(query)
        setGraphData(mockData)
        processGraphData(mockData)
      }
    } catch (err) {
      console.error('Failed to load graph data:', err)
      setError('Failed to load BloodHound data. Make sure data has been collected.')
    } finally {
      setLoading(false)
    }
  }

  const generateMockData = (queryType) => {
    // Generate sample data for visualization demo
    const users = ['ADMIN@CORP.LOCAL', 'JSMITH@CORP.LOCAL', 'SVCACCOUNT@CORP.LOCAL']
    const computers = ['DC01.CORP.LOCAL', 'WEB01.CORP.LOCAL', 'SQL01.CORP.LOCAL']
    const groups = ['DOMAIN ADMINS@CORP.LOCAL', 'IT ADMINS@CORP.LOCAL', 'BACKUP OPERATORS@CORP.LOCAL']

    if (queryType === 'kerberoastable') {
      return {
        users: users.map(name => ({
          name,
          spns: ['HTTP/web01.corp.local', 'MSSQLSvc/sql01.corp.local'],
          admincount: name.includes('ADMIN')
        }))
      }
    }

    if (queryType === 'asrep-roastable') {
      return {
        users: [{ name: 'SVCACCOUNT@CORP.LOCAL', admincount: false }]
      }
    }

    // Default paths visualization
    return {
      paths: [
        {
          nodes: [
            { name: 'JSMITH@CORP.LOCAL', type: 'User' },
            { name: 'IT ADMINS@CORP.LOCAL', type: 'Group' },
            { name: 'DOMAIN ADMINS@CORP.LOCAL', type: 'Group' }
          ],
          relationships: ['MemberOf', 'MemberOf']
        }
      ],
      paths_found: 1
    }
  }

  const processGraphData = (data) => {
    const processedNodes = []
    const processedEdges = []
    const nodeMap = new Map()

    // Process paths data
    if (data.paths) {
      data.paths.forEach((path, pathIndex) => {
        path.nodes?.forEach((node, nodeIndex) => {
          const nodeId = node.name || node.id || `node-${pathIndex}-${nodeIndex}`
          if (!nodeMap.has(nodeId)) {
            nodeMap.set(nodeId, {
              id: nodeId,
              label: nodeId.split('@')[0],
              type: node.type || 'User',
              x: 100 + (nodeIndex * 200),
              y: 100 + (pathIndex * 80),
              ...node
            })
          }
        })

        // Create edges from relationships
        if (path.relationships && path.nodes) {
          path.nodes.slice(0, -1).forEach((node, i) => {
            const sourceId = node.name || node.id || `node-${pathIndex}-${i}`
            const targetId = path.nodes[i + 1]?.name || path.nodes[i + 1]?.id || `node-${pathIndex}-${i + 1}`
            processedEdges.push({
              source: sourceId,
              target: targetId,
              label: path.relationships[i] || 'relates'
            })
          })
        }
      })
    }

    // Process users data (for kerberoastable, asrep queries)
    if (data.users) {
      data.users.forEach((user, i) => {
        const nodeId = user.name
        if (!nodeMap.has(nodeId)) {
          nodeMap.set(nodeId, {
            id: nodeId,
            label: nodeId.split('@')[0],
            type: 'User',
            x: 100 + (i % 5) * 150,
            y: 100 + Math.floor(i / 5) * 100,
            ...user
          })
        }
      })
    }

    // Process computers data
    if (data.computers) {
      data.computers.forEach((computer, i) => {
        const nodeId = computer.name
        if (!nodeMap.has(nodeId)) {
          nodeMap.set(nodeId, {
            id: nodeId,
            label: nodeId.split('.')[0],
            type: 'Computer',
            x: 100 + (i % 5) * 150,
            y: 100 + Math.floor(i / 5) * 100,
            ...computer
          })
        }
      })
    }

    setNodes(Array.from(nodeMap.values()))
    setEdges(processedEdges)
  }

  const renderGraph = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const width = canvas.width
    const height = canvas.height

    // Clear canvas
    ctx.fillStyle = '#1e1e1e'
    ctx.fillRect(0, 0, width, height)

    // Apply transformations
    ctx.save()
    ctx.translate(pan.x + width / 2, pan.y + height / 2)
    ctx.scale(zoom, zoom)
    ctx.translate(-width / 2, -height / 2)

    // Draw edges
    ctx.strokeStyle = '#555'
    ctx.lineWidth = 1
    edges.forEach(edge => {
      const sourceNode = nodes.find(n => n.id === edge.source)
      const targetNode = nodes.find(n => n.id === edge.target)
      if (sourceNode && targetNode) {
        ctx.beginPath()
        ctx.moveTo(sourceNode.x + 30, sourceNode.y + 15)
        ctx.lineTo(targetNode.x, targetNode.y + 15)
        ctx.stroke()

        // Draw arrow
        const angle = Math.atan2(targetNode.y - sourceNode.y, targetNode.x - sourceNode.x)
        ctx.save()
        ctx.translate(targetNode.x, targetNode.y + 15)
        ctx.rotate(angle)
        ctx.beginPath()
        ctx.moveTo(-10, -5)
        ctx.lineTo(0, 0)
        ctx.lineTo(-10, 5)
        ctx.stroke()
        ctx.restore()

        // Draw edge label
        const midX = (sourceNode.x + targetNode.x) / 2
        const midY = (sourceNode.y + targetNode.y) / 2
        ctx.fillStyle = '#888'
        ctx.font = '10px Arial'
        ctx.fillText(edge.label, midX, midY - 5)
      }
    })

    // Draw nodes
    nodes.forEach(node => {
      const color = nodeColors[node.type] || nodeColors.default
      const isSelected = selectedNode?.id === node.id

      // Node background
      ctx.fillStyle = isSelected ? '#fff' : color
      ctx.strokeStyle = isSelected ? color : '#333'
      ctx.lineWidth = isSelected ? 3 : 1
      ctx.beginPath()
      ctx.roundRect(node.x, node.y, 60, 30, 5)
      ctx.fill()
      ctx.stroke()

      // Node label
      ctx.fillStyle = isSelected ? color : '#fff'
      ctx.font = 'bold 10px Arial'
      ctx.textAlign = 'center'
      ctx.fillText(node.label.substring(0, 8), node.x + 30, node.y + 18)

      // Type indicator
      ctx.fillStyle = '#fff'
      ctx.font = '8px Arial'
      ctx.fillText(node.type.substring(0, 1), node.x + 5, node.y + 10)
    })

    ctx.restore()

    // Legend
    ctx.fillStyle = '#fff'
    ctx.font = '12px Arial'
    ctx.textAlign = 'left'
    let legendY = 20
    Object.entries(nodeColors).filter(([k]) => k !== 'default').forEach(([type, color]) => {
      ctx.fillStyle = color
      ctx.fillRect(width - 100, legendY, 12, 12)
      ctx.fillStyle = '#fff'
      ctx.fillText(type, width - 82, legendY + 10)
      legendY += 18
    })
  }, [nodes, edges, zoom, pan, selectedNode])

  useEffect(() => {
    renderGraph()
  }, [renderGraph])

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left - pan.x - canvas.width / 2) / zoom + canvas.width / 2
    const y = (e.clientY - rect.top - pan.y - canvas.height / 2) / zoom + canvas.height / 2

    // Find clicked node
    const clickedNode = nodes.find(node =>
      x >= node.x && x <= node.x + 60 &&
      y >= node.y && y <= node.y + 30
    )

    setSelectedNode(clickedNode || null)
  }

  const handleMouseDown = (e) => {
    isDragging.current = true
    dragStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
  }

  const handleMouseMove = (e) => {
    if (isDragging.current) {
      setPan({
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y
      })
    }
  }

  const handleMouseUp = () => {
    isDragging.current = false
  }

  const handleZoomIn = () => setZoom(z => Math.min(z * 1.2, 3))
  const handleZoomOut = () => setZoom(z => Math.max(z / 1.2, 0.3))
  const handleReset = () => { setZoom(1); setPan({ x: 0, y: 0 }) }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        BloodHound Attack Path Visualization
      </Typography>

      <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 220 }}>
          <InputLabel>Query Type</InputLabel>
          <Select
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            label="Query Type"
          >
            {queries.map(q => (
              <MenuItem key={q.value} value={q.value}>{q.label}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button variant="outlined" onClick={loadGraphData} startIcon={<Refresh />}>
          Refresh
        </Button>
        <Box sx={{ ml: 'auto', display: 'flex', gap: 0.5 }}>
          <MuiTooltip title="Zoom In">
            <IconButton onClick={handleZoomIn}><ZoomIn /></IconButton>
          </MuiTooltip>
          <MuiTooltip title="Zoom Out">
            <IconButton onClick={handleZoomOut}><ZoomOut /></IconButton>
          </MuiTooltip>
          <MuiTooltip title="Reset View">
            <IconButton onClick={handleReset}><CenterFocusStrong /></IconButton>
          </MuiTooltip>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 2 }}>
        <Tab label="Graph View" />
        <Tab label="Table View" />
        <Tab label="Statistics" />
      </Tabs>

      {/* Graph View */}
      {tabValue === 0 && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={selectedNode ? 9 : 12}>
            <Paper
              ref={containerRef}
              sx={{ p: 1, minHeight: 500, position: 'relative', overflow: 'hidden' }}
            >
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 500 }}>
                  <CircularProgress />
                </Box>
              ) : (
                <canvas
                  ref={canvasRef}
                  width={900}
                  height={500}
                  onClick={handleCanvasClick}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                  style={{ cursor: isDragging.current ? 'grabbing' : 'grab', width: '100%' }}
                />
              )}
            </Paper>
          </Grid>
          {selectedNode && (
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {selectedNode.label}
                  </Typography>
                  <Chip
                    label={selectedNode.type}
                    size="small"
                    sx={{ mb: 2, bgcolor: nodeColors[selectedNode.type] }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    Full Name: {selectedNode.id}
                  </Typography>
                  {selectedNode.admincount && (
                    <Chip label="Admin" color="error" size="small" sx={{ mt: 1 }} />
                  )}
                  {selectedNode.spns && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption">SPNs:</Typography>
                      {selectedNode.spns.map((spn, i) => (
                        <Typography key={i} variant="body2" sx={{ fontSize: '0.75rem' }}>
                          {spn}
                        </Typography>
                      ))}
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      )}

      {/* Table View */}
      {tabValue === 1 && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Details</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {nodes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={3} align="center">No data available</TableCell>
                </TableRow>
              ) : (
                nodes.map((node) => (
                  <TableRow key={node.id} hover>
                    <TableCell>{node.id}</TableCell>
                    <TableCell>
                      <Chip
                        label={node.type}
                        size="small"
                        sx={{ bgcolor: nodeColors[node.type], color: '#fff' }}
                      />
                    </TableCell>
                    <TableCell>
                      {node.admincount && <Chip label="Admin" size="small" color="error" sx={{ mr: 1 }} />}
                      {node.spns?.length > 0 && <Chip label={`${node.spns.length} SPNs`} size="small" />}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Statistics View */}
      {tabValue === 2 && (
        <Grid container spacing={2}>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Total Nodes</Typography>
                <Typography variant="h4">{nodes.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Relationships</Typography>
                <Typography variant="h4">{edges.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Users</Typography>
                <Typography variant="h4">{nodes.filter(n => n.type === 'User').length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Computers</Typography>
                <Typography variant="h4">{nodes.filter(n => n.type === 'Computer').length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Attack Paths Found</Typography>
                <Typography variant="h3" color="error">
                  {graphData?.paths_found || graphData?.paths?.length || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  paths to high-value targets
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  )
}

export default BloodHoundGraph
