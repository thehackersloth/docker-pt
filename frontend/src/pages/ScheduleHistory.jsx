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
  Button,
  Grid,
} from '@mui/material'
import api from '../services/api'

function ScheduleHistory() {
  const [schedules, setSchedules] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSchedules()
  }, [])

  const loadSchedules = async () => {
    try {
      const response = await api.get('/schedules')
      setSchedules(response.data)
      setLoading(false)
    } catch (error) {
      console.error('Failed to load schedules:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Container>
        <Typography>Loading schedule history...</Typography>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Schedule History
        </Typography>

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Last Run</TableCell>
                <TableCell>Next Run</TableCell>
                <TableCell>Run Count</TableCell>
                <TableCell>Success/Failure</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {schedules.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    No schedules found
                  </TableCell>
                </TableRow>
              ) : (
                schedules.map((schedule) => (
                  <TableRow key={schedule.id} hover>
                    <TableCell>{schedule.name}</TableCell>
                    <TableCell>{schedule.schedule_type}</TableCell>
                    <TableCell>
                      <Chip
                        label={schedule.enabled ? 'Enabled' : 'Disabled'}
                        color={schedule.enabled ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {schedule.last_run_at
                        ? new Date(schedule.last_run_at).toLocaleString()
                        : 'Never'}
                    </TableCell>
                    <TableCell>
                      {schedule.next_run_at
                        ? new Date(schedule.next_run_at).toLocaleString()
                        : '-'}
                    </TableCell>
                    <TableCell>{schedule.run_count}</TableCell>
                    <TableCell>
                      {schedule.success_count} / {schedule.failure_count}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        onClick={() => {
                          if (schedule.enabled) {
                            api.post(`/schedules/${schedule.id}/disable`)
                          } else {
                            api.post(`/schedules/${schedule.id}/enable`)
                          }
                          loadSchedules()
                        }}
                      >
                        {schedule.enabled ? 'Disable' : 'Enable'}
                      </Button>
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

export default ScheduleHistory
