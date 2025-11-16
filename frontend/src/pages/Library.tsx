import { useEffect, useState } from 'react';
import {
  Stack,
  Title,
  TextInput,
  Table,
  Badge,
  Group,
  ActionIcon,
  Text,
  Pagination,
  Modal,
  Checkbox,
  Button,
  Paper,
  Tooltip,
} from '@mantine/core';
import { IconSearch, IconTrash, IconInfoCircle, IconPlayerPlay, IconEdit, IconExternalLink, IconChevronUp, IconChevronDown } from '@tabler/icons-react';
import { mediaApi, type MediaFile } from '../services/api';
import { notifications } from '@mantine/notifications';
import { modals } from '@mantine/modals';
import VideoPlayer from '../components/VideoPlayer';
import RenameModal from '../components/RenameModal';
import BatchRenameModal from '../components/BatchRenameModal';

export default function Library() {
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<string>('discovered_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [selectedFile, setSelectedFile] = useState<MediaFile | null>(null);
  const [opened, setOpened] = useState(false);
  const [renameModalOpened, setRenameModalOpened] = useState(false);
  const [selectedFileForRename, setSelectedFileForRename] = useState<MediaFile | null>(null);

  // Batch operations state
  const [selectedFiles, setSelectedFiles] = useState<Set<number>>(new Set());
  const [batchRenameOpened, setBatchRenameOpened] = useState(false);

  const itemsPerPage = 50;

  useEffect(() => {
    loadFiles();
  }, []);

  // Clear selections when filtered files change
  useEffect(() => {
    setSelectedFiles(new Set());
  }, [search, sortColumn, sortDirection]);

  const loadFiles = async () => {
    try {
      setLoading(true);
      const res = await mediaApi.listMedia({ limit: 1000 });
      setFiles(res.data.files || []);
    } catch (error) {
      console.error('Error loading files:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load media files',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (file: MediaFile) => {
    modals.openConfirmModal({
      title: 'Delete Media File',
      children: (
        <Text size="sm">
          Are you sure you want to delete "{file.filename}"? This action cannot be undone.
        </Text>
      ),
      labels: { confirm: 'Delete', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: async () => {
        try {
          await mediaApi.deleteMedia(file.id);
          notifications.show({
            title: 'Success',
            message: 'File queued for deletion',
            color: 'green',
          });
          loadFiles();
        } catch (error: any) {
          notifications.show({
            title: 'Error',
            message: error.response?.data?.detail || 'Failed to delete file',
            color: 'red',
          });
        }
      },
    });
  };

  const handlePlay = (file: MediaFile) => {
    setSelectedFile(file);
    setOpened(true);
  };

  const handleRename = (file: MediaFile) => {
    setSelectedFileForRename(file);
    setRenameModalOpened(true);
  };

  const closeRenameModal = () => {
    setRenameModalOpened(false);
    setSelectedFileForRename(null);
  };

  const handleRenameSuccess = () => {
    loadFiles();
  };

  // Batch selection handlers
  const toggleFileSelection = (fileId: number) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(fileId)) {
      newSelected.delete(fileId);
    } else {
      newSelected.add(fileId);
    }
    setSelectedFiles(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedFiles.size === paginatedFiles.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(paginatedFiles.map(f => f.id)));
    }
  };

  const clearSelection = () => {
    setSelectedFiles(new Set());
  };

  // Batch delete handler
  const handleBatchDelete = () => {
    const selectedCount = selectedFiles.size;
    const fileList = Array.from(selectedFiles).map(id =>
      files.find(f => f.id === id)?.filename || 'Unknown'
    );

    modals.openConfirmModal({
      title: `Delete ${selectedCount} Files`,
      children: (
        <Stack gap="sm">
          <Text size="sm" c="red" fw={500}>
            Are you sure you want to delete {selectedCount} files? This action cannot be undone.
          </Text>
          <Text size="sm" fw={500}>Files to delete:</Text>
          <Paper p="sm" withBorder mah={200} style={{ overflowY: 'auto' }}>
            <Stack gap="xs">
              {fileList.slice(0, 10).map((filename, idx) => (
                <Text key={idx} size="sm">• {filename}</Text>
              ))}
              {fileList.length > 10 && (
                <Text size="sm" c="dimmed">...and {fileList.length - 10} more</Text>
              )}
            </Stack>
          </Paper>
        </Stack>
      ),
      labels: { confirm: `Delete ${selectedCount} Files`, cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: async () => {
        try {
          await mediaApi.batchDelete(Array.from(selectedFiles));
          notifications.show({
            title: 'Success',
            message: `${selectedCount} files queued for deletion`,
            color: 'green',
          });
          clearSelection();
          loadFiles();
        } catch (error: any) {
          notifications.show({
            title: 'Error',
            message: error.response?.data?.detail || 'Failed to delete files',
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

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const getQualityColor = (score: number): string => {
    if (score >= 150) return 'green';
    if (score >= 100) return 'blue';
    if (score >= 50) return 'yellow';
    return 'orange';
  };

  // Parse resolution to numeric value for sorting
  const getResolutionValue = (file: MediaFile): number => {
    const res = file.resolution?.toLowerCase();
    if (res?.includes('4k') || res?.includes('2160')) return 2160;
    if (res?.includes('1080')) return 1080;
    if (res?.includes('720')) return 720;
    if (res?.includes('480')) return 480;
    if (file.height) return file.height;
    return 0;
  };

  // Get codec quality ranking for sorting
  const getCodecValue = (codec: string | null | undefined): number => {
    if (!codec) return 0;
    const c = codec.toLowerCase();
    if (c.includes('hevc') || c.includes('h265') || c.includes('h.265')) return 5;
    if (c.includes('av1')) return 4;
    if (c.includes('h264') || c.includes('h.264') || c.includes('avc')) return 3;
    if (c.includes('vp9')) return 2;
    return 1;
  };

  // Check if file has English audio
  const hasEnglish = (languages: string[] | null | undefined): boolean => {
    if (!languages || languages.length === 0) return false;
    return languages.some(lang =>
      lang.toLowerCase() === 'eng' ||
      lang.toLowerCase() === 'en' ||
      lang.toLowerCase() === 'english'
    );
  };

  // Handle column header click for sorting
  const handleSort = (column: string) => {
    if (sortColumn === column) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New column - set default "best first" direction
      setSortColumn(column);
      setSortDirection('desc'); // Most columns default to descending (best first)
      // Exception: name defaults to ascending (A-Z)
      if (column === 'filename') {
        setSortDirection('asc');
      }
    }
  };

  // Sortable header component with clean minimal design
  const SortableHeader = ({ column, children, width }: { column: string; children: React.ReactNode; width?: string }) => {
    const isActive = sortColumn === column;
    return (
      <Table.Th
        style={{
          cursor: 'pointer',
          userSelect: 'none',
          transition: 'all 0.15s ease',
          width: width,
        }}
        onClick={() => handleSort(column)}
      >
        <Group gap={4} wrap="nowrap">
          <Text
            size="sm"
            fw={isActive ? 600 : 500}
            c={isActive ? 'blue' : 'dimmed'}
            style={{ transition: 'all 0.15s ease' }}
          >
            {children}
          </Text>
          {isActive && (
            <div style={{ opacity: 0.7 }}>
              {sortDirection === 'desc' ? (
                <IconChevronDown size={14} stroke={2.5} />
              ) : (
                <IconChevronUp size={14} stroke={2.5} />
              )}
            </div>
          )}
        </Group>
      </Table.Th>
    );
  };

  const filteredFiles = files
    .filter((file) =>
      file.filename?.toLowerCase().includes(search.toLowerCase()) ||
      file.filepath?.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      let comparison = 0;

      switch (sortColumn) {
        case 'filename':
          comparison = (a.filename || '').localeCompare(b.filename || '');
          break;
        case 'resolution':
          comparison = getResolutionValue(b) - getResolutionValue(a);
          break;
        case 'codec':
          comparison = getCodecValue(b.video_codec) - getCodecValue(a.video_codec);
          break;
        case 'quality_score':
          comparison = (b.quality_score || 0) - (a.quality_score || 0);
          break;
        case 'duration':
          comparison = (b.duration || 0) - (a.duration || 0);
          break;
        case 'file_size':
          comparison = (b.file_size || 0) - (a.file_size || 0);
          break;
        case 'languages':
          // English first, then alphabetical
          const aHasEng = hasEnglish(a.audio_languages);
          const bHasEng = hasEnglish(b.audio_languages);
          if (aHasEng && !bHasEng) comparison = -1;
          else if (!aHasEng && bHasEng) comparison = 1;
          else {
            const aLang = a.audio_languages?.[0] || '';
            const bLang = b.audio_languages?.[0] || '';
            comparison = aLang.localeCompare(bLang);
          }
          break;
        default: // discovered_at
          comparison = new Date(b.discovered_at).getTime() - new Date(a.discovered_at).getTime();
      }

      return sortDirection === 'asc' ? -comparison : comparison;
    });

  const paginatedFiles = filteredFiles.slice((page - 1) * itemsPerPage, page * itemsPerPage);
  const totalPages = Math.ceil(filteredFiles.length / itemsPerPage);
  const selectedCount = selectedFiles.size;
  const allPageFilesSelected = paginatedFiles.length > 0 && paginatedFiles.every(f => selectedFiles.has(f.id));
  const somePageFilesSelected = paginatedFiles.some(f => selectedFiles.has(f.id)) && !allPageFilesSelected;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={2}>Media Library</Title>
        <Text c="dimmed">{filteredFiles.length} files</Text>
      </Group>

      <TextInput
        placeholder="Search files..."
        leftSection={<IconSearch size={16} />}
        value={search}
        onChange={(e) => setSearch(e.currentTarget.value)}
      />

      {/* Batch Action Bar */}
      {selectedCount > 0 && (
        <Paper p="md" withBorder bg="blue.0">
          <Group justify="space-between">
            <Group>
              <Badge size="lg" variant="filled">
                {selectedCount} file{selectedCount !== 1 ? 's' : ''} selected
              </Badge>
              <Button variant="subtle" size="sm" onClick={clearSelection}>
                Clear Selection
              </Button>
            </Group>
            <Group>
              <Button
                variant="filled"
                onClick={() => setBatchRenameOpened(true)}
                disabled={selectedCount === 0}
              >
                Batch Rename
              </Button>
              <Button
                variant="filled"
                color="red"
                onClick={handleBatchDelete}
                disabled={selectedCount === 0}
              >
                Batch Delete
              </Button>
            </Group>
          </Group>
        </Paper>
      )}

      {loading ? (
        <Text c="dimmed">Loading...</Text>
      ) : paginatedFiles.length === 0 ? (
        <Text c="dimmed">No files found. Run a scan to populate the library.</Text>
      ) : (
        <>
          <Table striped highlightOnHover style={{ tableLayout: 'fixed', width: '100%' }}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th style={{ width: '3%' }}>
                  <Checkbox
                    checked={allPageFilesSelected}
                    indeterminate={somePageFilesSelected}
                    onChange={toggleSelectAll}
                    aria-label="Select all files on this page"
                  />
                </Table.Th>
                <SortableHeader column="filename" width="30%">Name</SortableHeader>
                <SortableHeader column="resolution" width="10%">Resolution</SortableHeader>
                <SortableHeader column="codec" width="10%">Codec</SortableHeader>
                <SortableHeader column="quality_score" width="8%">Quality</SortableHeader>
                <SortableHeader column="duration" width="10%">Duration</SortableHeader>
                <SortableHeader column="file_size" width="10%">Size</SortableHeader>
                <SortableHeader column="languages" width="12%">Languages</SortableHeader>
                <Table.Th style={{ width: '7%' }}>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {paginatedFiles.map((file) => (
                <Table.Tr key={file.id}>
                  <Table.Td>
                    <Checkbox
                      checked={selectedFiles.has(file.id)}
                      onChange={() => toggleFileSelection(file.id)}
                      aria-label={`Select ${file.filename}`}
                    />
                  </Table.Td>
                  <Table.Td style={{ overflow: 'hidden' }}>
                    <Text size="sm" lineClamp={1} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {file.filename}
                    </Text>
                    {file.parsed_title && (
                      <Text size="xs" c="dimmed" lineClamp={1} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {file.parsed_title} {file.parsed_year && `(${file.parsed_year})`}
                      </Text>
                    </Tooltip>
                    {file.parsed_title && (
                      <Tooltip
                        label={`${file.parsed_title}${file.parsed_year ? ` (${file.parsed_year})` : ''}`}
                        withArrow
                        position="bottom-start"
                      >
                        <Text size="xs" c="dimmed" lineClamp={1} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'help' }}>
                          {file.parsed_title} {file.parsed_year && `(${file.parsed_year})`}
                        </Text>
                      </Tooltip>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="light">
                      {file.resolution || `${file.width}x${file.height}` || 'Unknown'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="outline" size="sm">
                      {file.video_codec?.toUpperCase() || 'Unknown'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={getQualityColor(file.quality_score || 0)}>
                      {file.quality_score || 0}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{file.duration ? formatDuration(file.duration) : 'N/A'}</Table.Td>
                  <Table.Td>{formatBytes(file.file_size)}</Table.Td>
                  <Table.Td style={{ overflow: 'hidden' }}>
                    <Group gap="xs" wrap="wrap">
                      {file.audio_languages?.map((lang) => (
                        <Badge key={lang} size="xs" variant="dot">
                          {lang}
                        </Badge>
                      ))}
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4} wrap="nowrap">
                      <ActionIcon
                        variant="subtle"
                        color="blue"
                        size="sm"
                        onClick={() => handlePlay(file)}
                      >
                        <IconPlayerPlay size={16} />
                      </ActionIcon>
                      <ActionIcon
                        variant="subtle"
                        color="blue"
                        size="sm"
                        onClick={() => handleRename(file)}
                      >
                        <IconEdit size={16} />
                      </ActionIcon>
                      <ActionIcon
                        variant="subtle"
                        size="sm"
                        onClick={() => {
                          modals.open({
                            title: 'File Details',
                            children: (
                              <Stack gap="xs">
                                <Text size="sm"><strong>Path:</strong> {file.filepath}</Text>
                                <Text size="sm">
                                  <strong>Codec:</strong> {file.video_codec || 'Unknown'} / {file.audio_codec || 'Unknown'}
                                </Text>
                                <Text size="sm">
                                  <strong>Bitrate:</strong> {file.bitrate ? `${Math.round(file.bitrate / 1000)} Mbps` : 'N/A'}
                                </Text>
                                <Text size="sm">
                                  <strong>Audio Channels:</strong> {file.audio_channels || 'N/A'}
                                </Text>
                                <Group gap="xs">
                                  <Text size="sm">
                                    <strong>MD5:</strong> {file.md5_hash ? 'Yes' : 'Not calculated'}
                                  </Text>
                                  {file.md5_hash && (
                                    <Badge
                                      variant="light"
                                      style={{ cursor: 'pointer' }}
                                      onClick={() => {
                                        navigator.clipboard.writeText(file.md5_hash || '');
                                        notifications.show({
                                          title: 'MD5 Hash',
                                          message: file.md5_hash,
                                          color: 'blue',
                                          autoClose: 5000,
                                        });
                                      }}
                                    >
                                      Copy Hash
                                    </Badge>
                                  )}
                                </Group>
                                {(file.tmdb_id || file.imdb_id || file.parsed_title) && (
                                  <Group gap="xs" mt="md">
                                    {/* TMDb Link */}
                                    {file.tmdb_id ? (
                                      <Button
                                        variant="light"
                                        size="sm"
                                        color="blue"
                                        leftSection={<IconExternalLink size={16} />}
                                        onClick={() => {
                                          const type = file.tmdb_type || file.media_type || 'movie';
                                          window.open(`https://www.themoviedb.org/${type}/${file.tmdb_id}`, '_blank');
                                        }}
                                      >
                                        View on TMDb
                                      </Button>
                                    ) : file.parsed_title && (
                                      <Button
                                        variant="light"
                                        size="sm"
                                        color="blue"
                                        leftSection={<IconExternalLink size={16} />}
                                        onClick={() => {
                                          const searchQuery = encodeURIComponent(
                                            file.parsed_title + (file.parsed_year ? ` ${file.parsed_year}` : '')
                                          );
                                          window.open(`https://www.themoviedb.org/search?query=${searchQuery}`, '_blank');
                                        }}
                                      >
                                        Search TMDb
                                      </Button>
                                    )}

                                    {/* IMDB Link */}
                                    {file.imdb_id && (
                                      <Button
                                        variant="light"
                                        size="sm"
                                        color="yellow"
                                        leftSection={<IconExternalLink size={16} />}
                                        onClick={() => {
                                          window.open(`https://www.imdb.com/title/${file.imdb_id}/`, '_blank');
                                        }}
                                      >
                                        View on IMDB
                                      </Button>
                                    )}
                                  </Group>
                                )}
                              </Stack>
                            ),
                          });
                        }}
                      >
                        <IconInfoCircle size={16} />
                      </ActionIcon>
                      <ActionIcon variant="subtle" color="red" size="sm" onClick={() => handleDelete(file)}>
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>

          <Group justify="center">
            <Pagination value={page} onChange={setPage} total={totalPages} />
          </Group>
        </>
      )}

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title="Video Player"
        size="xl"
        centered
      >
        {selectedFile && (
          <VideoPlayer
            fileId={selectedFile.id}
            filename={selectedFile.filename}
            quality={selectedFile.quality_score ?? undefined}
            resolution={selectedFile.resolution ?? undefined}
            codec={selectedFile.video_codec ?? undefined}
            useSmartStream={true}
          />
        )}
      </Modal>

      <RenameModal
        opened={renameModalOpened}
        onClose={closeRenameModal}
        file={selectedFileForRename}
        onRenameSuccess={handleRenameSuccess}
      />

      <BatchRenameModal
        opened={batchRenameOpened}
        onClose={() => setBatchRenameOpened(false)}
        files={files.filter(f => selectedFiles.has(f.id))}
        onSuccess={() => {
          clearSelection();
          loadFiles();
        }}
      />
    </Stack>
  );
}
