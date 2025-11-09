import { useEffect, useState } from 'react';
import {
  Stack,
  Title,
  Card,
  Text,
  Badge,
  Group,
  Button,
  Table,
  Select,
  TextInput,
  Accordion,
  ActionIcon,
  Tooltip,
} from '@mantine/core';
import {
  IconPackage,
  IconDownload,
  IconTrash,
  IconCheck,
  IconAlertCircle,
  IconClock,
  IconFolder,
} from '@tabler/icons-react';
import { mediaApi, type ArchiveFile } from '../services/api';
import { notifications } from '@mantine/notifications';
import { modals } from '@mantine/modals';

export default function Unarchive() {
  const [archives, setArchives] = useState<ArchiveFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [scanPaths, setScanPaths] = useState('/volume1/downloads');

  useEffect(() => {
    loadArchives();
  }, [statusFilter]);

  const loadArchives = async () => {
    try {
      setLoading(true);
      const res = await mediaApi.listArchives({ status: statusFilter || undefined });
      setArchives(res.data.archives || []);
    } catch (error) {
      console.error('Error loading archives:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load archives',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleScanForArchives = async () => {
    try {
      notifications.show({
        title: 'Scanning',
        message: 'Scanning for archive files...',
        color: 'blue',
        autoClose: false,
        id: 'archive-scan',
      });

      const paths = scanPaths.split(',').map(p => p.trim());
      const res = await mediaApi.scanArchives({ paths });

      notifications.update({
        id: 'archive-scan',
        title: 'Scan Complete',
        message: `Found ${res.data.found} archives (${res.data.new} new)`,
        color: 'green',
        autoClose: 3000,
      });

      loadArchives();
    } catch (error) {
      notifications.update({
        id: 'archive-scan',
        title: 'Error',
        message: 'Failed to scan for archives',
        color: 'red',
        autoClose: 3000,
      });
    }
  };

  const handleExtract = (archive: ArchiveFile) => {
    modals.openConfirmModal({
      title: 'Extract Archive',
      children: (
        <Stack gap="xs">
          <Text size="sm">
            Extract <strong>{archive.filename}</strong> to:
          </Text>
          <Text size="sm" c="dimmed">
            {archive.destination_path}
          </Text>
          <Text size="xs" c="dimmed" mt="md">
            This will extract all files and index them in the media library.
          </Text>
        </Stack>
      ),
      labels: { confirm: 'Extract', cancel: 'Cancel' },
      confirmProps: { color: 'blue' },
      onConfirm: async () => {
        try {
          await mediaApi.extractArchive(archive.id);
          notifications.show({
            title: 'Success',
            message: 'Archive extracted successfully',
            color: 'green',
          });
          loadArchives();
        } catch (error) {
          notifications.show({
            title: 'Error',
            message: 'Failed to extract archive',
            color: 'red',
          });
        }
      },
    });
  };

  const handleMarkForDeletion = (archive: ArchiveFile) => {
    modals.openConfirmModal({
      title: 'Mark for Deletion',
      children: (
        <Text size="sm">
          Are you sure you want to mark "{archive.filename}" for immediate deletion?
          This will remove the 6-month grace period for seeding.
        </Text>
      ),
      labels: { confirm: 'Mark for Deletion', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: async () => {
        try {
          await mediaApi.markArchiveForDeletion(archive.id);
          notifications.show({
            title: 'Success',
            message: 'Archive marked for deletion',
            color: 'green',
          });
          loadArchives();
        } catch (error) {
          notifications.show({
            title: 'Error',
            message: 'Failed to mark archive',
            color: 'red',
          });
        }
      },
    });
  };

  const handleDelete = (archive: ArchiveFile) => {
    modals.openConfirmModal({
      title: 'Delete Archive',
      children: (
        <Text size="sm">
          Are you sure you want to permanently delete "{archive.filename}"?
          This action cannot be undone.
        </Text>
      ),
      labels: { confirm: 'Delete', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: async () => {
        try {
          await mediaApi.deleteArchive(archive.id);
          notifications.show({
            title: 'Success',
            message: 'Archive deleted',
            color: 'green',
          });
          loadArchives();
        } catch (error) {
          notifications.show({
            title: 'Error',
            message: 'Failed to delete archive',
            color: 'red',
          });
        }
      },
    });
  };

  const formatBytes = (bytes: number): string => {
    const gb = bytes / (1024 ** 3);
    if (gb >= 1) return `${gb.toFixed(2)} GB`;
    const mb = bytes / (1024 ** 2);
    return `${mb.toFixed(2)} MB`;
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleString();
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'extracted': return 'green';
      case 'pending': return 'blue';
      case 'failed': return 'red';
      default: return 'gray';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'extracted': return <IconCheck size={16} />;
      case 'pending': return <IconClock size={16} />;
      case 'failed': return <IconAlertCircle size={16} />;
      default: return <IconPackage size={16} />;
    }
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={2}>Archive Management</Title>
        <Text c="dimmed">{archives.length} archives</Text>
      </Group>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Stack gap="md">
          <Title order={4}>Scan for Archives</Title>
          <Text size="sm" c="dimmed">
            Scan NAS paths for RAR, ZIP, and 7z archives. Archives will be tracked for extraction and seeding.
          </Text>

          <Group>
            <TextInput
              placeholder="/volume1/downloads, /volume1/torrents"
              label="Scan Paths (comma-separated)"
              value={scanPaths}
              onChange={(e) => setScanPaths(e.currentTarget.value)}
              style={{ flex: 1 }}
            />
          </Group>

          <Button
            leftSection={<IconPackage size={16} />}
            onClick={handleScanForArchives}
          >
            Scan for Archives
          </Button>
        </Stack>
      </Card>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Group justify="space-between" mb="md">
          <Title order={4}>Archives</Title>
          <Select
            placeholder="Filter by status"
            value={statusFilter}
            onChange={setStatusFilter}
            data={[
              { value: '', label: 'All' },
              { value: 'pending', label: 'Pending' },
              { value: 'extracted', label: 'Extracted' },
              { value: 'failed', label: 'Failed' },
            ]}
            w={200}
            clearable
          />
        </Group>

        {loading ? (
          <Text c="dimmed">Loading...</Text>
        ) : archives.length === 0 ? (
          <Text c="dimmed">No archives found. Run a scan to find RAR/ZIP files.</Text>
        ) : (
          <Accordion variant="contained">
            {archives.map((archive) => (
              <Accordion.Item key={archive.id} value={archive.id.toString()}>
                <Accordion.Control>
                  <Group justify="space-between">
                    <div>
                      <Group gap="xs">
                        <Text fw={500}>{archive.filename}</Text>
                        <Badge color={getStatusColor(archive.extraction_status)} leftSection={getStatusIcon(archive.extraction_status)}>
                          {archive.extraction_status}
                        </Badge>
                      </Group>
                      <Text size="sm" c="dimmed" mt={4}>
                        {archive.parsed_title} {archive.parsed_year && `(${archive.parsed_year})`} · {formatBytes(archive.file_size)} · {archive.media_type}
                      </Text>
                    </div>
                  </Group>
                </Accordion.Control>
                <Accordion.Panel>
                  <Stack gap="md">
                    <Table>
                      <Table.Tbody>
                        <Table.Tr>
                          <Table.Td fw={500}>File Path</Table.Td>
                          <Table.Td>{archive.filepath}</Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                          <Table.Td fw={500}>Archive Type</Table.Td>
                          <Table.Td><Badge variant="light">{archive.archive_type.toUpperCase()}</Badge></Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                          <Table.Td fw={500}>Destination</Table.Td>
                          <Table.Td>
                            <Group gap="xs">
                              <IconFolder size={16} />
                              <Text size="sm">{archive.destination_path}</Text>
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                        {archive.extracted_to_path && (
                          <Table.Tr>
                            <Table.Td fw={500}>Extracted To</Table.Td>
                            <Table.Td>{archive.extracted_to_path}</Table.Td>
                          </Table.Tr>
                        )}
                        <Table.Tr>
                          <Table.Td fw={500}>Discovered</Table.Td>
                          <Table.Td>{formatDate(archive.discovered_at)}</Table.Td>
                        </Table.Tr>
                        {archive.mark_for_deletion_at && (
                          <Table.Tr>
                            <Table.Td fw={500}>Deletion Date</Table.Td>
                            <Table.Td>
                              <Text c="orange">{formatDate(archive.mark_for_deletion_at)}</Text>
                            </Table.Td>
                          </Table.Tr>
                        )}
                      </Table.Tbody>
                    </Table>

                    <Group justify="flex-end">
                      {archive.extraction_status === 'pending' && (
                        <Button
                          leftSection={<IconDownload size={16} />}
                          color="blue"
                          onClick={() => handleExtract(archive)}
                        >
                          Extract
                        </Button>
                      )}
                      {archive.extraction_status === 'extracted' && (
                        <Tooltip label="Mark for immediate deletion (removes 6-month grace period)">
                          <ActionIcon
                            variant="light"
                            color="orange"
                            onClick={() => handleMarkForDeletion(archive)}
                          >
                            <IconClock size={18} />
                          </ActionIcon>
                        </Tooltip>
                      )}
                      <ActionIcon
                        variant="light"
                        color="red"
                        onClick={() => handleDelete(archive)}
                      >
                        <IconTrash size={18} />
                      </ActionIcon>
                    </Group>
                  </Stack>
                </Accordion.Panel>
              </Accordion.Item>
            ))}
          </Accordion>
        )}
      </Card>
    </Stack>
  );
}
