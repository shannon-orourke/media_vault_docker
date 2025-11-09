import { useState, useEffect } from 'react';
import {
  Modal,
  Tabs,
  TextInput,
  Select,
  Button,
  Group,
  Stack,
  Text,
  Checkbox,
  Accordion,
  Card,
  Badge,
  Image,
  Loader,
  Alert,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconCheck,
  IconX,
  IconSearch,
  IconHistory,
  IconAlertCircle,
} from '@tabler/icons-react';
import { MediaFile, mediaApi, TMDBSearchResult, RenameHistoryEntry } from '../services/api';

interface RenameModalProps {
  opened: boolean;
  onClose: () => void;
  file: MediaFile | null;
  onRenameSuccess?: () => void;
}

type RenameMode = 'simple' | 'pattern' | 'findreplace' | 'tmdb';

const PATTERN_OPTIONS = [
  { value: 'title-year', label: '{title} ({year})' },
  { value: 'title-season-episode', label: '{title} - S{season}E{episode}' },
  { value: 'title-year-quality', label: '{title} ({year}) - {quality}' },
  { value: 'mediatype-title', label: '{media_type} - {title}' },
];

export default function RenameModal({ opened, onClose, file, onRenameSuccess }: RenameModalProps) {
  const mediaFile = file;
  const [activeTab, setActiveTab] = useState<RenameMode>('simple');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Simple rename state
  const [newFilename, setNewFilename] = useState('');

  // Pattern rename state
  const [selectedPattern, setSelectedPattern] = useState<string>('title-year');

  // Find/Replace state
  const [findText, setFindText] = useState('');
  const [replaceText, setReplaceText] = useState('');
  const [useRegex, setUseRegex] = useState(false);
  const [caseSensitive, setCaseSensitive] = useState(false);

  // TMDB state
  const [tmdbQuery, setTmdbQuery] = useState('');
  const [tmdbMediaType, setTmdbMediaType] = useState<string>('movie');
  const [tmdbResults, setTmdbResults] = useState<TMDBSearchResult[]>([]);
  const [tmdbLoading, setTmdbLoading] = useState(false);
  const [enrichMetadata, setEnrichMetadata] = useState(true);
  const [selectedTmdbId, setSelectedTmdbId] = useState<number | null>(null);

  // History state
  const [history, setHistory] = useState<RenameHistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Initialize simple rename with current filename
  useEffect(() => {
    if (opened && mediaFile) {
      setNewFilename(mediaFile.filename);
      setError(null);
      setTmdbQuery(mediaFile.parsed_title || '');
      setTmdbMediaType(mediaFile.media_type === 'tv' ? 'tv' : 'movie');
      loadHistory();
    }
  }, [opened, mediaFile]);

  // Load rename history
  const loadHistory = async () => {
    if (!mediaFile) return;
    setHistoryLoading(true);
    try {
      const response = await mediaApi.getRenameHistory(mediaFile.id);
      setHistory(response.data.history || []);
    } catch (err) {
      console.error('Failed to load rename history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  // Get file extension
  const getExtension = () => {
    if (!mediaFile) return '';
    const parts = mediaFile.filename.split('.');
    return parts.length > 1 ? '.' + parts[parts.length - 1] : '';
  };

  // Validate extension matches
  const validateExtension = (filename: string): boolean => {
    const currentExt = getExtension();
    return filename.endsWith(currentExt);
  };

  // Generate preview for pattern rename
  const getPatternPreview = (): string => {
    if (!mediaFile) return '';
    const ext = getExtension();

    switch (selectedPattern) {
      case 'title-year':
        if (!mediaFile.parsed_title) return 'Missing title data';
        return `${mediaFile.parsed_title}${mediaFile.parsed_year ? ` (${mediaFile.parsed_year})` : ''}${ext}`;

      case 'title-season-episode':
        if (!mediaFile.parsed_title) return 'Missing title data';
        // Note: MediaFile doesn't have season/episode fields in current schema
        return 'Season/episode data not available in current schema';

      case 'title-year-quality':
        if (!mediaFile.parsed_title) return 'Missing title data';
        return `${mediaFile.parsed_title}${mediaFile.parsed_year ? ` (${mediaFile.parsed_year})` : ''}${mediaFile.quality_tier ? ` - ${mediaFile.quality_tier}` : ''}${ext}`;

      case 'mediatype-title':
        if (!mediaFile.parsed_title) return 'Missing title data';
        return `${mediaFile.media_type || 'unknown'} - ${mediaFile.parsed_title}${ext}`;

      default:
        return mediaFile.filename;
    }
  };

  // Generate preview for find/replace
  const getFindReplacePreview = (): string => {
    if (!mediaFile) return '';
    if (!findText) return mediaFile.filename;

    try {
      if (useRegex) {
        const flags = caseSensitive ? 'g' : 'gi';
        const regex = new RegExp(findText, flags);
        return mediaFile.filename.replace(regex, replaceText);
      } else {
        if (caseSensitive) {
          return mediaFile.filename.split(findText).join(replaceText);
        } else {
          const regex = new RegExp(findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
          return mediaFile.filename.replace(regex, replaceText);
        }
      }
    } catch (err) {
      return 'Invalid regex pattern';
    }
  };

  // Search TMDB
  const handleTmdbSearch = async () => {
    if (!mediaFile) return;
    if (!tmdbQuery.trim()) {
      setError('Please enter a search query');
      return;
    }

    setTmdbLoading(true);
    setError(null);
    setTmdbResults([]);

    try {
      const response = await mediaApi.tmdbSearch(
        mediaFile.id,
        tmdbQuery,
        tmdbMediaType,
        mediaFile.parsed_year || undefined
      );
      const results = response.data.results || [];
      setTmdbResults(results);
      if (results.length === 0) {
        setError('No results found');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to search TMDB');
    } finally {
      setTmdbLoading(false);
    }
  };

  // Handle rename
  const handleRename = async () => {
    if (!mediaFile) return;
    setLoading(true);
    setError(null);

    try {
      let filenameToUse = '';

      switch (activeTab) {
        case 'simple':
          if (!validateExtension(newFilename)) {
            setError(`Filename must end with ${getExtension()}`);
            setLoading(false);
            return;
          }
          filenameToUse = newFilename;
          break;

        case 'pattern':
          const preview = getPatternPreview();
          if (preview.includes('Missing') || preview.includes('not available')) {
            setError(preview);
            setLoading(false);
            return;
          }
          filenameToUse = preview;
          break;

        case 'findreplace':
          filenameToUse = getFindReplacePreview();
          if (filenameToUse === 'Invalid regex pattern') {
            setError('Invalid regex pattern');
            setLoading(false);
            return;
          }
          break;

        case 'tmdb':
          if (!selectedTmdbId) {
            setError('Please select a result');
            setLoading(false);
            return;
          }
          // TMDB apply handles the rename
          await mediaApi.tmdbApply(mediaFile.id, selectedTmdbId, tmdbMediaType, enrichMetadata);
          notifications.show({
            title: 'Success',
            message: 'File renamed and metadata enriched',
            color: 'green',
          });
          onRenameSuccess?.();
          onClose();
          return;
      }

      // Perform rename for non-TMDB modes
      await mediaApi.renameFile(mediaFile.id, filenameToUse);
      notifications.show({
        title: 'Success',
        message: 'File renamed successfully',
        color: 'green',
      });
      onRenameSuccess?.();
      onClose();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to rename file';
      setError(errorMsg);
      notifications.show({
        title: 'Error',
        message: errorMsg,
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle revert
  const handleRevert = async (historyIndex: number) => {
    if (!mediaFile) return;
    setLoading(true);
    setError(null);

    try {
      await mediaApi.revertRename(mediaFile.id, historyIndex);
      notifications.show({
        title: 'Success',
        message: 'Rename reverted successfully',
        color: 'green',
      });
      onRenameSuccess?.();
      loadHistory();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to revert rename';
      setError(errorMsg);
      notifications.show({
        title: 'Error',
        message: errorMsg,
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  if (!mediaFile) {
    return null;
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Text fw={600} size="lg">Rename File</Text>}
      size="xl"
    >
      <Stack gap="md">
        {error && (
          <Alert icon={<IconAlertCircle size={16} />} color="red" onClose={() => setError(null)} withCloseButton>
            {error}
          </Alert>
        )}

        <Text size="sm" c="dimmed">
          Current: <strong>{mediaFile.filename}</strong>
        </Text>

        <Tabs value={activeTab} onChange={(value) => setActiveTab(value as RenameMode)}>
          <Tabs.List>
            <Tabs.Tab value="simple">Simple Rename</Tabs.Tab>
            <Tabs.Tab value="pattern">Pattern Rename</Tabs.Tab>
            <Tabs.Tab value="findreplace">Find/Replace</Tabs.Tab>
            <Tabs.Tab value="tmdb">TMDB Rename</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="simple" pt="md">
            <Stack gap="sm">
              <TextInput
                label="New Filename"
                placeholder="Enter new filename"
                value={newFilename}
                onChange={(e) => setNewFilename(e.currentTarget.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRename()}
                required
              />
              <Text size="sm" c="dimmed">
                Preview: <strong>{newFilename}</strong>
              </Text>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="pattern" pt="md">
            <Stack gap="sm">
              <Select
                label="Rename Pattern"
                data={PATTERN_OPTIONS}
                value={selectedPattern}
                onChange={(value) => setSelectedPattern(value || 'title-year')}
              />
              <Card withBorder p="sm">
                <Text size="sm" c="dimmed">Preview:</Text>
                <Text size="sm" fw={500}>{getPatternPreview()}</Text>
              </Card>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="findreplace" pt="md">
            <Stack gap="sm">
              <TextInput
                label="Find"
                placeholder="Text to find"
                value={findText}
                onChange={(e) => setFindText(e.currentTarget.value)}
              />
              <TextInput
                label="Replace"
                placeholder="Replacement text"
                value={replaceText}
                onChange={(e) => setReplaceText(e.currentTarget.value)}
              />
              <Group gap="md">
                <Checkbox
                  label="Use regex"
                  checked={useRegex}
                  onChange={(e) => setUseRegex(e.currentTarget.checked)}
                />
                <Checkbox
                  label="Case sensitive"
                  checked={caseSensitive}
                  onChange={(e) => setCaseSensitive(e.currentTarget.checked)}
                />
              </Group>
              <Card withBorder p="sm">
                <Text size="sm" c="dimmed">Before:</Text>
                <Text size="sm">{mediaFile.filename}</Text>
                <Text size="sm" c="dimmed" mt="xs">After:</Text>
                <Text size="sm" fw={500}>{getFindReplacePreview()}</Text>
              </Card>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="tmdb" pt="md">
            <Stack gap="sm">
              <Group align="flex-end">
                <TextInput
                  label="Search TMDB"
                  placeholder="Enter title..."
                  value={tmdbQuery}
                  onChange={(e) => setTmdbQuery(e.currentTarget.value)}
                  style={{ flex: 1 }}
                  onKeyDown={(e) => e.key === 'Enter' && handleTmdbSearch()}
                />
                <Select
                  label="Media Type"
                  data={[
                    { value: 'movie', label: 'Movie' },
                    { value: 'tv', label: 'TV Show' },
                  ]}
                  value={tmdbMediaType}
                  onChange={(value) => setTmdbMediaType(value || 'movie')}
                  style={{ width: 120 }}
                />
                <Button
                  onClick={handleTmdbSearch}
                  loading={tmdbLoading}
                  leftSection={<IconSearch size={16} />}
                >
                  Search
                </Button>
              </Group>

              <Checkbox
                label="Enrich metadata (update title, year, media type in database)"
                checked={enrichMetadata}
                onChange={(e) => setEnrichMetadata(e.currentTarget.checked)}
              />

              {tmdbLoading && (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              )}

              {!tmdbLoading && tmdbResults.length > 0 && (
                <Stack gap="xs" mah={400} style={{ overflowY: 'auto' }}>
                  {tmdbResults.map((result) => {
                    const title = result.title || result.name || 'Unknown';
                    const year = result.release_date?.substring(0, 4) || result.first_air_date?.substring(0, 4);
                    const posterUrl = result.poster_path
                      ? `https://image.tmdb.org/t/p/w92${result.poster_path}`
                      : null;

                    return (
                      <Card
                        key={result.id}
                        withBorder
                        p="sm"
                        style={{
                          cursor: 'pointer',
                          backgroundColor: selectedTmdbId === result.id ? 'var(--mantine-color-blue-light)' : undefined,
                        }}
                        onClick={() => setSelectedTmdbId(result.id)}
                      >
                        <Group wrap="nowrap" align="flex-start">
                          {posterUrl ? (
                            <Image src={posterUrl} w={60} h={90} fit="cover" radius="sm" />
                          ) : (
                            <div style={{ width: 60, height: 90, backgroundColor: '#ddd', borderRadius: 4 }} />
                          )}
                          <Stack gap={4} style={{ flex: 1 }}>
                            <Group gap="xs">
                              <Text fw={600} size="sm">{title}</Text>
                              {year && <Badge size="sm">{year}</Badge>}
                              <Badge size="sm" variant="light">{result.media_type}</Badge>
                            </Group>
                            <Text size="xs" c="dimmed" lineClamp={2}>
                              {result.overview || 'No description available'}
                            </Text>
                            {selectedTmdbId === result.id && (
                              <Badge color="blue" size="sm" leftSection={<IconCheck size={12} />}>
                                Selected
                              </Badge>
                            )}
                          </Stack>
                        </Group>
                      </Card>
                    );
                  })}
                </Stack>
              )}
            </Stack>
          </Tabs.Panel>
        </Tabs>

        {/* Rename History */}
        <Accordion>
          <Accordion.Item value="history">
            <Accordion.Control icon={<IconHistory size={20} />}>
              Rename History {history.length > 0 && `(${history.length})`}
            </Accordion.Control>
            <Accordion.Panel>
              {historyLoading ? (
                <Group justify="center" p="md">
                  <Loader size="sm" />
                </Group>
              ) : history.length === 0 ? (
                <Text size="sm" c="dimmed" ta="center" p="md">
                  No rename history
                </Text>
              ) : (
                <Stack gap="xs">
                  {history.map((entry, index) => (
                    <Card key={index} withBorder p="xs">
                      <Group justify="space-between" wrap="nowrap">
                        <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
                          <Group gap="xs" wrap="nowrap">
                            <Text size="xs" c="dimmed" style={{ flexShrink: 0 }}>From:</Text>
                            <Text size="xs" truncate>{entry.old_filename}</Text>
                          </Group>
                          <Group gap="xs" wrap="nowrap">
                            <Text size="xs" c="dimmed" style={{ flexShrink: 0 }}>To:</Text>
                            <Text size="xs" fw={500} truncate>{entry.new_filename}</Text>
                          </Group>
                          <Text size="xs" c="dimmed">
                            {new Date(entry.renamed_at).toLocaleString()}
                          </Text>
                        </Stack>
                        <Button
                          size="xs"
                          variant="light"
                          onClick={() => handleRevert(index)}
                          disabled={loading}
                        >
                          Revert
                        </Button>
                      </Group>
                    </Card>
                  ))}
                </Stack>
              )}
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>

        {/* Footer Actions */}
        <Group justify="flex-end" mt="md">
          <Button
            variant="subtle"
            onClick={onClose}
            leftSection={<IconX size={16} />}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleRename}
            loading={loading}
            leftSection={<IconCheck size={16} />}
          >
            {activeTab === 'tmdb' ? 'Apply' : 'Rename'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
