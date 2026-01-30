import React, { useState } from 'react';
import {
  Box,
  Button,
  Paper,
  Typography,
  LinearProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DeleteIcon from '@mui/icons-material/Delete';
import DescriptionIcon from '@mui/icons-material/Description';
import api from '../services/api';

function PDFUpload() {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState(null);
  const [pdfs, setPdfs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, filename: null });

  React.useEffect(() => {
    loadPDFs();
  }, []);

  const loadPDFs = async () => {
    try {
      const response = await api.get('/pdf-upload/list');
      setPdfs(response.data.pdfs || []);
    } catch (error) {
      console.error('Failed to load PDFs:', error);
      setMessage({ type: 'error', text: 'Failed to load PDFs' });
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.pdf')) {
      setMessage({ type: 'error', text: 'Only PDF files are allowed' });
      return;
    }

    if (file.size > 100 * 1024 * 1024) {
      setMessage({ type: 'error', text: 'File size exceeds 100MB limit' });
      return;
    }

    setUploading(true);
    setProgress(0);
    setMessage(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('auto_learn', 'true');

      const response = await api.post('/pdf-upload/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setProgress(percentCompleted);
        },
      });

      setMessage({
        type: 'success',
        text: `PDF uploaded successfully! Extracted ${response.data.methodology.phases} phases, ${response.data.methodology.tools} tools, ${response.data.methodology.techniques} techniques.`
      });

      // Reload PDF list
      await loadPDFs();
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Upload failed'
      });
    } finally {
      setUploading(false);
      setProgress(0);
      event.target.value = ''; // Reset file input
    }
  };

  const handleDelete = async () => {
    if (!deleteDialog.filename) return;

    try {
      await api.delete(`/pdf-upload/${deleteDialog.filename}`);
      setMessage({ type: 'success', text: 'PDF deleted successfully' });
      setDeleteDialog({ open: false, filename: null });
      await loadPDFs();
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Delete failed'
      });
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        PDF Methodology Upload
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Upload PDFs to extract methodology and continuously learn from them
      </Typography>

      {message && (
        <Alert severity={message.type} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ mb: 2 }}>
          <input
            accept=".pdf"
            style={{ display: 'none' }}
            id="pdf-upload-input"
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
          />
          <label htmlFor="pdf-upload-input">
            <Button
              variant="contained"
              component="span"
              startIcon={<CloudUploadIcon />}
              disabled={uploading}
              fullWidth
              sx={{ mb: 2 }}
            >
              {uploading ? 'Uploading...' : 'Upload PDF'}
            </Button>
          </label>
        </Box>

        {uploading && (
          <Box sx={{ width: '100%' }}>
            <LinearProgress variant="determinate" value={progress} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {progress}% uploaded
            </Typography>
          </Box>
        )}

        <Typography variant="body2" color="text.secondary">
          Supported: PDF files up to 100MB
        </Typography>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Uploaded PDFs ({pdfs.length})
        </Typography>

        {loading ? (
          <Typography>Loading...</Typography>
        ) : pdfs.length === 0 ? (
          <Typography color="text.secondary">No PDFs uploaded yet</Typography>
        ) : (
          <List>
            {pdfs.map((pdf, index) => (
              <ListItem
                key={index}
                secondaryAction={
                  <IconButton
                    edge="end"
                    onClick={() => setDeleteDialog({ open: true, filename: pdf.filename })}
                  >
                    <DeleteIcon />
                  </IconButton>
                }
              >
                <DescriptionIcon sx={{ mr: 2, color: 'primary.main' }} />
                <ListItemText
                  primary={pdf.filename}
                  secondary={
                    <>
                      {formatFileSize(pdf.size)} • {pdf.methodology.phases} phases •{' '}
                      {pdf.methodology.tools} tools • {pdf.methodology.techniques} techniques
                      <br />
                      Uploaded: {new Date(pdf.uploaded_at).toLocaleString()}
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Paper>

      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, filename: null })}>
        <DialogTitle>Delete PDF</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete {deleteDialog.filename}?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, filename: null })}>
            Cancel
          </Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default PDFUpload;
