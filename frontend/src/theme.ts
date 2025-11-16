import { createTheme, MantineColorsTuple } from '@mantine/core';

// Portainer-inspired color palette
const navyBlue: MantineColorsTuple = [
  '#e8f0ff',
  '#c5d9ff',
  '#9fbfff',
  '#79a5ff',
  '#538bff',
  '#2d71ff',
  '#1e5ee6',
  '#1349b8',
  '#0b3891',
  '#052769',
];

const portainerBlue: MantineColorsTuple = [
  '#e5f4ff',
  '#cde4ff',
  '#9bc5ff',
  '#64a5ff',
  '#3889fe',
  '#1d76fe',
  '#0c6bff',
  '#005ae4',
  '#004fcd',
  '#0043b6',
];

const darkGray: MantineColorsTuple = [
  '#f5f5f5',
  '#e7e7e7',
  '#cdcdcd',
  '#b2b2b2',
  '#9a9a9a',
  '#8b8b8b',
  '#848484',
  '#717171',
  '#656565',
  '#575757',
];

export const theme = createTheme({
  primaryColor: 'portainerBlue',
  colors: {
    navyBlue,
    portainerBlue,
    darkGray,
  },
  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  defaultRadius: 'sm',

  components: {
    AppShell: {
      styles: {
        header: {
          backgroundColor: '#1a1a1a',
          borderBottom: '1px solid #2d2d2d',
        },
        navbar: {
          backgroundColor: '#151515',
          borderRight: '1px solid #2d2d2d',
        },
        main: {
          backgroundColor: '#0f0f0f',
        },
      },
    },
    NavLink: {
      styles: () => ({
        root: {
          borderRadius: '6px',
          color: '#a0a0a0',
          fontWeight: 500,
          padding: '10px 12px',
          '&:hover': {
            backgroundColor: '#1f1f1f',
            color: '#ffffff',
          },
          '&[data-active]': {
            backgroundColor: '#1e5ee6',
            color: '#ffffff',
            '&:hover': {
              backgroundColor: '#1e5ee6',
            },
          },
        },
        label: {
          fontSize: '14px',
        },
      }),
    },
    Button: {
      styles: {
        root: {
          fontWeight: 500,
        },
      },
    },
    Card: {
      styles: {
        root: {
          backgroundColor: '#1a1a1a',
          borderColor: '#2d2d2d',
        },
      },
    },
    Table: {
      styles: {
        table: {
          backgroundColor: '#1a1a1a',
        },
        thead: {
          backgroundColor: '#151515',
          borderBottom: '2px solid #2d2d2d',
        },
        tr: {
          borderBottom: '1px solid #2d2d2d',
          '&:hover': {
            backgroundColor: '#1f1f1f',
          },
        },
      },
    },
    Paper: {
      styles: {
        root: {
          backgroundColor: '#1a1a1a',
          borderColor: '#2d2d2d',
        },
      },
    },
  },
});
