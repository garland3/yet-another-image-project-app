import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ImageView from '../ImageView';

// Mock react-router-dom
const mockParams = { imageId: 'test-image-id' };
const mockSearchParams = new URLSearchParams('project=test-project-id');
const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => mockParams,
  useSearchParams: () => [mockSearchParams],
  useNavigate: () => mockNavigate,
}));

// Mock child components
jest.mock('../components/ImageDisplay', () => {
  return function MockImageDisplay({ image, imageId }) {
    return <div data-testid="image-display">ImageDisplay - {image ? image.filename : 'Loading'}</div>;
  };
});

jest.mock('../components/ImageMetadata', () => {
  return function MockImageMetadata() {
    return <div data-testid="image-metadata">ImageMetadata</div>;
  };
});

jest.mock('../components/ImageClassifications', () => {
  return function MockImageClassifications() {
    return <div data-testid="image-classifications">ImageClassifications</div>;
  };
});

jest.mock('../components/CompactImageClassifications', () => {
  return function MockCompactImageClassifications() {
    return <div data-testid="compact-image-classifications">CompactImageClassifications</div>;
  };
});

jest.mock('../components/ImageComments', () => {
  return function MockImageComments() {
    return <div data-testid="image-comments">ImageComments</div>;
  };
});

jest.mock('../components/ImageDeletionControls', () => {
  return function MockImageDeletionControls() {
    return <div data-testid="image-deletion-controls">ImageDeletionControls</div>;
  };
});

// Mock data
const mockRegularImage = {
  id: 'test-image-id',
  filename: 'test-image.jpg',
  size_bytes: 1024000,
  created_at: '2023-01-01T00:00:00Z',
  deleted_at: null,
  storage_deleted: false
};

const mockDeletedImage = {
  id: 'test-image-id',
  filename: 'deleted-image.jpg',
  size_bytes: 512000,
  created_at: '2023-01-02T00:00:00Z',
  deleted_at: '2023-01-03T00:00:00Z',
  storage_deleted: false,
  deletion_reason: 'Test deletion'
};

const mockProjectImages = [mockRegularImage, mockDeletedImage];

// Mock fetch
global.fetch = jest.fn();

const renderImageView = () => {
  return render(
    <BrowserRouter>
      <ImageView />
    </BrowserRouter>
  );
};

describe('ImageView', () => {
  beforeEach(() => {
    fetch.mockClear();
    mockNavigate.mockClear();
    console.error = jest.fn(); // Mock console.error to avoid noise in tests
  });

  afterEach(() => {
    fetch.mockRestore();
  });

  describe('Regular Image Loading', () => {
    test('loads regular image successfully via direct endpoint', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockRegularImage)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockProjectImages)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([])
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401
        });

      renderImageView();

      await waitFor(() => {
        expect(screen.getByText('test-image.jpg')).toBeInTheDocument();
      });

      expect(fetch).toHaveBeenCalledWith('/api/images/test-image-id');
      expect(screen.getByTestId('image-display')).toHaveTextContent('test-image.jpg');
    });

    test('sets document title correctly for regular images', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockRegularImage)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockProjectImages)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([])
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401
        });

      renderImageView();

      await waitFor(() => {
        expect(document.title).toBe('test-image.jpg - Image Manager');
      });
    });
  });

  describe('Deleted Image Fallback Logic', () => {
    test('falls back to project endpoint when direct fetch fails', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: false,
          status: 404
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([mockDeletedImage])
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockProjectImages)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([])
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401
        });

      renderImageView();

      await waitFor(() => {
        expect(screen.getByText('deleted-image.jpg')).toBeInTheDocument();
      });

      // Verify direct fetch was attempted first
      expect(fetch).toHaveBeenNthCalledWith(1, '/api/images/test-image-id');
      
      // Verify fallback to project endpoint with include_deleted=true
      expect(fetch).toHaveBeenNthCalledWith(2, '/api/projects/test-project-id/images?include_deleted=true');
    });

    test('logs fallback attempt when direct fetch fails', async () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
      
      fetch
        .mockResolvedValueOnce({
          ok: false,
          status: 404
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([mockDeletedImage])
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockProjectImages)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([])
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401
        });

      renderImageView();

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Direct image fetch failed, trying project endpoint with deleted images...'
        );
      });

      consoleSpy.mockRestore();
    });

    test('sets document title correctly for deleted images loaded via fallback', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: false,
          status: 404
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([mockDeletedImage])
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockProjectImages)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([])
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401
        });

      renderImageView();

      await waitFor(() => {
        expect(document.title).toBe('deleted-image.jpg - Image Manager');
      });
    });

    test('handles case where image not found in project images', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: false,
          status: 404
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([]) // Empty array - image not found
        });

      renderImageView();

      await waitFor(() => {
        expect(screen.getByText('Failed to load image. Please try again later.')).toBeInTheDocument();
      });

      expect(console.error).toHaveBeenCalledWith(
        'Error loading image data:',
        expect.any(Error)
      );
    });

    test('handles project endpoint failure after direct fetch failure', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: false,
          status: 404
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 500
        });

      renderImageView();

      await waitFor(() => {
        expect(screen.getByText('Failed to load image. Please try again later.')).toBeInTheDocument();
      });
    });
  });

  describe('Project Images Loading', () => {
    test('loads project images with include_deleted=true', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockRegularImage)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockProjectImages)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([])
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401
        });

      renderImageView();

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith('/api/projects/test-project-id/images?include_deleted=true');
      });
    });

    test('handles project images loading failure', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockRegularImage)
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 500
        });

      renderImageView();

      await waitFor(() => {
        expect(screen.getByText('Failed to load project images for navigation. Please try again later.')).toBeInTheDocument();
      });
    });
  });

  describe('Navigation', () => {
    test('back button navigates to project page', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockRegularImage)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockProjectImages)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([])
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401
        });

      renderImageView();

      await waitFor(() => {
        expect(screen.getByText('< Back to Project')).toBeInTheDocument();
      });
    });
  });

  describe('Error States', () => {
    test('displays error when image ID or project ID is missing', () => {
      // Mock missing params
      jest.doMock('react-router-dom', () => ({
        ...jest.requireActual('react-router-dom'),
        useParams: () => ({ imageId: null }),
        useSearchParams: () => [new URLSearchParams()],
        useNavigate: () => mockNavigate,
      }));

      renderImageView();

      expect(screen.getByText('Image ID or Project ID is missing.')).toBeInTheDocument();
    });

    test('displays loading state initially', () => {
      fetch.mockImplementation(() => new Promise(() => {})); // Never resolves

      renderImageView();

      expect(screen.getByText('Loading image...')).toBeInTheDocument();
    });
  });

  describe('Component Integration', () => {
    test('renders all expected child components', async () => {
      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockRegularImage)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockProjectImages)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve([])
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 401
        });

      renderImageView();

      await waitFor(() => {
        expect(screen.getByTestId('image-display')).toBeInTheDocument();
        expect(screen.getByTestId('image-metadata')).toBeInTheDocument();
        expect(screen.getByTestId('image-classifications')).toBeInTheDocument();
        expect(screen.getByTestId('compact-image-classifications')).toBeInTheDocument();
        expect(screen.getByTestId('image-comments')).toBeInTheDocument();
        expect(screen.getByTestId('image-deletion-controls')).toBeInTheDocument();
      });
    });
  });
});