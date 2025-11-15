import { useState } from 'react';
import {
  Stack,
  Title,
  Card,
  Textarea,
  Button,
  Group,
  Select,
  Text,
  Badge,
  Divider,
} from '@mantine/core';
import { IconScan, IconCopy } from '@tabler/icons-react';
import { mediaApi } from '../services/api';
import { notifications } from '@mantine/notifications';

const DEFAULT_SCAN_PATHS = [
  '/volume1/docker/transmission/downloads/complete/tv',
  '/volume1/docker/transmission/downloads/complete/movies',
  '/volume1/videos',
  '/volume1/docker/data/torrents/torrents',
].join('\n');

export default function Scanner() {
  const [paths, setPaths] = useState(DEFAULT_SCAN_PATHS);
  const [scanType, setScanType] = useState<'full' | 'incremental'>('full');
  const [scanning, setScanning] = useState(false);
  const [deduplicating, setDeduplicating] = useState(false);
  const [lastScanResult, setLastScanResult] = useState<{
    filesFound: number;
    filesNew: number;
    filesUpdated: number;
    errors: number;
  } | null>(null);

  const handleStartScan = async () => {
    const pathList = paths.split('\n').map(p => p.trim()).filter(p => p.length > 0);

    if (pathList.length === 0) {
      notifications.show({
        title: 'Error',
        message: 'Please enter at least one path to scan',
        color: 'red',
      });
      return;
    }

    try {
      setScanning(true);
      const res = await mediaApi.startScan({
        paths: pathList,
        scan_type: scanType,
      });

      setLastScanResult({
        filesFound: res.data.files_found,
        filesNew: res.data.files_new,
        filesUpdated: res.data.files_updated,
        errors: res.data.errors_count,
      });

      notifications.show({
        title: 'Scan Complete',
        message: res.data.message,
        color: 'green',
      });
    } catch (error: any) {
      console.error('Error starting scan:', error);
      notifications.show({
        title: 'Scan Failed',
        message: error.response?.data?.detail || 'Failed to start scan',
        color: 'red',
      });
    } finally {
      setScanning(false);
    }
  };

  const handleDeduplicate = async () => {
    try {
      setDeduplicating(true);
      const res = await mediaApi.runDeduplicate();

      notifications.show({
        title: 'Deduplication Complete',
        message: `Found ${res.data.groups_created} duplicate groups (${res.data.exact_duplicates} exact, ${res.data.fuzzy_duplicates} fuzzy)`,
        color: 'green',
      });
    } catch (error: any) {
      console.error('Error running deduplication:', error);
      notifications.show({
        title: 'Deduplication Failed',
        message: error.response?.data?.detail || 'Failed to run deduplication',
        color: 'red',
      });
    } finally {
      setDeduplicating(false);
    }
  };

  return (
    <Stack gap="md">
      <Title order={2}>Scanner</Title>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Stack gap="md">
          <Title order={4}>NAS Scan</Title>
          <Text size="sm" c="dimmed">
            Scan NAS paths for video files and extract metadata using FFprobe.
          </Text>

          <Textarea
            label="NAS Paths (one per line)"
            placeholder={DEFAULT_SCAN_PATHS}
            value={paths}
            onChange={(e) => setPaths(e.currentTarget.value)}
            rows={4}
          />

          <Select
            label="Scan Type"
            value={scanType}
            onChange={(value) => setScanType(value as 'full' | 'incremental')}
            data={[
              { value: 'full', label: 'Full Scan (scan all files)' },
              { value: 'incremental', label: 'Incremental (skip existing files)' },
            ]}
          />

          <Button
            leftSection={<IconScan size={16} />}
            onClick={handleStartScan}
            loading={scanning}
            fullWidth
          >
            {scanning ? 'Scanning...' : 'Start Scan'}
          </Button>

          {lastScanResult && (
            <>
              <Divider />
              <Group>
                <Badge variant="light">Files Found: {lastScanResult.filesFound}</Badge>
                <Badge variant="light" color="green">New: {lastScanResult.filesNew}</Badge>
                <Badge variant="light" color="blue">Updated: {lastScanResult.filesUpdated}</Badge>
                <Badge variant="light" color="red">Errors: {lastScanResult.errors}</Badge>
              </Group>
            </>
          )}
        </Stack>
      </Card>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Stack gap="md">
          <Title order={4}>Duplicate Detection</Title>
          <Text size="sm" c="dimmed">
            Run duplicate detection on all media files using MD5 hashing and fuzzy matching.
          </Text>

          <Button
            leftSection={<IconCopy size={16} />}
            onClick={handleDeduplicate}
            loading={deduplicating}
            variant="light"
            fullWidth
          >
            {deduplicating ? 'Analyzing...' : 'Run Duplicate Detection'}
          </Button>
        </Stack>
      </Card>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Stack gap="md">
          <Title order={4}>How It Works</Title>
          <Text size="sm">
            <strong>1. Scan:</strong> MediaVault recursively scans the specified NAS paths for video files
            (.mkv, .mp4, .avi, etc.). For each file, it extracts metadata using FFprobe including resolution,
            codec, bitrate, audio tracks, and subtitle tracks.
          </Text>
          <Text size="sm">
            <strong>2. Quality Scoring:</strong> Each file receives a quality score (0-200) based on resolution,
            codec, bitrate, audio quality, HDR, and subtitle tracks.
          </Text>
          <Text size="sm">
            <strong>3. Duplicate Detection:</strong> Uses MD5 hashing for exact duplicates and guessit + rapidfuzz
            for fuzzy matching (title + year for movies, title + season + episode for TV shows).
          </Text>
          <Text size="sm">
            <strong>4. Manual Review:</strong> All detected duplicates are presented for manual review. The system
            will never auto-delete files without your explicit approval.
          </Text>
        </Stack>
      </Card>
    </Stack>
  );
}
