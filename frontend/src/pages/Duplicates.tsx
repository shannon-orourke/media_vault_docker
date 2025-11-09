import { useEffect, useState } from 'react';
import {
  Stack,
  Title,
  Card,
  Text,
  Badge,
  Group,
  Button,
  Accordion,
  Table,
} from '@mantine/core';
import { IconCheck, IconX } from '@tabler/icons-react';
import { mediaApi, type DuplicateGroup, type DuplicateMember } from '../services/api';
import { notifications } from '@mantine/notifications';
import { modals } from '@mantine/modals';

interface GroupWithMembers {
  group: DuplicateGroup & { members?: DuplicateMember[] };
  members: DuplicateMember[];
}

export default function Duplicates() {
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Record<number, GroupWithMembers>>({});
  const [loading, setLoading] = useState(true);
  const [mutatingGroup, setMutatingGroup] = useState<number | null>(null);

  useEffect(() => {
    loadGroups();
  }, []);

  const loadGroups = async () => {
    try {
      setLoading(true);
      const res = await mediaApi.listDuplicateGroups();
      setGroups(res.data.groups || []);
    } catch (error) {
      console.error('Error loading duplicate groups:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load duplicate groups',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const loadGroupDetails = async (groupId: number) => {
    if (expandedGroups[groupId]) return;

    try {
      const res = await mediaApi.getDuplicateGroup(groupId);
      const groupData = res.data;
      const newState: Record<number, GroupWithMembers> = {
        ...expandedGroups,
        [groupId]: {
          group: groupData as any,
          members: groupData.members || [],
        },
      };
      setExpandedGroups(newState);
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to load group details',
        color: 'red',
      });
    }
  };

  const handleKeep = async (groupId: number, fileId: number) => {
    try {
      setMutatingGroup(groupId);
      await mediaApi.keepFile(groupId, fileId);
      notifications.show({
        title: 'Success',
        message: 'File marked as keeper',
        color: 'green',
      });
      // Reload group details
      const res = await mediaApi.getDuplicateGroup(groupId);
      const groupData = res.data;
      const newState: Record<number, GroupWithMembers> = {
        ...expandedGroups,
        [groupId]: {
          group: groupData as any,
          members: groupData.members || [],
        },
      };
      setExpandedGroups(newState);
    } catch (error: any) {
      notifications.show({
        title: 'Error',
        message: error.response?.data?.detail || 'Failed to mark file as keeper',
        color: 'red',
      });
    } finally {
      setMutatingGroup(null);
    }
  };

  const handleDismiss = (groupId: number) => {
    modals.openConfirmModal({
      title: 'Dismiss Duplicate Group',
      children: (
        <Text size="sm">
          Are you sure you want to dismiss this duplicate group? This will remove it from the review queue.
        </Text>
      ),
      labels: { confirm: 'Dismiss', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: async () => {
        try {
          setMutatingGroup(groupId);
          await mediaApi.dismissGroup(groupId);
          notifications.show({
            title: 'Success',
            message: 'Group dismissed',
            color: 'green',
          });
          loadGroups();
        } catch (error: any) {
          notifications.show({
            title: 'Error',
            message: error.response?.data?.detail || 'Failed to dismiss group',
            color: 'red',
          });
        } finally {
          setMutatingGroup(null);
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

  const getQualityColor = (score: number): string => {
    if (score >= 150) return 'green';
    if (score >= 100) return 'blue';
    if (score >= 50) return 'yellow';
    return 'orange';
  };

  const getConfidenceColor = (score: number): string => {
    if (score >= 0.9) return 'green';
    if (score >= 0.7) return 'yellow';
    return 'orange';
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={2}>Duplicate Groups</Title>
        <Text c="dimmed">{groups.length} groups</Text>
      </Group>

      {loading ? (
        <Text c="dimmed">Loading...</Text>
      ) : groups.length === 0 ? (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Text c="dimmed">No duplicate groups found. Run a scan and then deduplicate to find duplicates.</Text>
        </Card>
      ) : (
        <Accordion
          variant="contained"
          onChange={(value) => {
            if (value) {
              const groupId = parseInt(value);
              loadGroupDetails(groupId);
            }
          }}
        >
          {groups.map((group) => (
            <Accordion.Item key={group.id} value={group.id.toString()}>
              <Accordion.Control>
                <Group justify="space-between">
                  <div>
                    <Text fw={500}>
                      {group.title || 'Exact Match Group'}{' '}
                      {group.year && `(${group.year})`}
                    </Text>
                    <Text size="sm" c="dimmed">
                      {group.member_count} duplicates · {group.duplicate_type}
                    </Text>
                    {group.action_reason && (
                      <Text size="xs" c="dimmed">
                        {group.action_reason}
                      </Text>
                    )}
                  </div>
                  <Badge color={getConfidenceColor(group.confidence || 0)}>
                    {((group.confidence || 0) * 100).toFixed(0)}% confidence
                  </Badge>
                </Group>
              </Accordion.Control>
              <Accordion.Panel>
                {expandedGroups[group.id] ? (
                  <Stack gap="md">
                    <Table>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>File Name</Table.Th>
                          <Table.Th>Resolution</Table.Th>
                          <Table.Th>Quality</Table.Th>
                          <Table.Th>Size</Table.Th>
                          <Table.Th>Languages</Table.Th>
                          <Table.Th>Status</Table.Th>
                          <Table.Th>Actions</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {expandedGroups[group.id].members.map((member, idx) => (
                          <Table.Tr key={idx}>
                            <Table.Td>
                              <Text size="sm" lineClamp={1} maw={300}>
                                {member.file.filename}
                              </Text>
                            </Table.Td>
                            <Table.Td>
                              <Badge variant="light">
                                {member.file.resolution || `${member.file.width}x${member.file.height}` || 'Unknown'}
                              </Badge>
                            </Table.Td>
                            <Table.Td>
                              <Badge color={getQualityColor(member.file.quality_score || 0)}>
                                {member.file.quality_score || 0}
                              </Badge>
                            </Table.Td>
                            <Table.Td>{formatBytes(member.file.file_size)}</Table.Td>
                            <Table.Td>
                              <Group gap="xs">
                                {member.file.audio_languages?.map((lang: string) => (
                                  <Badge key={lang} size="xs" variant="dot">
                                    {lang}
                                  </Badge>
                                ))}
                              </Group>
                            </Table.Td>
                            <Table.Td>
                              {member.recommended_action === 'keep' ? (
                                <Badge color="green" leftSection={<IconCheck size={14} />}>
                                  Keeper
                                </Badge>
                              ) : (
                                <Badge color="gray">Review</Badge>
                              )}
                              {member.action_reason && (
                                <Text size="xs" c="dimmed">
                                  {member.action_reason}
                                </Text>
                              )}
                            </Table.Td>
                            <Table.Td>
                              <Group gap="xs">
                                {member.recommended_action !== 'keep' && (
                                  <Button
                                    size="xs"
                                    variant="light"
                                    color="green"
                                    leftSection={<IconCheck size={16} />}
                                    onClick={() => handleKeep(group.id, member.file.id)}
                                    loading={mutatingGroup === group.id}
                                    disabled={mutatingGroup === group.id}
                                  >
                                    Keep
                                  </Button>
                                )}
                              </Group>
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>

                    <Group justify="flex-end">
                      <Button
                        variant="light"
                        color="red"
                        leftSection={<IconX size={16} />}
                        onClick={() => handleDismiss(group.id)}
                        loading={mutatingGroup === group.id}
                        disabled={mutatingGroup === group.id}
                      >
                        Dismiss Group
                      </Button>
                    </Group>
                  </Stack>
                ) : (
                  <Text c="dimmed">Loading...</Text>
                )}
              </Accordion.Panel>
            </Accordion.Item>
          ))}
        </Accordion>
      )}
    </Stack>
  );
}
