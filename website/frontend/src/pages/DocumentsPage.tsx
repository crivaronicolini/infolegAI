import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { FileUpload, FileUploadTrigger } from '@/components/ui/file-upload';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader } from '@/components/ui/loader';
import {
  getDocuments,
  uploadDocuments,
  deleteAllDocuments,
  type Document,
} from '@/lib/api';

export function DocumentsPage() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadDocuments();
    } else {
      setIsLoading(false);
    }
  }, [user, loadDocuments]);

  const handleFilesAdded = async (files: File[]) => {
    const pdfFiles = files.filter((f) => f.type === 'application/pdf');
    if (pdfFiles.length === 0) {
      alert('Only PDF files are supported');
      return;
    }

    setIsUploading(true);
    try {
      const result = await uploadDocuments(pdfFiles);
      if (result.successful_uploads.length > 0) {
        setDocuments((prev) => [...result.successful_uploads, ...prev]);
      }
      if (result.failed_uploads.length > 0) {
        alert(`Failed: ${result.failed_uploads.map((f) => f.filename).join(', ')}`);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteAll = async () => {
    if (!confirm('Delete all documents? This cannot be undone.')) return;

    try {
      await deleteAllDocuments();
      setDocuments([]);
    } catch (error) {
      console.error('Failed to delete documents:', error);
      alert('Failed to delete documents');
    }
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <p className="text-muted-foreground">Sign in to manage your documents</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Documents</h1>
        {documents.length > 0 && (
          <Button variant="destructive" size="sm" onClick={handleDeleteAll}>
            Delete All
          </Button>
        )}
      </div>

      <FileUpload onFilesAdded={handleFilesAdded} accept=".pdf">
        <Card className="mb-6 border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            {isUploading ? (
              <>
                <Loader variant="dots" />
                <p className="mt-4 text-muted-foreground">Uploading...</p>
              </>
            ) : (
              <>
                <div className="text-4xl mb-4">📄</div>
                <p className="text-muted-foreground mb-4">
                  Drag and drop PDF files here, or click to browse
                </p>
                <FileUploadTrigger asChild>
                  <Button>Upload PDFs</Button>
                </FileUploadTrigger>
              </>
            )}
          </CardContent>
        </Card>
      </FileUpload>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader variant="dots" />
        </div>
      ) : documents.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No documents uploaded yet. Upload PDFs to start asking questions.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {documents.map((doc) => (
            <Card key={doc.id}>
              <CardHeader className="py-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-medium flex items-center gap-2">
                    <span className="text-xl">📄</span>
                    {doc.filename}
                  </CardTitle>
                  <span className="text-sm text-muted-foreground">
                    {new Date(doc.uploaded_at).toLocaleDateString()}
                  </span>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
