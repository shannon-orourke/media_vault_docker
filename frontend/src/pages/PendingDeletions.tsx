import React, { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Badge,
  Modal,
  Alert,
  Pagination,
  Loader,
  Text,
  Group,
  Stack,
  Select,
  Paper,
  Title
} from '@mantine/core';
import {
  IconTrash,
  IconRestore,
  IconCheck,
  IconAlertTriangle
} from '@tabler/icons-react';
import { mediaApi, PendingDeletion } from '../services/api';

const formatFileSize = (bytes?: number | null): string => {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  const power = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length);
  const unit = units[power - 1] ?? 'KB';
  return `${(bytes / Math.pow(1024, power)).toFixed(1)} ${unit}`;
};

const formatDate = (dateString?: string | null): string => {
  if (!dateString) return 'Unknown date';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return 'Invalid date';
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric'
  });
};

const PendingDeletions: React.FC = () => {
  const [pendingDeletions, setPendingDeletions] = useState<PendingDeletion[]>([]);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const limit = 10;
  const [languageConcernFilter, setLanguageConcernFilter] = useState<string | null>(null);
  const [restoreModalOpen, setRestoreModalOpen] = useState<boolean>(false);
  const [approveModalOpen, setApproveModalOpen] = useState<boolean>(false);
  const [selectedDeletion, setSelectedDeletion] = useState<PendingDeletion | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const fetchPendingDeletions = async () => {
    setLoading(true);
    setError(null);
    try {
      const filterValue =
        languageConcernFilter === 'true' ? true :
        languageConcernFilter === 'false' ? false :
        undefined;

      const response = await mediaApi.listPendingDeletions({
        skip: (page - 1) * limit,
        limit,
        language_concern: filterValue
      });

      const mapped = (response.data.pending || []).map((item) => ({
        ...item,
        language_concern: Boolean(item.language_concern),
      }));

      setPendingDeletions(mapped);
      setTotalItems(response.data.total);
    } catch (err) {
      setError('Failed to fetch pending deletions. Please try again later.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPendingDeletions();
    const interval = setInterval(fetchPendingDeletions, 30000); // Auto-refresh every 30s
    return () => clearInterval(interval);
  }, [page, languageConcernFilter]);

  const handleRestoreClick = (deletion: PendingDeletion) => {
    setSelectedDeletion(deletion);
    setRestoreModalOpen(true);
  };

  const handleApproveClick = (deletion: PendingDeletion) => {
    setSelectedDeletion(deletion);
    setApproveModalOpen(true);
  };

  const handleConfirmRestore = async () => {
    if (!selectedDeletion) return;
    setActionLoading(true);
    try {
      await mediaApi.restoreFile(selectedDeletion.id);
      setRestoreModalOpen(false);
      setSelectedDeletion(null);
      fetchPendingDeletions();
    } catch (err) {
      setError('Failed to restore file. Please try again later.');
      console.error(err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmApprove = async () => {
    if (!selectedDeletion) return;
    setActionLoading(true);
    try {
      await mediaApi.approveDeletion(selectedDeletion.id);
      setApproveModalOpen(false);
      setSelectedDeletion(null);
      fetchPendingDeletions();
    } catch (err) {
      setError('Failed to approve deletion. Please try again later.');
      console.error(err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCleanup = async () => {
    if (!confirm('This will permanently delete all approved pending deletions. Continue?')) {
      return;
    }
    setLoading(true);
    try {
      const response = await mediaApi.cleanupOldPending();
      const deleted = response.data.deleted ?? 0;
      alert(`Cleaned up ${deleted} old pending deletions.`);
      fetchPendingDeletions();
    } catch (err) {
      setError('Failed to cleanup old pending deletions.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const hasLanguageConcern = pendingDeletions.some(deletion => deletion.language_concern);

  return (
    <Stack p="md">
      <Title order={2}>Pending Deletions</Title>

      {hasLanguageConcern && (
        <Alert icon={<IconAlertTriangle size={16} />} title="Language Concerns" color="yellow">
          Some deletions have language concerns. Please review them carefully.
        </Alert>
      )}

      <Group justify="space-between">
        <Select
          label="Filter by Language Concern"
          placeholder="All"
          value={languageConcernFilter}
          onChange={(value) => setLanguageConcernFilter(value)}
          data={[
            { value: 'true', label: 'Has Concern' },
            { value: 'false', label: 'No Concern' }
          ]}
          clearable
          style={{ width: 200 }}
        />
        <Button
          variant="outline"
          color="red"
          onClick={handleCleanup}
          disabled={loading || totalItems === 0}
        >
          Cleanup Old Pending
        </Button>
      </Group>

      {error && <Alert title="Error" color="red">{error}</Alert>}

      {loading && (
        <Group justify="center" p="xl">
          <Loader />
        </Group>
      )}

      {!loading && pendingDeletions.length === 0 && (
        <Paper p="xl" withBorder>
          <Text ta="center" c="dimmed">No pending deletions found.</Text>
        </Paper>
      )}

      {!loading && pendingDeletions.length > 0 && (
        <>
          <Table striped highlightOnHover>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Original Path</th>
                <th>Temp Path</th>
                <th>File Size</th>
                <th>Reason</th>
                <th>Quality Diff</th>
                <th>Language</th>
                <th>Staged At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {pendingDeletions.map(deletion => (
                <tr
                  key={deletion.id}
                  style={{
                    backgroundColor: deletion.language_concern ? 'rgba(255, 212, 59, 0.1)' : 'transparent'
                  }}
                >
                  <td>
                    <Text size="sm" fw={500}>{deletion.filename}</Text>
                  </td>
                  <td>
                    <Text size="xs" color="dimmed">{deletion.original_filepath}</Text>
                  </td>
                  <td>
                    <Text size="xs" color="dimmed">{deletion.temp_filepath || 'N/A'}</Text>
                  </td>
                  <td>
                    <Text size="sm">{formatFileSize(deletion.file_size)}</Text>
                  </td>
                  <td>
                    <Text size="sm">{deletion.reason}</Text>
                  </td>
                  <td>
                    {deletion.quality_score_diff !== null && deletion.quality_score_diff !== undefined ? (
                      <Badge color={deletion.quality_score_diff > 0 ? 'green' : 'red'}>
                        {deletion.quality_score_diff > 0 ? '+' : ''}{deletion.quality_score_diff.toFixed(2)}
                      </Badge>
                    ) : (
                      <Badge color="gray">N/A</Badge>
                    )}
                  </td>
                  <td>
                    <Badge color={deletion.language_concern ? 'yellow' : 'gray'}>
                      {deletion.language_concern ? 'Concern' : 'OK'}
                    </Badge>
                  </td>
                  <td>
                    <Text size="xs">{formatDate(deletion.staged_at)}</Text>
                  </td>
                  <td>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        variant="light"
                        color="blue"
                        leftSection={<IconRestore size={14} />}
                        onClick={() => handleRestoreClick(deletion)}
                      >
                        Restore
                      </Button>
                      <Button
                        size="xs"
                        variant="light"
                        color="red"
                        leftSection={<IconCheck size={14} />}
                        onClick={() => handleApproveClick(deletion)}
                      >
                        Approve
                      </Button>
                    </Group>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>

          <Group justify="center" mt="md">
            <Pagination
              total={Math.ceil(totalItems / limit)}
              value={page}
              onChange={setPage}
            />
          </Group>
        </>
      )}

      {/* Restore Confirmation Modal */}
      <Modal
        opened={restoreModalOpen}
        onClose={() => setRestoreModalOpen(false)}
        title="Confirm Restore"
      >
        <Text mb="md">
          Are you sure you want to restore <strong>{selectedDeletion?.filename}</strong>?
        </Text>
        <Text size="sm" color="dimmed" mb="md">
          This will move the file back to its original location.
        </Text>
        <Group justify="flex-end">
          <Button
            variant="outline"
            onClick={() => setRestoreModalOpen(false)}
            disabled={actionLoading}
          >
            Cancel
          </Button>
          <Button
            color="blue"
            onClick={handleConfirmRestore}
            loading={actionLoading}
            leftSection={<IconRestore size={16} />}
          >
            Restore
          </Button>
        </Group>
      </Modal>

      {/* Approve Deletion Confirmation Modal */}
      <Modal
        opened={approveModalOpen}
        onClose={() => setApproveModalOpen(false)}
        title="Confirm Deletion Approval"
      >
        <Text mb="md">
          Are you sure you want to approve deletion of <strong>{selectedDeletion?.filename}</strong>?
        </Text>
        <Text size="sm" color="dimmed" mb="md">
          This action cannot be undone. The file will be permanently deleted.
        </Text>
        <Group justify="flex-end">
          <Button
            variant="outline"
            onClick={() => setApproveModalOpen(false)}
            disabled={actionLoading}
          >
            Cancel
          </Button>
          <Button
            color="red"
            onClick={handleConfirmApprove}
            loading={actionLoading}
            leftSection={<IconTrash size={16} />}
          >
            Approve Deletion
          </Button>
        </Group>
      </Modal>
    </Stack>
  );
};

export default PendingDeletions;
