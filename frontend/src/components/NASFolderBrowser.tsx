import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Stack,
  Text,
  Group,
  Loader,
  Paper,
  Checkbox,
  Badge,
  Breadcrumbs,
  Anchor,
  Table,
  ScrollArea,
  Alert,
  Progress,
} from '@mantine/core';
import {
  IconFolder,
  IconFile,
  IconArrowLeft,
  IconScan,
  IconCheck,
  IconAlertCircle,
} from '@tabler/icons-react';
import axios from 'axios';

interface FileItem {
  name: string;
  path: string;
  is_directory: boolean;
  size?: number;
  video_count?: number;
}

interface BrowseResponse {
  current_path: string;
  parent_path?: string;
  items: FileItem[];
}

interface ScanStatus {
  scan_id: number;
  status: string;
  files_found: number;
  files_new: number;
  files_updated: number;
  errors_count: number;
  scan_started_at: string;
  scan_completed_at?: string;
}

const API_BASE = 'http://localhost:8007/api';

export function NASFolderBrowser() {
  const [currentPath, setCurrentPath] = useState('/volume1');
  const [items, setItems] = useState<FileItem[]>([]);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load folder contents
  const loadFolder = async (path: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.get<BrowseResponse>(`${API_BASE}/nas/browse`, {
        params: { path },
      });

      setCurrentPath(response.data.current_path);
      setItems(response.data.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load folder');
      console.error('Error loading folder:', err);
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadFolder(currentPath);
  }, []);

  // Navigate to folder
  const navigateTo = (path: string) => {
    loadFolder(path);
  };

  // Navigate up
  const navigateUp = () => {
    const parts = currentPath.split('/').filter(Boolean);
    if (parts.length > 1) {
      parts.pop();
      navigateTo('/' + parts.join('/'));
    }
  };

  // Toggle folder selection
  const toggleSelection = (path: string) => {
    const newSelection = new Set(selectedPaths);
    if (newSelection.has(path)) {
      newSelection.delete(path);
    } else {
      newSelection.add(path);
    }
    setSelectedPaths(newSelection);
  };

  // Start scan
  const startScan = async () => {
    if (selectedPaths.size === 0) {
      setError('Please select at least one folder to scan');
      return;
    }

    setScanning(true);
    setError(null);

    try {
      const response = await axios.post<ScanStatus>(`${API_BASE}/nas/scan`, {
        paths: Array.from(selectedPaths),
        scan_type: 'full',
      });

      setScanStatus(response.data);

      // Poll for updates
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await axios.get<ScanStatus>(
            `${API_BASE}/nas/scan/${response.data.scan_id}`
          );

          setScanStatus(statusResponse.data);

          if (statusResponse.data.status === 'completed' || statusResponse.data.status === 'failed') {
            clearInterval(pollInterval);
            setScanning(false);
          }
        } catch (err) {
          console.error('Error polling scan status:', err);
          clearInterval(pollInterval);
          setScanning(false);
        }
      }, 2000);

      // Clear selection after starting scan
      setSelectedPaths(new Set());
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start scan');
      console.error('Error starting scan:', err);
      setScanning(false);
    }
  };

  // Format file size
  const formatSize = (bytes?: number): string => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  // Render breadcrumbs
  const renderBreadcrumbs = () => {
    const parts = currentPath.split('/').filter(Boolean);
    const breadcrumbs = parts.map((part, index) => {
      const path = '/' + parts.slice(0, index + 1).join('/');
      return (
        <Anchor key={path} onClick={() => navigateTo(path)} size="sm">
          {part}
        </Anchor>
      );
    });

    return <Breadcrumbs>{breadcrumbs}</Breadcrumbs>;
  };

  // Render scan progress
  const renderScanProgress = () => {
    if (!scanStatus) return null;

    const isCompleted = scanStatus.status === 'completed';
    const isFailed = scanStatus.status === 'failed';
    const isRunning = scanStatus.status === 'running';

    return (
      <Paper p="md" withBorder mb="md">
        <Stack gap="sm">
          <Group justify="space-between">
            <Text fw={600}>Scan Status</Text>
            <Badge color={isCompleted ? 'green' : isFailed ? 'red' : 'blue'}>
              {scanStatus.status.toUpperCase()}
            </Badge>
          </Group>

          {isRunning && <Progress value={100} striped animated />}

          <Group gap="xl">
            <Box>
              <Text size="xs" c="dimmed">Files Found</Text>
              <Text fw={600}>{scanStatus.files_found}</Text>
            </Box>
            <Box>
              <Text size="xs" c="dimmed">New Files</Text>
              <Text fw={600} c="green">{scanStatus.files_new}</Text>
            </Box>
            <Box>
              <Text size="xs" c="dimmed">Updated Files</Text>
              <Text fw={600} c="blue">{scanStatus.files_updated}</Text>
            </Box>
            <Box>
              <Text size="xs" c="dimmed">Errors</Text>
              <Text fw={600} c="red">{scanStatus.errors_count}</Text>
            </Box>
          </Group>

          {isCompleted && (
            <Alert icon={<IconCheck size={16} />} color="green">
              Scan completed successfully!
            </Alert>
          )}
          {isFailed && (
            <Alert icon={<IconAlertCircle size={16} />} color="red">
              Scan failed. Check logs for details.
            </Alert>
          )}
        </Stack>
      </Paper>
    );
  };

  return (
    <Box>
      <Stack gap="md">
        {/* Scan Progress */}
        {renderScanProgress()}

        {/* Header */}
        <Group justify="space-between">
          <Box>
            <Text size="lg" fw={600}>
              Browse NAS Folders
            </Text>
            <Text size="sm" c="dimmed">
              Select folders to scan for media files
            </Text>
          </Box>
          <Button
            leftSection={<IconScan size={16} />}
            onClick={startScan}
            disabled={selectedPaths.size === 0 || scanning}
            loading={scanning}
          >
            Scan Selected ({selectedPaths.size})
          </Button>
        </Group>

        {/* Error Alert */}
        {error && (
          <Alert icon={<IconAlertCircle size={16} />} color="red" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Navigation */}
        <Paper p="md" withBorder>
          <Group justify="space-between" mb="md">
            <Group>
              <Button
                variant="subtle"
                size="sm"
                leftSection={<IconArrowLeft size={16} />}
                onClick={navigateUp}
                disabled={currentPath === '/volume1' || currentPath === '/'}
              >
                Back
              </Button>
              {renderBreadcrumbs()}
            </Group>
            <Text size="sm" c="dimmed">
              {items.filter((i) => i.is_directory).length} folders, {items.filter((i) => !i.is_directory).length} files
            </Text>
          </Group>

          {/* File/Folder List */}
          {loading ? (
            <Group justify="center" p="xl">
              <Loader size="md" />
              <Text>Loading...</Text>
            </Group>
          ) : (
            <ScrollArea h={500}>
              <Table highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th w={40}>Select</Table.Th>
                    <Table.Th>Name</Table.Th>
                    <Table.Th>Videos</Table.Th>
                    <Table.Th>Size</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {items.map((item) => (
                    <Table.Tr
                      key={item.path}
                      style={{ cursor: item.is_directory ? 'pointer' : 'default' }}
                    >
                      <Table.Td>
                        {item.is_directory && (
                          <Checkbox
                            checked={selectedPaths.has(item.path)}
                            onChange={() => toggleSelection(item.path)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        )}
                      </Table.Td>
                      <Table.Td onClick={() => item.is_directory && navigateTo(item.path)}>
                        <Group gap="xs">
                          {item.is_directory ? (
                            <IconFolder size={20} color="var(--mantine-color-blue-6)" />
                          ) : (
                            <IconFile size={20} />
                          )}
                          <Text>{item.name}</Text>
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        {item.is_directory && item.video_count !== undefined && item.video_count > 0 && (
                          <Badge size="sm" variant="light">
                            {item.video_count} videos
                          </Badge>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm" c="dimmed">
                          {formatSize(item.size)}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          )}
        </Paper>
      </Stack>
    </Box>
  );
}
