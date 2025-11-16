import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AppShell, Group, Title, NavLink, Container, ActionIcon, Tooltip } from '@mantine/core';
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
      header={{ height: 60 }}
      navbar={{
        width: 250,
        breakpoint: 'sm',
        collapsed: { mobile: !opened, desktop: !opened }
      }}
      padding="md"
      transitionDuration={300}
      transitionTimingFunction="ease-in-out"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="md">
            <Tooltip
              label={opened ? 'Hide sidebar' : 'Show sidebar'}
              position="right"
              withArrow
              transitionProps={{ transition: 'fade', duration: 200 }}
            >
              <ActionIcon
                onClick={toggle}
                variant="subtle"
                size="lg"
                color="gray"
                style={{
                  transition: 'all 200ms ease-in-out',
                }}
              >
                {opened ? (
                  <IconLayoutSidebarLeftCollapse size={22} stroke={1.5} />
                ) : (
                  <IconLayoutSidebarLeftExpand size={22} stroke={1.5} />
                )}
              </ActionIcon>
            </Tooltip>
            <Title order={3} style={{ fontWeight: 500 }}>MediaVault</Title>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            component="button"
            label={item.label}
            leftSection={<item.icon size={20} />}
            active={location.pathname === item.path}
            onClick={() => navigate(item.path)}
            mb="xs"
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Container size="xl" style={{ flex: 1, width: '100%' }}>
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
        </Container>
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
