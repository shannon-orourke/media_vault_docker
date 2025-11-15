import { useRef, useEffect, useState } from 'react';
import 'plyr/dist/plyr.css';
import { Box, Text, Badge, Group, Stack, Alert, Loader, Center } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';

interface VideoPlayerProps {
  fileId: number;
  filename: string;
  quality?: number;
  resolution?: string;
  codec?: string;
  showMetadata?: boolean;
  useSmartStream?: boolean;    // Use smart streaming (auto progressive or direct)
}

export default function VideoPlayer({
  fileId,
  filename,
  quality,
  resolution,
  codec,
  showMetadata = true,
  useSmartStream = true
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const setupPlayer = async () => {
      if (!videoRef.current || playerRef.current) return;

      try {
        const PlyrModule: any = await import('plyr');
        if (cancelled) return;

        const PlyrClass = PlyrModule.default ?? (PlyrModule as any);
        playerRef.current = new PlyrClass(videoRef.current, {
          controls: [
            'play-large',
            'play',
            'progress',
            'current-time',
            'duration',
            'mute',
            'volume',
            'settings',
            'pip',
            'airplay',
            'fullscreen'
          ],
          settings: ['speed', 'loop'],
          speed: {
            selected: 1,
            options: [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]
          },
          ratio: '16:9',
          storage: { enabled: true, key: 'mediavault-player' }
        });

        // Add event listeners
        if (videoRef.current) {
          videoRef.current.addEventListener('loadeddata', () => {
            setLoading(false);
            setError(null);
          });

          videoRef.current.addEventListener('error', (e: any) => {
            const video = e.target as HTMLVideoElement;
            let errorMessage = 'Failed to load video';

            if (video.error) {
              switch (video.error.code) {
                case video.error.MEDIA_ERR_ABORTED:
                  errorMessage = 'Video playback was aborted';
                  break;
                case video.error.MEDIA_ERR_NETWORK:
                  errorMessage = 'Network error while loading video';
                  break;
                case video.error.MEDIA_ERR_DECODE:
                  errorMessage = 'Video decoding failed (codec not supported)';
                  break;
                case video.error.MEDIA_ERR_SRC_NOT_SUPPORTED:
                  errorMessage = 'Video format not supported or file not found';
                  break;
              }
            }

            setLoading(false);
            setError(errorMessage);
          });

          videoRef.current.addEventListener('waiting', () => {
            setLoading(true);
          });

          videoRef.current.addEventListener('playing', () => {
            setLoading(false);
          });
        }
      } catch (err) {
        setError('Failed to initialize video player');
        setLoading(false);
      }
    };

    setupPlayer();

    return () => {
      cancelled = true;
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
    };
  }, [fileId]);

  const getQualityColor = (score?: number): string => {
    if (!score) return 'gray';
    if (score >= 150) return 'green';
    if (score >= 100) return 'blue';
    if (score >= 50) return 'yellow';
    return 'red';
  };

  return (
    <Stack gap="sm">
      {showMetadata && (
        <Group gap="xs">
          <Text size="sm" fw={600}>{filename}</Text>
          {quality !== undefined && (
            <Badge color={getQualityColor(quality)} variant="light">
              Q: {quality}
            </Badge>
          )}
          {resolution && (
            <Badge color="blue" variant="outline">{resolution}</Badge>
          )}
          {codec && (
            <Badge color="gray" variant="outline">{codec}</Badge>
          )}
        </Group>
      )}

      {error && (
        <Alert
          icon={<IconAlertCircle size={16} />}
          title="Playback Error"
          color="red"
          variant="light"
        >
          {error}
          <Text size="xs" c="dimmed" mt="xs">
            The file may not exist on disk or the NAS may not be mounted.
          </Text>
        </Alert>
      )}

      <Box pos="relative">
        {loading && !error && (
          <Center
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 10,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              borderRadius: '8px'
            }}
          >
            <Loader size="lg" color="blue" />
          </Center>
        )}

        <video
          ref={videoRef}
          playsInline
          controls
          style={{ width: '100%', display: error ? 'none' : 'block' }}
        >
          <source
            src={useSmartStream ? `/api/stream/${fileId}/smart` : `/api/stream/${fileId}`}
            type="video/mp4"
          />
          Your browser does not support the video tag.
        </video>
      </Box>
    </Stack>
  );
}
