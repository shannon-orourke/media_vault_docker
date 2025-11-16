import { useEffect, useState } from 'react';
import { Grid, Card, Text, Title, Group, Stack, Badge, RingProgress, Table, ThemeIcon, Skeleton } from '@mantine/core';
import { IconVideo, IconCopy, IconFileAlert, IconScan } from '@tabler/icons-react';
import { mediaApi, type ScanHistory } from '../services/api';
import { notifications } from '@mantine/notifications';

interface Stats {
  totalFiles: number;
  duplicateGroups: number;
  totalSize: string;
  lastScan: string | null;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>({
    totalFiles: 0,
    duplicateGroups: 0,
    totalSize: '0 GB',
    lastScan: null,
  });
  const [recentScans, setRecentScans] = useState<ScanHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      // Load media stats
      const mediaRes = await mediaApi.listMedia({ limit: 1000 });
      const files = mediaRes.data.files || [];
      const totalFiles = mediaRes.data.total || 0;
      const totalSize = files.reduce((sum, file) => sum + (file.file_size || 0), 0);

      // Load scan history
      const scansRes = await mediaApi.getScanHistory(5);
      const scans = scansRes.data;
      setRecentScans(scans);

      // Load duplicate groups
      const dupsRes = await mediaApi.listDuplicateGroups();
      const duplicateGroups = dupsRes.data.total || 0;

      setStats({
        totalFiles,
        duplicateGroups,
        totalSize: formatBytes(totalSize),
        lastScan: scans.length > 0 ? scans[0].scan_started_at : null,
      });
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load dashboard data',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 GB';
    const gb = bytes / (1024 ** 3);
    return `${gb.toFixed(2)} GB`;
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <Stack gap="md">
      <Title order={1} style={{ fontWeight: 700, fontSize: '32px', letterSpacing: '-0.03em' }}>Dashboard</Title>

      <Grid>
        <Grid.Col span={{ base: 12, md: 6, lg: 3 }}>
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between" mb="md">
              <Text size="sm" c="dimmed" fw={600} tt="uppercase" style={{ letterSpacing: '0.05em' }}>Total Files</Text>
              <ThemeIcon size={48} radius="md" variant="light" color="blue">
                <IconVideo size={28} stroke={2} />
              </ThemeIcon>
            </Group>
            {loading ? (
              <Skeleton height={40} mb="xs" />
            ) : (
              <Title order={1} c="portainerBlue.6" style={{ fontSize: '36px', fontWeight: 700 }}>{stats.totalFiles}</Title>
            )}
            <Text size="sm" c="dimmed" mt="xs">{stats.totalSize}</Text>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6, lg: 3 }}>
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between" mb="md">
              <Text size="sm" c="dimmed" fw={600} tt="uppercase" style={{ letterSpacing: '0.05em' }}>Duplicate Groups</Text>
              <ThemeIcon size={48} radius="md" variant="light" color="warningAmber.6">
                <IconCopy size={28} stroke={2} />
              </ThemeIcon>
            </Group>
            {loading ? (
              <Skeleton height={40} mb="xs" />
            ) : (
              <Title order={1} c="warningAmber.6" style={{ fontSize: '36px', fontWeight: 700 }}>{stats.duplicateGroups}</Title>
            )}
            <Text size="sm" c="dimmed" mt="xs">Needs review</Text>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6, lg: 3 }}>
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between" mb="md">
              <Text size="sm" c="dimmed" fw={600} tt="uppercase" style={{ letterSpacing: '0.05em' }}>Last Scan</Text>
              <ThemeIcon size={48} radius="md" variant="light" color="cyan">
                <IconScan size={28} stroke={2} />
              </ThemeIcon>
            </Group>
            {loading ? (
              <Skeleton height={40} mb="xs" />
            ) : (
              <Text size="md" fw={600} mt="sm">
                {stats.lastScan ? formatDate(stats.lastScan) : 'Never'}
              </Text>
            )}
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6, lg: 3 }}>
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between" mb="md">
              <Text size="sm" c="dimmed" fw={600} tt="uppercase" style={{ letterSpacing: '0.05em' }}>Storage Health</Text>
              <ThemeIcon size={48} radius="md" variant="light" color="successGreen.6">
                <IconFileAlert size={28} stroke={2} />
              </ThemeIcon>
            </Group>
            {loading ? (
              <Skeleton height={60} />
            ) : (
              <Group mt="sm">
                <RingProgress
                  size={70}
                  thickness={8}
                  sections={[{ value: 75, color: 'successGreen.6' }]}
                  label={
                    <Text c="successGreen.6" fw={700} ta="center" size="lg">
                      75%
                    </Text>
                  }
                />
                <Text size="sm" c="dimmed" fw={500}>organized</Text>
              </Group>
            )}
          </Card>
        </Grid.Col>
      </Grid>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Title order={3} mb="md" style={{ fontWeight: 600, fontSize: '20px' }}>Recent Scans</Title>
        {loading ? (
          <Stack gap="sm">
            <Skeleton height={40} />
            <Skeleton height={40} />
            <Skeleton height={40} />
          </Stack>
        ) : recentScans.length === 0 ? (
          <Text c="dimmed">No scans yet. Start a scan from the Scanner page.</Text>
        ) : (
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Started</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Files Found</Table.Th>
                <Table.Th>New</Table.Th>
                <Table.Th>Updated</Table.Th>
                <Table.Th>Errors</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {recentScans.map((scan) => (
                <Table.Tr key={scan.id}>
                  <Table.Td>{formatDate(scan.scan_started_at)}</Table.Td>
                  <Table.Td>
                    <Badge variant="light">{scan.scan_type}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={scan.status === 'completed' ? 'green' : scan.status === 'running' ? 'blue' : 'red'}>
                      {scan.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{scan.files_found}</Table.Td>
                  <Table.Td>{scan.files_new}</Table.Td>
                  <Table.Td>{scan.files_updated}</Table.Td>
                  <Table.Td>{scan.errors_count}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}
