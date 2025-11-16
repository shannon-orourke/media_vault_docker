import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AppShell, Group, Title, NavLink, ActionIcon, Tooltip, Box, Stack } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconHome,
  IconVideo,
  IconCopy,
  IconSettings,
  IconScan,
  IconPackage,
  IconTrash,
  IconLayoutSidebarLeftCollapse,
  IconLayoutSidebarLeftExpand,
} from '@tabler/icons-react';
import Dashboard from './pages/Dashboard';
import Library from './pages/Library';
import Duplicates from './pages/Duplicates';
import Scanner from './pages/Scanner';
import Settings from './pages/Settings';
import Unarchive from './pages/Unarchive';
import PendingDeletions from './pages/PendingDeletions';

function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [opened, { toggle }] = useDisclosure(true);

  const navItems = [
    { icon: IconHome, label: 'Dashboard', path: '/dashboard' },
    { icon: IconVideo, label: 'Library', path: '/library' },
    { icon: IconCopy, label: 'Duplicates', path: '/duplicates' },
    { icon: IconPackage, label: 'Unarchive', path: '/unarchive' },
    { icon: IconTrash, label: 'Pending Deletions', path: '/pending-deletions' },
    { icon: IconScan, label: 'Scanner', path: '/scanner' },
    { icon: IconSettings, label: 'Settings', path: '/settings' },
  ];

  return (
    <AppShell
      header={{ height: 50 }}
      navbar={{
        width: 260,
        breakpoint: 'sm',
        collapsed: { mobile: !opened, desktop: !opened }
      }}
      padding={0}
      transitionDuration={300}
      transitionTimingFunction="ease-in-out"
      styles={{
        header: {
          backgroundColor: '#1a1a1a',
          borderBottom: '1px solid #2d2d2d',
          padding: 0,
        },
        navbar: {
          backgroundColor: '#151515',
          borderRight: '1px solid #2d2d2d',
        },
        main: {
          backgroundColor: '#0f0f0f',
          minHeight: '100vh',
        },
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="lg" justify="space-between">
          <Group gap="sm">
            <Tooltip
              label={opened ? 'Hide sidebar' : 'Show sidebar'}
              position="right"
              withArrow
              transitionProps={{ transition: 'fade', duration: 200 }}
            >
              <ActionIcon
                onClick={toggle}
                variant="subtle"
                size="md"
                color="gray"
                style={{
                  transition: 'all 200ms ease-in-out',
                  color: '#a0a0a0',
                }}
              >
                {opened ? (
                  <IconLayoutSidebarLeftCollapse size={20} stroke={1.5} />
                ) : (
                  <IconLayoutSidebarLeftExpand size={20} stroke={1.5} />
                )}
              </ActionIcon>
            </Tooltip>
            <Box style={{
              width: 2,
              height: 24,
              backgroundColor: '#2d2d2d',
              borderRadius: 2,
            }} />
            <Title
              order={4}
              style={{
                fontWeight: 700,
                color: '#ffffff',
                letterSpacing: '-0.03em',
              }}
            >
              MediaVault
            </Title>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md" style={{ paddingTop: '1rem' }}>
        <Stack gap="xs">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              component="button"
              label={item.label}
              leftSection={<item.icon size={20} stroke={2.0} />}
              active={location.pathname === item.path}
              onClick={() => navigate(item.path)}
              style={{
                borderRadius: '6px',
                fontSize: '14px',
              }}
            />
          ))}
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main>
        <Box style={{ padding: '24px', minHeight: 'calc(100vh - 50px)' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/library" element={<Library />} />
            <Route path="/duplicates" element={<Duplicates />} />
            <Route path="/unarchive" element={<Unarchive />} />
            <Route path="/pending-deletions" element={<PendingDeletions />} />
            <Route path="/scanner" element={<Scanner />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Box>
      </AppShell.Main>
    </AppShell>
  );
}

function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  );
}

export default App;
