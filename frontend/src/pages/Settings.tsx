import { Stack, Title, Card, Text, Group, Badge, Code } from '@mantine/core';
import { IconDatabase, IconServer, IconCloud } from '@tabler/icons-react';

export default function Settings() {
  return (
    <Stack gap="md">
      <Title order={2}>Settings</Title>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Group mb="md">
          <IconServer size={24} />
          <Title order={4}>NAS Configuration</Title>
        </Group>
        <Stack gap="xs">
          <Group>
            <Text size="sm" fw={500} w={150}>Host:</Text>
            <Code>10.27.10.11</Code>
          </Group>
          <Group>
            <Text size="sm" fw={500} w={150}>Username:</Text>
            <Code>ProxmoxBackupsSMB</Code>
          </Group>
          <Group>
            <Text size="sm" fw={500} w={150}>Scan Paths:</Text>
            <Stack gap="xs">
              <Code>/volume1/docker</Code>
              <Code>/volume1/videos</Code>
            </Stack>
          </Group>
          <Group>
            <Text size="sm" fw={500} w={150}>Archive Path:</Text>
            <Code>/volume1/video/duplicates_before_purge/</Code>
          </Group>
        </Stack>
      </Card>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Group mb="md">
          <IconDatabase size={24} />
          <Title order={4}>Database</Title>
        </Group>
        <Stack gap="xs">
          <Group>
            <Text size="sm" fw={500} w={150}>Host:</Text>
            <Code>localhost:5433</Code>
          </Group>
          <Group>
            <Text size="sm" fw={500} w={150}>Database:</Text>
            <Code>mediavault</Code>
          </Group>
          <Group>
            <Text size="sm" fw={500} w={150}>Status:</Text>
            <Badge color="green">Connected</Badge>
          </Group>
        </Stack>
      </Card>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Group mb="md">
          <IconCloud size={24} />
          <Title order={4}>External APIs</Title>
        </Group>
        <Stack gap="xs">
          <Group>
            <Text size="sm" fw={500} w={150}>TMDb:</Text>
            <Badge color="green">Configured</Badge>
          </Group>
          <Group>
            <Text size="sm" fw={500} w={150}>Azure OpenAI:</Text>
            <Badge color="green">Configured</Badge>
          </Group>
          <Group>
            <Text size="sm" fw={500} w={150}>Langfuse:</Text>
            <Badge color="blue">Optional</Badge>
          </Group>
        </Stack>
      </Card>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Title order={4} mb="md">Deletion Policy</Title>
        <Text size="sm" mb="xs">
          <strong>Auto-Delete:</strong> <Badge color="red">DISABLED</Badge>
        </Text>
        <Text size="sm" c="dimmed">
          All deletion decisions require manual approval. Files are moved to a temporary staging area
          before final deletion. This ensures you never lose important files accidentally.
        </Text>
        <Text size="sm" c="dimmed" mt="xs">
          <strong>Language Policy:</strong> The system will never delete the only English version of a file.
          If multiple duplicates exist and only one has English audio, it will be automatically marked as the keeper.
        </Text>
      </Card>
    </Stack>
  );
}
