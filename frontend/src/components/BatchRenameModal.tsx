import { useState, useMemo } from 'react';
import {
  Modal,
  Stack,
  SegmentedControl,
  TextInput,
  Table,
  Button,
  Group,
  Text,
  Paper,
  Alert,
} from '@mantine/core';
import { IconArrowRight, IconAlertCircle } from '@tabler/icons-react';
import { mediaApi, type MediaFile, type BatchRenamePayload } from '../services/api';
import { notifications } from '@mantine/notifications';

interface BatchRenameModalProps {
  opened: boolean;
  onClose: () => void;
  files: MediaFile[];
  onSuccess: () => void;
}

type RenameStrategy = 'pattern' | 'prefix_suffix' | 'find_replace';

export default function BatchRenameModal({ opened, onClose, files, onSuccess }: BatchRenameModalProps) {
  const [strategy, setStrategy] = useState<RenameStrategy>('pattern');
  const [pattern, setPattern] = useState('');
  const [prefix, setPrefix] = useState('');
  const [suffix, setSuffix] = useState('');
  const [findText, setFindText] = useState('');
  const [replaceText, setReplaceText] = useState('');
  const [loading, setLoading] = useState(false);

  // Generate preview of renamed files
  const previewFiles = useMemo(() => {
    return files.map(file => {
      let newFilename = file.filename;
      const ext = file.filename.substring(file.filename.lastIndexOf('.'));
      const nameWithoutExt = file.filename.substring(0, file.filename.lastIndexOf('.'));

      try {
        if (strategy === 'pattern' && pattern) {
          // Replace placeholders with actual metadata
          newFilename = pattern
            .replace('{title}', file.parsed_title || 'Unknown')
            .replace('{year}', file.parsed_year?.toString() || '')
            .replace('{season}', '') // Not implemented yet in MediaFile
            .replace('{episode}', '') // Not implemented yet in MediaFile
            .replace('{resolution}', file.resolution || 'Unknown')
            .replace('{codec}', file.video_codec || 'Unknown')
            + ext;
        } else if (strategy === 'prefix_suffix') {
          newFilename = `${prefix}${nameWithoutExt}${suffix}${ext}`;
        } else if (strategy === 'find_replace' && findText) {
          newFilename = nameWithoutExt.replace(new RegExp(findText, 'g'), replaceText) + ext;
        }
      } catch (error) {
        // If replacement fails, keep original filename
        newFilename = file.filename;
      }

      return {
        id: file.id,
        original: file.filename,
        new: newFilename,
        changed: newFilename !== file.filename,
      };
    });
  }, [files, strategy, pattern, prefix, suffix, findText, replaceText]);

  const changedCount = previewFiles.filter(f => f.changed).length;

  const handleApply = async () => {
    if (changedCount === 0) {
      notifications.show({
        title: 'No Changes',
        message: 'No files will be renamed with the current settings',
        color: 'yellow',
      });
      return;
    }

    setLoading(true);
    try {
      const payload: BatchRenamePayload = {
        file_ids: files.map(f => f.id),
      };

      if (strategy === 'pattern' && pattern) {
        payload.pattern = pattern;
      } else if (strategy === 'prefix_suffix') {
        payload.prefix = prefix;
        payload.suffix = suffix;
      } else if (strategy === 'find_replace' && findText) {
        payload.replace_old = findText;
        payload.replace_new = replaceText;
      }

      await mediaApi.batchRename(payload);

      notifications.show({
        title: 'Success',
        message: `${changedCount} files renamed successfully`,
        color: 'green',
      });

      onSuccess();
      onClose();
      resetForm();
    } catch (error: any) {
      notifications.show({
        title: 'Error',
        message: error.response?.data?.detail || 'Failed to rename files',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setStrategy('pattern');
    setPattern('');
    setPrefix('');
    setSuffix('');
    setFindText('');
    setReplaceText('');
  };

  const handleClose = () => {
    onClose();
    resetForm();
  };

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Batch Rename Files"
      size="xl"
      centered
    >
      <Stack gap="md">
        <Alert icon={<IconAlertCircle size={16} />} color="blue">
          <Text size="sm">
            Renaming {files.length} file{files.length !== 1 ? 's' : ''}. Preview changes below before applying.
          </Text>
        </Alert>

        <SegmentedControl
          value={strategy}
          onChange={(value) => setStrategy(value as RenameStrategy)}
          data={[
            { label: 'Pattern', value: 'pattern' },
            { label: 'Prefix/Suffix', value: 'prefix_suffix' },
            { label: 'Find & Replace', value: 'find_replace' },
          ]}
          fullWidth
        />

        {strategy === 'pattern' && (
          <Stack gap="xs">
            <TextInput
              label="Rename Pattern"
              placeholder="e.g., {title} ({year}) [{resolution}]"
              value={pattern}
              onChange={(e) => setPattern(e.currentTarget.value)}
              description="Available placeholders: {title}, {year}, {season}, {episode}, {resolution}, {codec}"
            />
          </Stack>
        )}

        {strategy === 'prefix_suffix' && (
          <Group grow>
            <TextInput
              label="Prefix"
              placeholder="Add text before filename"
              value={prefix}
              onChange={(e) => setPrefix(e.currentTarget.value)}
            />
            <TextInput
              label="Suffix"
              placeholder="Add text after filename"
              value={suffix}
              onChange={(e) => setSuffix(e.currentTarget.value)}
            />
          </Group>
        )}

        {strategy === 'find_replace' && (
          <Group grow>
            <TextInput
              label="Find"
              placeholder="Text to find"
              value={findText}
              onChange={(e) => setFindText(e.currentTarget.value)}
            />
            <TextInput
              label="Replace With"
              placeholder="Replacement text"
              value={replaceText}
              onChange={(e) => setReplaceText(e.currentTarget.value)}
            />
          </Group>
        )}

        <Paper withBorder p="md">
          <Stack gap="xs">
            <Text fw={500} size="sm">
              Preview ({changedCount} of {files.length} files will be renamed)
            </Text>
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Original Filename</Table.Th>
                    <Table.Th></Table.Th>
                    <Table.Th>New Filename</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {previewFiles.map((file) => (
                    <Table.Tr key={file.id} bg={file.changed ? 'blue.0' : undefined}>
                      <Table.Td>
                        <Text size="sm" lineClamp={1}>{file.original}</Text>
                      </Table.Td>
                      <Table.Td w={40}>
                        {file.changed && <IconArrowRight size={16} />}
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm" lineClamp={1} fw={file.changed ? 500 : 400}>
                          {file.new}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>
          </Stack>
        </Paper>

        <Group justify="flex-end">
          <Button variant="subtle" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            onClick={handleApply}
            loading={loading}
            disabled={changedCount === 0}
          >
            Apply to {changedCount} File{changedCount !== 1 ? 's' : ''}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
