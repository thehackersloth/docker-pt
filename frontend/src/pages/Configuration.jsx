import React, { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Box,
  Tabs,
  Tab,
  Paper,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Grid,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider,
  Card,
  CardContent,
  CardHeader,
} from '@mui/material'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  )
}

function Configuration() {
  const [tabValue, setTabValue] = useState(0)
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [aiModels, setAiModels] = useState({})

  useEffect(() => {
    loadConfig()
    loadAiModels()
  }, [])

  const loadConfig = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/config`)
      setConfig(response.data)
      setLoading(false)
    } catch (error) {
      console.error('Failed to load config:', error)
      setMessage({ type: 'error', text: 'Failed to load configuration' })
      setLoading(false)
    }
  }

  const loadAiModels = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/config/ai-models`)
      setAiModels(response.data)
    } catch (error) {
      console.error('Failed to load AI models:', error)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      await axios.put(`${API_URL}/api/v1/config`, config)
      setMessage({ type: 'success', text: 'Configuration saved successfully' })
    } catch (error) {
      console.error('Failed to save config:', error)
      setMessage({ type: 'error', text: 'Failed to save configuration' })
    } finally {
      setSaving(false)
    }
  }

  const handleTestEmail = async () => {
    try {
      await axios.post(`${API_URL}/api/v1/config/test-email`)
      setMessage({ type: 'success', text: 'Email test sent' })
    } catch (error) {
      setMessage({ type: 'error', text: 'Email test failed' })
    }
  }

  const handleTestAI = async (provider) => {
    try {
      await axios.post(`${API_URL}/api/v1/config/test-ai/${provider}`)
      setMessage({ type: 'success', text: `${provider} connection test successful` })
    } catch (error) {
      setMessage({ type: 'error', text: `${provider} connection test failed` })
    }
  }

  const updateConfig = (section, field, value) => {
    setConfig((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }))
  }

  if (loading) {
    return (
      <Container>
        <Typography>Loading configuration...</Typography>
      </Container>
    )
  }

  if (!config) {
    return (
      <Container>
        <Alert severity="error">Failed to load configuration</Alert>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Configuration
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Configure API keys, AI models, email settings, and more
        </Typography>

        {message && (
          <Alert severity={message.type} sx={{ mt: 2, mb: 2 }} onClose={() => setMessage(null)}>
            {message.text}
          </Alert>
        )}

        <Paper sx={{ mt: 3 }}>
          <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
            <Tab label="AI Configuration" />
            <Tab label="Email Settings" />
            <Tab label="Scan Settings" />
            <Tab label="Tool Settings" />
            <Tab label="Security" />
            <Tab label="System" />
          </Tabs>

          {/* AI Configuration Tab */}
          <TabPanel value={tabValue} index={0}>
            <Card>
              <CardHeader title="AI Configuration" />
              <CardContent>
                <Alert severity="warning" sx={{ mb: 3 }}>
                  ⚠️ Public AI APIs (OpenAI, Anthropic, etc.) are PUBLIC services. 
                  Data sent to these services may be stored or used for training. 
                  For privacy or regulated networks, use LOCAL AI only (Ollama, llama.cpp, RayServe, WhiteRabbit Neo).
                </Alert>
                <Alert severity="info" sx={{ mb: 3 }}>
                  💡 <strong>Privacy Recommendation:</strong> For maximum privacy in pentesting, we recommend using 
                  <strong> WhiteRabbit Neo</strong> - a privacy-focused local LLM designed for security professionals. 
                  <a href="https://github.com/projectmlc/whiterabbit-neo" target="_blank" rel="noopener noreferrer" style={{ marginLeft: '8px' }}>
                    Learn more about WhiteRabbit Neo →
                  </a>
                </Alert>

                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.ai.enabled}
                          onChange={(e) => updateConfig('ai', 'enabled', e.target.checked)}
                        />
                      }
                      label="Enable AI"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControl fullWidth>
                      <InputLabel>Privacy Mode</InputLabel>
                      <Select
                        value={config.ai.privacy_mode}
                        onChange={(e) => updateConfig('ai', 'privacy_mode', e.target.value)}
                        label="Privacy Mode"
                      >
                        <MenuItem value="strict">Strict (Local AI Only)</MenuItem>
                        <MenuItem value="normal">Normal (With Warnings)</MenuItem>
                        <MenuItem value="permissive">Permissive (All AI)</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.ai.local_only}
                          onChange={(e) => updateConfig('ai', 'local_only', e.target.checked)}
                        />
                      }
                      label="Local AI Only"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }}>Cloud AI Providers (⚠️ Public APIs)</Divider>
                  </Grid>

                  {/* OpenAI */}
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.ai.openai_enabled}
                          onChange={(e) => updateConfig('ai', 'openai_enabled', e.target.checked)}
                          disabled={config.ai.local_only}
                        />
                      }
                      label="OpenAI (GPT-4, GPT-3.5)"
                    />
                  </Grid>
                  {config.ai.openai_enabled && !config.ai.local_only && (
                    <>
                      <Grid item xs={12} md={6}>
                        <TextField
                          fullWidth
                          label="OpenAI API Key"
                          type="password"
                          value={config.ai.openai_api_key || ''}
                          onChange={(e) => updateConfig('ai', 'openai_api_key', e.target.value)}
                          helperText="Get your API key from platform.openai.com"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>OpenAI Model</InputLabel>
                          <Select
                            value={config.ai.openai_model}
                            onChange={(e) => updateConfig('ai', 'openai_model', e.target.value)}
                            label="OpenAI Model"
                          >
                            {aiModels.openai?.map((model) => (
                              <MenuItem key={model} value={model}>
                                {model}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Button
                          variant="outlined"
                          onClick={() => handleTestAI('openai')}
                        >
                          Test Connection
                        </Button>
                      </Grid>
                    </>
                  )}

                  {/* Anthropic */}
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.ai.anthropic_enabled}
                          onChange={(e) => updateConfig('ai', 'anthropic_enabled', e.target.checked)}
                          disabled={config.ai.local_only}
                        />
                      }
                      label="Anthropic (Claude)"
                    />
                  </Grid>
                  {config.ai.anthropic_enabled && !config.ai.local_only && (
                    <>
                      <Grid item xs={12} md={6}>
                        <TextField
                          fullWidth
                          label="Anthropic API Key"
                          type="password"
                          value={config.ai.anthropic_api_key || ''}
                          onChange={(e) => updateConfig('ai', 'anthropic_api_key', e.target.value)}
                          helperText="Get your API key from console.anthropic.com"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>Anthropic Model</InputLabel>
                          <Select
                            value={config.ai.anthropic_model}
                            onChange={(e) => updateConfig('ai', 'anthropic_model', e.target.value)}
                            label="Anthropic Model"
                          >
                            {aiModels.anthropic?.map((model) => (
                              <MenuItem key={model} value={model}>
                                {model}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Button
                          variant="outlined"
                          onClick={() => handleTestAI('anthropic')}
                        >
                          Test Connection
                        </Button>
                      </Grid>
                    </>
                  )}

                  {/* GitHub Copilot */}
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.ai.github_copilot_enabled}
                          onChange={(e) => updateConfig('ai', 'github_copilot_enabled', e.target.checked)}
                          disabled={config.ai.local_only}
                        />
                      }
                      label="GitHub Copilot"
                    />
                  </Grid>
                  {config.ai.github_copilot_enabled && !config.ai.local_only && (
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="GitHub Copilot Key"
                        type="password"
                        value={config.ai.github_copilot_key || ''}
                        onChange={(e) => updateConfig('ai', 'github_copilot_key', e.target.value)}
                      />
                    </Grid>
                  )}

                  {/* Gemini */}
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.ai.gemini_enabled}
                          onChange={(e) => updateConfig('ai', 'gemini_enabled', e.target.checked)}
                          disabled={config.ai.local_only}
                        />
                      }
                      label="Google Gemini"
                    />
                  </Grid>
                  {config.ai.gemini_enabled && !config.ai.local_only && (
                    <>
                      <Grid item xs={12} md={6}>
                        <TextField
                          fullWidth
                          label="Gemini API Key"
                          type="password"
                          value={config.ai.gemini_api_key || ''}
                          onChange={(e) => updateConfig('ai', 'gemini_api_key', e.target.value)}
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>Gemini Model</InputLabel>
                          <Select
                            value={config.ai.gemini_model}
                            onChange={(e) => updateConfig('ai', 'gemini_model', e.target.value)}
                            label="Gemini Model"
                          >
                            {aiModels.gemini?.map((model) => (
                              <MenuItem key={model} value={model}>
                                {model}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                    </>
                  )}

                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }}>Local AI Providers (✅ Private)</Divider>
                  </Grid>

                  {/* Ollama */}
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.ai.ollama_enabled}
                          onChange={(e) => updateConfig('ai', 'ollama_enabled', e.target.checked)}
                        />
                      }
                      label="Ollama (✅ Local, Private)"
                    />
                  </Grid>
                  {config.ai.ollama_enabled && (
                    <>
                      <Grid item xs={12} md={6}>
                        <TextField
                          fullWidth
                          label="Ollama Base URL"
                          value={config.ai.ollama_base_url}
                          onChange={(e) => updateConfig('ai', 'ollama_base_url', e.target.value)}
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>Ollama Model</InputLabel>
                          <Select
                            value={config.ai.ollama_model}
                            onChange={(e) => updateConfig('ai', 'ollama_model', e.target.value)}
                            label="Ollama Model"
                          >
                            {aiModels.ollama?.map((model) => (
                              <MenuItem key={model} value={model}>
                                {model}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Button
                          variant="outlined"
                          onClick={() => handleTestAI('ollama')}
                        >
                          Test Connection
                        </Button>
                      </Grid>
                    </>
                  )}

                  {/* llama.cpp */}
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.ai.llama_cpp_enabled}
                          onChange={(e) => updateConfig('ai', 'llama_cpp_enabled', e.target.checked)}
                        />
                      }
                      label="llama.cpp (✅ Local, Private)"
                    />
                  </Grid>
                  {config.ai.llama_cpp_enabled && (
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Model Path"
                        value={config.ai.llama_cpp_model_path}
                        onChange={(e) => updateConfig('ai', 'llama_cpp_model_path', e.target.value)}
                      />
                    </Grid>
                  )}

                  {/* RayServe */}
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.ai.rayserve_enabled}
                          onChange={(e) => updateConfig('ai', 'rayserve_enabled', e.target.checked)}
                        />
                      }
                      label="RayServe (✅ Local, Private)"
                    />
                  </Grid>
                  {config.ai.rayserve_enabled && (
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="RayServe Endpoint"
                        value={config.ai.rayserve_endpoint}
                        onChange={(e) => updateConfig('ai', 'rayserve_endpoint', e.target.value)}
                      />
                    </Grid>
                  )}

                  {/* WhiteRabbit Neo */}
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.ai.whiterabbit_neo_enabled}
                          onChange={(e) => updateConfig('ai', 'whiterabbit_neo_enabled', e.target.checked)}
                        />
                      }
                      label={
                        <Box>
                          WhiteRabbit Neo (✅ Local, Private)
                          <Typography variant="caption" display="block" color="text.secondary">
                            Recommended for privacy-focused pentesting
                          </Typography>
                        </Box>
                      }
                    />
                  </Grid>
                  {config.ai.whiterabbit_neo_enabled && (
                    <>
                      <Grid item xs={12} md={6}>
                        <TextField
                          fullWidth
                          label="WhiteRabbit Neo Base URL"
                          value={config.ai.whiterabbit_neo_base_url}
                          onChange={(e) => updateConfig('ai', 'whiterabbit_neo_base_url', e.target.value)}
                          helperText="Default: http://whiterabbit-neo:8000"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>WhiteRabbit Neo Model</InputLabel>
                          <Select
                            value={config.ai.whiterabbit_neo_model}
                            onChange={(e) => updateConfig('ai', 'whiterabbit_neo_model', e.target.value)}
                            label="WhiteRabbit Neo Model"
                          >
                            {aiModels.whiterabbit_neo?.map((model) => (
                              <MenuItem key={model} value={model}>
                                {model}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Button
                          variant="outlined"
                          onClick={() => handleTestAI('whiterabbit_neo')}
                          sx={{ mr: 2 }}
                        >
                          Test Connection
                        </Button>
                        <Button
                          variant="text"
                          href="https://github.com/projectmlc/whiterabbit-neo"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Learn More / GitHub
                        </Button>
                      </Grid>
                    </>
                  )}
                </Grid>
              </CardContent>
            </Card>
          </TabPanel>

          {/* Email Settings Tab */}
          <TabPanel value={tabValue} index={1}>
            <Card>
              <CardHeader title="Email Configuration" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.email.enabled}
                          onChange={(e) => updateConfig('email', 'enabled', e.target.checked)}
                        />
                      }
                      label="Enable Email"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="SMTP Host"
                      value={config.email.smtp_host}
                      onChange={(e) => updateConfig('email', 'smtp_host', e.target.value)}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="SMTP Port"
                      type="number"
                      value={config.email.smtp_port}
                      onChange={(e) => updateConfig('email', 'smtp_port', parseInt(e.target.value))}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="SMTP Username"
                      value={config.email.smtp_username || ''}
                      onChange={(e) => updateConfig('email', 'smtp_username', e.target.value)}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="SMTP Password"
                      type="password"
                      value={config.email.smtp_password || ''}
                      onChange={(e) => updateConfig('email', 'smtp_password', e.target.value)}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.email.smtp_use_tls}
                          onChange={(e) => updateConfig('email', 'smtp_use_tls', e.target.checked)}
                        />
                      }
                      label="Use TLS"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.email.smtp_use_ssl}
                          onChange={(e) => updateConfig('email', 'smtp_use_ssl', e.target.checked)}
                        />
                      }
                      label="Use SSL"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="From Email"
                      value={config.email.email_from}
                      onChange={(e) => updateConfig('email', 'email_from', e.target.value)}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="From Name"
                      value={config.email.email_from_name}
                      onChange={(e) => updateConfig('email', 'email_from_name', e.target.value)}
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Button
                      variant="outlined"
                      onClick={handleTestEmail}
                      sx={{ mr: 2 }}
                    >
                      Test Email
                    </Button>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </TabPanel>

          {/* Scan Settings Tab */}
          <TabPanel value={tabValue} index={2}>
            <Card>
              <CardHeader title="Scan Configuration" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="Max Concurrent Scans"
                      type="number"
                      value={config.scan.max_concurrent_scans}
                      onChange={(e) => updateConfig('scan', 'max_concurrent_scans', parseInt(e.target.value))}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="Max Scan Duration (seconds)"
                      type="number"
                      value={config.scan.max_scan_duration}
                      onChange={(e) => updateConfig('scan', 'max_scan_duration', parseInt(e.target.value))}
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.scan.require_authorization}
                          onChange={(e) => updateConfig('scan', 'require_authorization', e.target.checked)}
                        />
                      }
                      label="Require Authorization"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.scan.confirm_destructive_actions}
                          onChange={(e) => updateConfig('scan', 'confirm_destructive_actions', e.target.checked)}
                        />
                      }
                      label="Confirm Destructive Actions"
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </TabPanel>

          {/* Tool Settings Tab */}
          <TabPanel value={tabValue} index={3}>
            <Card>
              <CardHeader title="Tool Configuration" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.tools.nmap_enabled}
                          onChange={(e) => updateConfig('tools', 'nmap_enabled', e.target.checked)}
                        />
                      }
                      label="Nmap"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.tools.openvas_enabled}
                          onChange={(e) => updateConfig('tools', 'openvas_enabled', e.target.checked)}
                        />
                      }
                      label="OpenVAS"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.tools.owasp_zap_enabled}
                          onChange={(e) => updateConfig('tools', 'owasp_zap_enabled', e.target.checked)}
                        />
                      }
                      label="OWASP ZAP"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.tools.metasploit_enabled}
                          onChange={(e) => updateConfig('tools', 'metasploit_enabled', e.target.checked)}
                        />
                      }
                      label="Metasploit"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.tools.bloodhound_enabled}
                          onChange={(e) => updateConfig('tools', 'bloodhound_enabled', e.target.checked)}
                        />
                      }
                      label="BloodHound"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.tools.crackmapexec_enabled}
                          onChange={(e) => updateConfig('tools', 'crackmapexec_enabled', e.target.checked)}
                        />
                      }
                      label="CrackMapExec"
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </TabPanel>

          {/* Security Tab */}
          <TabPanel value={tabValue} index={4}>
            <Card>
              <CardHeader title="Security Configuration" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="JWT Expiration (seconds)"
                      type="number"
                      value={config.security.jwt_expiration}
                      onChange={(e) => updateConfig('security', 'jwt_expiration', parseInt(e.target.value))}
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.security.require_mfa}
                          onChange={(e) => updateConfig('security', 'require_mfa', e.target.checked)}
                        />
                      }
                      label="Require MFA"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.security.audit_enabled}
                          onChange={(e) => updateConfig('security', 'audit_enabled', e.target.checked)}
                        />
                      }
                      label="Enable Audit Logging"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.security.log_ai_queries}
                          onChange={(e) => updateConfig('security', 'log_ai_queries', e.target.checked)}
                        />
                      }
                      label="Log AI Queries"
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </TabPanel>

          {/* System Tab */}
          <TabPanel value={tabValue} index={5}>
            <Card>
              <CardHeader title="System Configuration" />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="App Name"
                      value={config.system.app_name}
                      onChange={(e) => updateConfig('system', 'app_name', e.target.value)}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="App Version"
                      value={config.system.app_version}
                      disabled
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControl fullWidth>
                      <InputLabel>Timezone</InputLabel>
                      <Select
                        value={config.system.timezone}
                        onChange={(e) => updateConfig('system', 'timezone', e.target.value)}
                        label="Timezone"
                      >
                        <MenuItem value="UTC">UTC</MenuItem>
                        <MenuItem value="America/New_York">America/New_York</MenuItem>
                        <MenuItem value="America/Los_Angeles">America/Los_Angeles</MenuItem>
                        <MenuItem value="Europe/London">Europe/London</MenuItem>
                        <MenuItem value="Asia/Tokyo">Asia/Tokyo</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <FormControl fullWidth>
                      <InputLabel>Log Level</InputLabel>
                      <Select
                        value={config.system.log_level}
                        onChange={(e) => updateConfig('system', 'log_level', e.target.value)}
                        label="Log Level"
                      >
                        <MenuItem value="DEBUG">DEBUG</MenuItem>
                        <MenuItem value="INFO">INFO</MenuItem>
                        <MenuItem value="WARNING">WARNING</MenuItem>
                        <MenuItem value="ERROR">ERROR</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.system.debug}
                          onChange={(e) => updateConfig('system', 'debug', e.target.checked)}
                        />
                      }
                      label="Debug Mode"
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </TabPanel>
        </Paper>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={saving}
            size="large"
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </Button>
        </Box>
      </Box>
    </Container>
  )
}

export default Configuration
