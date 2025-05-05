// Global variables
let projectId = null;
let imageId = null;
let imageData = null;
let projectImages = [];
let currentImageIndex = -1;
let zoomLevel = 1;
let imageNaturalWidth = 0;
let imageNaturalHeight = 0;

// Drawing state
let isDrawingBox = false;
let drawingStartX = 0;
let drawingStartY = 0;
let currentDrawingClassId = null;
let currentDrawingColor = 'red';
let activeBoxes = []; // Holds data for boxes fetched from backend
let highlightedBoxId = null;

// DOM Elements
let imageDisplay = null;
let mainImage = null;
let svgOverlay = null;
let tempRect = null; // Temporary rectangle for drawing

// --- State Variables ---
let currentImageId = null; // Keep track of the currently displayed image ID
let currentProjectId = null; // Keep track of the current project ID
let isPanning = false;
let startX, startY, initialTranslateX, initialTranslateY;
let currentTransform = { x: 0, y: 0, k: 1 }; // Pan (x, y) and zoom (k) state
let isLoading = true; // Track initial loading state

// --- Navigation Functions ---
// Define these before initUI uses them
function navigateToPreviousImage() {
  if (currentImageIndex > 0) {
    const prevImage = projectImages[currentImageIndex - 1];
    window.location.href = `/ui/view?id=${prevImage.id}&project=${projectId}`;
  }
}

function navigateToNextImage() {
  if (currentImageIndex < projectImages.length - 1) {
    const nextImage = projectImages[currentImageIndex + 1];
    window.location.href = `/ui/view?id=${nextImage.id}&project=${projectId}`;
  }
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  console.log("View.js: DOMContentLoaded event fired. Setting up UI and listeners...");
  // Get image ID and project ID from URL
  const urlParams = new URLSearchParams(window.location.search);
  imageId = urlParams.get('id');
  projectId = urlParams.get('project');
  
  if (!imageId || !projectId) {
    showError('Image ID or Project ID is missing. Redirecting to projects page...');
    setTimeout(() => {
      window.location.href = '/ui';
    }, 3000);
    return;
  }
  
  // Initialize the UI
  initUI();
  
  // Load image data
  loadImageData();
  
  // Load all project images for navigation
  loadProjectImages();

  // Add listeners for events from boundingBoxManager
  document.addEventListener('startDrawingMode', handleStartDrawingMode);
  document.addEventListener('cancelDrawingMode', handleCancelDrawingMode);
  document.addEventListener('drawingComplete', cleanupDrawingState);
  document.addEventListener('boxesUpdated', handleBoxesUpdated);
  document.addEventListener('highlightBox', handleHighlightBox);

  // Global variables for other scripts (use with caution or refactor to events/modules)
  window.imageId = imageId;
  window.projectId = projectId;
});

function initUI() {
  imageDisplay = document.getElementById('image-display');
  // Add position relative if not already set by CSS
  if (imageDisplay) {
      imageDisplay.style.position = 'relative';
  }

  // Setup event listeners
  const backButton = document.getElementById('back-button');
  const prevButton = document.getElementById('prev-button');
  const nextButton = document.getElementById('next-button');
  const zoomInButton = document.getElementById('zoom-in-button');
  const zoomOutButton = document.getElementById('zoom-out-button');
  const resetZoomButton = document.getElementById('reset-zoom-button');
  const downloadButton = document.getElementById('download-button');
  
  // Back button
  if (backButton) {
    backButton.addEventListener('click', () => {
      window.location.href = `/ui/project?id=${projectId}`;
    });
  }
  
  // Previous button
  if (prevButton) {
    prevButton.addEventListener('click', navigateToPreviousImage);
    // Initially disable until we know there's a previous image
    prevButton.disabled = true;
  }
  
  // Next button
  if (nextButton) {
    nextButton.addEventListener('click', navigateToNextImage);
    // Initially disable until we know there's a next image
    nextButton.disabled = true;
  }
  
  // Zoom controls
  if (zoomInButton) {
    zoomInButton.addEventListener('click', () => {
      zoom(1.2);
    });
  }
  
  if (zoomOutButton) {
    zoomOutButton.addEventListener('click', () => {
      zoom(1 / 1.2);
    });
  }
  
  if (resetZoomButton) {
    resetZoomButton.addEventListener('click', () => {
      resetView();
    });
  }
  
  // Download button
  if (downloadButton) {
    downloadButton.addEventListener('click', downloadCurrentImage);
  }
  
  // Keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
      navigateToPreviousImage();
    } else if (e.key === 'ArrowRight') {
      navigateToNextImage();
    } else if (e.key === '+' || e.key === '=') {
      zoom(1.2);
    } else if (e.key === '-') {
      zoom(1 / 1.2);
    } else if (e.key === '0') {
      resetView();
    }
  });

  // Setup Panzoom listeners on the image display area
  imageDisplay.addEventListener('mousedown', handlePanZoomMouseDown);
  imageDisplay.addEventListener('mousemove', handlePanZoomMouseMove);
  window.addEventListener('mouseup', handlePanZoomMouseUp); // Use window for mouseup
  // imageDisplay.addEventListener('wheel', handleWheelZoom, { passive: false }); // REMOVE Wheel Zoom

  // Ensure initial state is correct
  updateLoadingState(true);
}

// --- Loading State ---
function updateLoadingState(loading) {
  isLoading = loading;
  const loadingContainerElement = document.querySelector('#image-display .loading-container'); // Adjust selector if needed
  if (loadingContainerElement) {
      loadingContainerElement.style.display = loading ? 'flex' : 'none';
  }
}

async function loadImageData() {
  try {
    showLoader('image-display');
    
    // Fetch image metadata
    const response = await fetch(`/images/${imageId}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    imageData = await response.json();
    
    // Update image title
    updateImageTitle(imageData);
    
    // Get download URL
    const urlResponse = await fetch(`/images/${imageId}/download/`);
    
    if (!urlResponse.ok) {
      throw new Error(`HTTP error! Status: ${urlResponse.status}`);
    }
    
    const urlData = await urlResponse.json();
    
    if (!urlData || !urlData.url) {
      throw new Error('Invalid URL data received from server');
    }
    
    // Display the image and setup overlay
    await displayImageAndOverlay(urlData.url); // Wait for image to load
    
    // Display metadata
    // Consider if displayMetadata should be called after image load completes
    // dispatchEvent for metadata component?
    // For now, call it here. If it relies on image dimensions, move it to displayImageAndOverlay.
    // displayMetadata(imageData); // Let's assume metadata tab handles its own loading via Alpine
    
  } catch (error) {
    console.error('Error loading image data:', error);
    showError('Failed to load image. Please try again later.');
    if (imageDisplay) imageDisplay.innerHTML = '<div class="error-card">Failed to load image</div>'; // Clear loader, show error
  } finally {
     // Loader hiding should happen *after* image is loaded in displayImageAndOverlay
     // hideLoader('image-display'); // Moved
  }
}

function updateImageTitle(image) {
  const imageTitle = document.getElementById('image-title');
  
  if (imageTitle) {
    imageTitle.textContent = image.filename || 'Unnamed image';
  }
  
  // Update page title
  document.title = `${image.filename || 'Image'} - Image Manager`;
}

function displayImageAndOverlay(url) {
  return new Promise((resolve, reject) => {
    if (!imageDisplay) return reject(new Error("Image display container not found"));

    // Clear existing content
    imageDisplay.innerHTML = '';

    // Create image element
    mainImage = document.createElement('img');
    mainImage.src = url;
    mainImage.alt = imageData.filename || 'Image';
    mainImage.id = 'main-image';
    mainImage.className = 'view-image';
    // Prevent default browser image drag behavior AND text selection
    mainImage.addEventListener('dragstart', (e) => e.preventDefault());
    mainImage.style.userSelect = 'none';
    mainImage.style.webkitUserSelect = 'none'; // For Safari
    mainImage.style.msUserSelect = 'none'; // For IE/Edge

    mainImage.onload = () => {
        console.log("Main image loaded.");
        imageNaturalWidth = mainImage.naturalWidth;
        imageNaturalHeight = mainImage.naturalHeight;
        console.log(`Natural dimensions: ${imageNaturalWidth}x${imageNaturalHeight}`);

        // Create SVG overlay *after* image is loaded to get dimensions
        createSvgOverlay();

        // Apply initial zoom/transform if needed (e.g., if zoomLevel is not 1)
        applyTransform();

        hideLoader('image-display'); // Hide loader now
        resolve(); // Resolve the promise
    };

    mainImage.onerror = () => {
        console.error('Error loading image from URL:', url);
        imageDisplay.innerHTML = '<div class="error-card">Failed to load image</div>';
        hideLoader('image-display');
        reject(new Error('Failed to load image from URL'));
    };

    // Append image to display
    imageDisplay.appendChild(mainImage);
  });
}

function createSvgOverlay() {
    if (!imageDisplay || !mainImage) return;

    // Remove existing overlay if any
    const existingOverlay = imageDisplay.querySelector('.svg-overlay');
    if (existingOverlay) {
        imageDisplay.removeChild(existingOverlay);
    }

    svgOverlay = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svgOverlay.setAttribute('class', 'svg-overlay');
    svgOverlay.style.position = 'absolute';
    svgOverlay.style.top = '0';
    svgOverlay.style.left = '0';
    svgOverlay.style.width = '100%'; // Cover the container
    svgOverlay.style.height = '100%';
    svgOverlay.style.pointerEvents = 'none'; // Default: don't interfere with image events
    svgOverlay.style.zIndex = '10'; // Ensure it's above the image

    // ViewBox should match the image's natural dimensions for coordinate mapping
    svgOverlay.setAttribute('viewBox', `0 0 ${imageNaturalWidth} ${imageNaturalHeight}`);
    svgOverlay.setAttribute('preserveAspectRatio', 'none'); // Let CSS handle scaling/positioning

    imageDisplay.appendChild(svgOverlay);
    console.log("SVG overlay created.");

     // Draw existing boxes now that overlay is ready
    drawExistingBoxes();
}

async function loadProjectImages() {
  try {
    console.log('Fetching images for project:', projectId);
    const response = await fetch(`/projects/${projectId}/images/`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    projectImages = await response.json();
    
    if (!Array.isArray(projectImages)) {
      console.error('Server response is not an array:', projectImages);
      throw new Error('Invalid server response: expected an array of images');
    }
    
    // Find the index of the current image
    currentImageIndex = projectImages.findIndex(img => img.id === imageId);
    
    // Update navigation buttons
    updateNavigationButtons();
    
  } catch (error) {
    console.error('Error loading project images:', error);
    showError('Failed to load project images for navigation. Please try again later.');
  }
}

function updateNavigationButtons() {
  const prevButton = document.getElementById('prev-button');
  const nextButton = document.getElementById('next-button');
  
  if (prevButton) {
    prevButton.disabled = currentImageIndex <= 0;
  }
  
  if (nextButton) {
    nextButton.disabled = currentImageIndex >= projectImages.length - 1 || currentImageIndex === -1;
  }
}

function applyZoom() {
  // zoomLevel is updated by button clicks/keys
  applyTransform();
}

function applyTransform() {
    if (!mainImage) return;

    // Apply scale to the main image element
    // We use transform-origin: 0 0 to scale from top-left, simplifying coordinate math slightly
    // This might affect visual centering; adjust container styles if needed.
    // Or keep default center origin and adjust coordinate math accordingly.
    // Let's stick with default center origin for now.
    mainImage.style.transformOrigin = 'center center'; // Or '0 0' if preferred
    mainImage.style.transform = `scale(${zoomLevel})`;

    // Note: SVG overlay itself doesn't need transform.
    // Its content uses intrinsic coordinates via viewBox.
    // CSS scaling of the parent container (#image-display) or the <img> tag
    // effectively scales the SVG visually along with the image.
    // The 'vector-effect: non-scaling-stroke' keeps strokes constant.

    // We might need to explicitly redraw boxes if label positioning/sizing
    // needs fine-tuning based on zoom, but viewBox handles basic scaling.
    // For now, assume viewBox + non-scaling-stroke is sufficient.
    // If labels become unreadable/overlap badly, redraw might be needed.
    // drawExistingBoxes(); // Optional: Redraw if needed for zoom adjustments

    console.log("Applied transform: zoomLevel =", zoomLevel);
}

async function downloadImage() {
  if (!imageData) return;
  
  try {
    // Get the direct content URL
    const contentUrl = `/images/${imageId}/content`;
    
    // Create a temporary link element
    const link = document.createElement('a');
    link.href = contentUrl;
    link.download = imageData.filename || 'image';
    
    // Append to the document, click it, and remove it
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
  } catch (error) {
    console.error('Error downloading image:', error);
    showError('Failed to download image. Please try again later.');
  }
}

function formatFileSize(bytes) {
  if (!bytes) return 'Unknown size';
  
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function formatDate(dateString) {
  if (!dateString) return 'Unknown';
  
  const date = new Date(dateString);
  return date.toLocaleString();
}

function showLoader(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  const loader = document.createElement('div');
  loader.className = 'loader';
  loader.innerHTML = '<div class="loading"></div>';
  
  container.appendChild(loader);
}

function hideLoader(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  const loader = container.querySelector('.loader');
  if (loader) {
    container.removeChild(loader);
  }
}

function showError(message) {
  const alertsContainer = document.getElementById('alerts-container');
  if (!alertsContainer) return;
  
  const alert = document.createElement('div');
  alert.className = 'alert alert-error';
  alert.textContent = message;
  
  alertsContainer.appendChild(alert);
  
  // Remove after 5 seconds
  setTimeout(() => {
    alertsContainer.removeChild(alert);
  }, 5000);
}

function showSuccess(message) {
  const alertsContainer = document.getElementById('alerts-container');
  if (!alertsContainer) return;
  
  const alert = document.createElement('div');
  alert.className = 'alert alert-success';
  alert.textContent = message;
  
  alertsContainer.appendChild(alert);
  
  // Remove after 5 seconds
  setTimeout(() => {
    alertsContainer.removeChild(alert);
  }, 5000);
}

// --- Coordinate Conversion ---

function screenToImageCoords(screenX, screenY) {
    if (!mainImage || !imageNaturalWidth || !imageNaturalHeight) {
        console.warn("Cannot convert coordinates: Image or dimensions not available.");
        return null;
    }

    const imgRect = mainImage.getBoundingClientRect();

    // Calculate position relative to the image's top-left corner in screen pixels
    const xRelScreen = screenX - imgRect.left;
    const yRelScreen = screenY - imgRect.top;

    // Calculate the scale factor (ratio of displayed size to natural size)
    // Note: getBoundingClientRect width/height include transforms (scale)
    const scaleX = imgRect.width / imageNaturalWidth;
    const scaleY = imgRect.height / imageNaturalHeight; // Usually same as scaleX unless aspect ratio is distorted

    // Convert screen-relative position to intrinsic image coordinates
    const intrinsicX = xRelScreen / scaleX;
    const intrinsicY = yRelScreen / scaleY;

    // Clamp coordinates to be within image bounds [0, naturalWidth/Height]
    const clampedX = Math.max(0, Math.min(intrinsicX, imageNaturalWidth));
    const clampedY = Math.max(0, Math.min(intrinsicY, imageNaturalHeight));

    // console.log(`Screen (${screenX}, ${screenY}) -> ImgRect (${imgRect.left}, ${imgRect.top}) -> RelScreen (${xRelScreen}, ${yRelScreen}) -> Scale (${scaleX.toFixed(2)}) -> Intrinsic (${intrinsicX.toFixed(1)}, ${intrinsicY.toFixed(1)}) -> Clamped (${clampedX.toFixed(1)}, ${clampedY.toFixed(1)})`);

    return { x: clampedX, y: clampedY };
}

function normalizeCoords(coords) {
    // Convert intrinsic pixel coordinates to normalized (0-1) relative coordinates
    if (!imageNaturalWidth || !imageNaturalHeight) return null;
    return {
        x_min: Math.min(coords.startX, coords.endX) / imageNaturalWidth,
        y_min: Math.min(coords.startY, coords.endY) / imageNaturalHeight,
        x_max: Math.max(coords.startX, coords.endX) / imageNaturalWidth,
        y_max: Math.max(coords.startY, coords.endY) / imageNaturalHeight
    };
}


// --- Drawing Event Handlers ---

// REMOVE OLD MOUSE/TOUCH HANDLERS (handleMouseDown, handleMouseMove, handleMouseUp, handleMouseLeave, handleTouchStart, handleTouchMove, handleTouchEnd)
// These are superseded by the handleDrawingMouseDown etc. triggered via handleStartDrawingMode.

/*
function handleMouseDown(e) {
    // ... removed ...
}

function handleMouseMove(e) {
    // ... removed ...
}

function handleMouseUp(e) {
    // ... removed ...
}

function handleMouseLeave(e) {
    // ... removed ...
}

function cleanupDrawing(removeListeners = true) {
    // ... removed ... // Superseded by cleanupDrawingState
}

function handleTouchStart(e) {
    // ... removed ...
}

function handleTouchMove(e) {
    // ... removed ...
}

function handleTouchEnd(e) {
    // ... removed ...
}
*/

// --- Helper for Temporary Drawing Rect ---
function createTempRect(x, y) {
    console.log(`createTempRect: Creating at SVG (${x.toFixed(1)}, ${y.toFixed(1)}) with color ${currentDrawingColor}`);
    if (!svgOverlay) {
        console.error("createTempRect: svgOverlay is not available!");
        return;
    }
    tempRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    tempRect.setAttribute('x', x);
    tempRect.setAttribute('y', y);
    tempRect.setAttribute('width', '0');
    tempRect.setAttribute('height', '0');
    tempRect.setAttribute('fill', 'none');
    tempRect.setAttribute('stroke', currentDrawingColor);
    tempRect.setAttribute('stroke-width', '2'); // Use intrinsic stroke width
     // Adjust stroke-width based on zoom? Maybe later. For now, fixed intrinsic width.
    tempRect.setAttribute('vector-effect', 'non-scaling-stroke'); // Keeps stroke width constant regardless of zoom
    tempRect.setAttribute('class', 'temp-drawing-box');
    svgOverlay.appendChild(tempRect);
}

// --- Bounding Box Visualization ---

function drawExistingBoxes() {
    if (!svgOverlay) {
        console.warn("SVG Overlay not ready for drawing boxes.");
        return;
    }
    console.log("Drawing existing boxes:", activeBoxes);

    // Clear existing boxes (except tempRect if it exists)
    const existingRects = svgOverlay.querySelectorAll('.bounding-box-rect, .bounding-box-label');
    existingRects.forEach(el => svgOverlay.removeChild(el));

    activeBoxes.forEach(box => {
        if (box.x_min === undefined || box.y_min === undefined || box.x_max === undefined || box.y_max === undefined) {
             console.warn("Skipping box with undefined coordinates:", box);
             return;
        }
        const x = box.x_min * imageNaturalWidth;
        const y = box.y_min * imageNaturalHeight;
        const width = (box.x_max - box.x_min) * imageNaturalWidth;
        const height = (box.y_max - box.y_min) * imageNaturalHeight;
        const color = box.color || 'lime'; // Use color from boundingBoxManager or default
        const className = box.className || 'Unknown';
        const boxId = box.id;

        // Create box rectangle
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', x);
        rect.setAttribute('y', y);
        rect.setAttribute('width', width);
        rect.setAttribute('height', height);
        rect.setAttribute('fill', 'none');
        rect.setAttribute('stroke', color);
        rect.setAttribute('stroke-width', '2'); // Intrinsic stroke width
        rect.setAttribute('vector-effect', 'non-scaling-stroke'); // Keep stroke width constant
        rect.setAttribute('class', 'bounding-box-rect');
        rect.setAttribute('data-box-id', boxId); // Store ID for potential interaction

        // Add highlighting style if this box is selected
        if (boxId === highlightedBoxId) {
             rect.setAttribute('stroke-width', '4'); // Thicker stroke for highlight
             rect.style.filter = 'drop-shadow(0 0 3px yellow)'; // Glow effect
        }

        // Make existing boxes clickable
        rect.style.pointerEvents = 'auto'; // Allow clicks on the rectangles
        rect.addEventListener('click', (e) => {
            if (isDrawingBox) return; // Don't allow selection while drawing
            e.stopPropagation(); // Prevent triggering image-display click/pan
            console.log("Clicked box:", boxId);
            // Dispatch event to notify boundingBoxManager to select this box (e.g., for editing/deletion)
            document.dispatchEvent(new CustomEvent('boxSelected', { detail: { boxId: boxId }}));
        });


        svgOverlay.appendChild(rect);

        // Create label (optional)
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        const labelPadding = 2;
        const fontSize = 12; // Intrinsic font size
        label.setAttribute('x', x + labelPadding); // Position label slightly inside the box
        label.setAttribute('y', y + fontSize + labelPadding); // Adjust vertical position
        label.setAttribute('font-size', fontSize); // Intrinsic font size
        label.setAttribute('fill', 'white');
        label.setAttribute('class', 'bounding-box-label');
        label.style.pointerEvents = 'none'; // Labels shouldn't be interactive
         // Add a background rect for better visibility
        const labelBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        labelBg.setAttribute('x', x);
        labelBg.setAttribute('y', y); // Position background at top of text
        labelBg.setAttribute('width', className.length * 6 + 8); // Estimate width based on text length
        labelBg.setAttribute('height', 16); // Fixed height
        labelBg.setAttribute('fill', color);
        labelBg.setAttribute('class', 'bounding-box-label-bg');
        labelBg.style.pointerEvents = 'none';

        label.textContent = className;

        svgOverlay.appendChild(labelBg); // Add background first
        svgOverlay.appendChild(label);

    });
}


// --- Event Handlers for Communication --- 
function handleStartDrawingMode(event) {
    if (!mainImage || !svgOverlay) {
        console.warn("handleStartDrawingMode: Image or SVG overlay not ready.");
        return;
    }
    // If already drawing, maybe cancel the previous and start new? For now, just ignore.
    if (isDrawingBox) {
        console.warn("handleStartDrawingMode: Already in drawing mode. Ignoring.");
        return;
    }

    const { classId, className, color } = event.detail;
    console.log(`handleStartDrawingMode: Entering drawing mode for class ${classId} (${className}) with color ${color}`);

    isDrawingBox = true;
    currentDrawingClassId = classId;
    currentDrawingColor = color || '#FF0000'; // Use provided color or default

    // Make SVG overlay interactive
    svgOverlay.style.pointerEvents = 'auto';
    svgOverlay.style.cursor = 'crosshair';

    // Attach drawing listeners directly to the SVG overlay and window
    svgOverlay.addEventListener('mousedown', handleDrawingMouseDown);
    window.addEventListener('mousemove', handleDrawingMouseMove);
    window.addEventListener('mouseup', handleDrawingMouseUp);
    // Add touch equivalents if necessary, adapting handleDrawing... functions
    // svgOverlay.addEventListener('touchstart', handleDrawingTouchStart, { passive: false });
    // window.addEventListener('touchmove', handleDrawingTouchMove, { passive: false });
    // window.addEventListener('touchend', handleDrawingTouchEnd);

    // Notify Alpine component that drawing mode has started
    // document.dispatchEvent(new CustomEvent('viewDrawingStarted')); // Not strictly needed if boundingBoxManager handles UI state
    console.log("handleStartDrawingMode: Dispatched viewDrawingStarted event.");
}

function handleCancelDrawingMode() {
    console.log("handleCancelDrawingMode: Exiting drawing mode.");
    // cleanupDrawingState will dispatch viewDrawingEnded
    cleanupDrawingState();
}

function cleanupDrawingState() {
    // Only clean up and dispatch event if we were actually in drawing mode
    const wasDrawing = isDrawingBox;

    // console.log(`cleanupDrawingState: Cleaning up... Was drawing: ${wasDrawing}`);

    isDrawingBox = false;
    drawingStartX = 0;
    drawingStartY = 0;
    currentDrawingClassId = null;
    currentDrawingColor = '#FF0000';

    if (svgOverlay) {
        // Make SVG overlay non-interactive again
        svgOverlay.style.pointerEvents = 'none';
        svgOverlay.style.cursor = 'default'; // Or inherit

        // Remove drawing listeners
        svgOverlay.removeEventListener('mousedown', handleDrawingMouseDown);
    }
    // Remove window listeners
    window.removeEventListener('mousemove', handleDrawingMouseMove);
    window.removeEventListener('mouseup', handleDrawingMouseUp);

    // Remove temporary rectangle if it exists
    if (tempRect) {
        if (svgOverlay && svgOverlay.contains(tempRect)) {
             tempRect.remove();
        }
        tempRect = null;
    }

    // Dispatch ended event *only if* we were previously drawing
    if (wasDrawing) {
        document.dispatchEvent(new CustomEvent('viewDrawingEnded'));
        console.log("cleanupDrawingState: Dispatched viewDrawingEnded event.");
    }
}

// MouseDown on SVG overlay when in drawing mode
function handleDrawingMouseDown(event) {
    // Only react to left button and if we are in drawing mode
    if (!isDrawingBox || event.button !== 0) return;

    event.stopPropagation(); // Prevent triggering pan/zoom
    console.log("handleDrawingMouseDown: Starting draw.");

    const startCoords = getMousePositionInSvg(event);
    drawingStartX = startCoords.x; // Store SVG coordinates
    drawingStartY = startCoords.y;

    // Create the temporary rectangle using SVG coordinates
    createTempRect(drawingStartX, drawingStartY);
}

// MouseMove on window when in drawing mode
function handleDrawingMouseMove(event) {
    // Only react if drawing is active (isDrawingBox=true and tempRect exists)
    if (!isDrawingBox || !tempRect) return;

    event.stopPropagation(); // Prevent other actions

    const currentCoords = getMousePositionInSvg(event);
    const currentX = currentCoords.x;
    const currentY = currentCoords.y;

    // Update temporary rectangle dimensions using SVG coordinates
    const width = Math.abs(currentX - drawingStartX);
    const height = Math.abs(currentY - drawingStartY);
    const rectX = Math.min(drawingStartX, currentX);
    const rectY = Math.min(drawingStartY, currentY);

    tempRect.setAttribute('x', rectX);
    tempRect.setAttribute('y', rectY);
    tempRect.setAttribute('width', width);
    tempRect.setAttribute('height', height);
}


// Mouseup on window when in drawing mode
function handleDrawingMouseUp(event) {
    // Only proceed if drawing was in progress (isDrawingBox true AND tempRect exists)
    // Only react to left button release
    if (!isDrawingBox || !tempRect || event.button !== 0) {
        // If mouseup occurs before mousedown after startDrawingMode, tempRect is null.
        // If mouseup is not left button, just clean up if needed.
        if (isDrawingBox) {
             console.log("handleDrawingMouseUp: Invalid state or button, cleaning up.");
             cleanupDrawingState(); // Will dispatch viewDrawingEnded if needed
        }
        return;
    }
    event.stopPropagation(); // Prevent other actions
    console.log("handleDrawingMouseUp: Finishing drawing.");

    const finalCoords = getMousePositionInSvg(event);
    const finalX = finalCoords.x;
    const finalY = finalCoords.y;

    // Ensure minimum size (optional, avoids zero-size boxes on simple clicks)
    const minSize = 2; // Minimum pixels width/height
    if (Math.abs(finalX - drawingStartX) < minSize || Math.abs(finalY - drawingStartY) < minSize) {
        console.log("handleDrawingMouseUp: Box too small, cancelling draw.");
        cleanupDrawingState(); // Will dispatch viewDrawingEnded
        return;
    }

    // Calculate final SVG box coordinates
    const boxSvgX = Math.min(drawingStartX, finalX);
    const boxSvgY = Math.min(drawingStartY, finalY);
    const boxSvgWidth = Math.abs(finalX - drawingStartX);
    const boxSvgHeight = Math.abs(finalY - drawingStartY);

    // Convert SVG corner points to normalized coordinates
    const topLeftNormalized = svgPointToNormalized(boxSvgX, boxSvgY);
    const bottomRightNormalized = svgPointToNormalized(boxSvgX + boxSvgWidth, boxSvgY + boxSvgHeight);

    if (!topLeftNormalized || !bottomRightNormalized) {
        console.error("handleDrawingMouseUp: Failed to convert coordinates to normalized.");
        showError("Failed to save box: Coordinate conversion error.");
        cleanupDrawingState(); // Will dispatch viewDrawingEnded
        return;
    }

    const normalizedCoords = {
        x_min: topLeftNormalized.x,
        y_min: topLeftNormalized.y,
        x_max: bottomRightNormalized.x,
        y_max: bottomRightNormalized.y
    };

    console.log("handleDrawingMouseUp: Calculated Normalized Coords:", normalizedCoords);

    // Dispatch the completion event for boundingBoxManager to handle saving
    document.dispatchEvent(new CustomEvent('drawingComplete', {
        detail: {
            normalizedCoords: normalizedCoords,
            classId: currentDrawingClassId
        }
    }));

    // Clean up the drawing state (removes temp rect, listeners, resets flags)
    // This will also dispatch the viewDrawingEnded event
    cleanupDrawingState();
}

function handleBoxesUpdated(event) {
    console.log(`Received boxesUpdated event: ${event.detail && event.detail.boxes ? event.detail.boxes.length : 'invalid'} boxes`);
    if (event.detail && Array.isArray(event.detail.boxes)) {
        activeBoxes = event.detail.boxes; // Update the global list
        requestAnimationFrame(() => { // Ensure drawing happens smoothly after state update
             drawExistingBoxes(); // Now call without argument, uses updated activeBoxes
        });
    }
}

function handleHighlightBox(event) {
    const { boxId } = event.detail; // boxId can be null to clear highlight
    console.log("HighlightBox event:", boxId);
    highlightedBoxId = boxId; // Store the ID to highlight (or null)
    // Request redraw - drawExistingBoxes will use highlightedBoxId
    requestAnimationFrame(() => {
         drawExistingBoxes();
     });

    /* // Old direct manipulation - less robust than redrawing
    // Remove existing highlight class/style before applying new one
    svgOverlay.querySelectorAll('.bounding-box-rect.highlighted').forEach(el => {
         el.classList.remove('highlighted');
         el.setAttribute('stroke-width', '2'); // Reset stroke width
         el.style.filter = 'none';
     });

    if (boxId) {
        const rectToHighlight = svgOverlay.querySelector(`.bounding-box-rect[data-box-id="${boxId}"]`);
        if (rectToHighlight) {
            rectToHighlight.classList.add('highlighted');
            // Apply visual highlight (e.g., thicker stroke, different style)
            rectToHighlight.setAttribute('stroke-width', '4');
             rectToHighlight.style.filter = 'drop-shadow(0 0 3px yellow)';
            // Optional: scroll into view if needed
        } else {
            console.warn("Box to highlight not found in SVG:", boxId);
        }
    }
    */
}

// --- Pan and Zoom Logic ---
function handlePanZoomMouseDown(e) {
    // Prevent panning if currently drawing a box
    if (isDrawingBox) {
        console.log("handlePanZoomMouseDown: Suppressed during drawing.");
        return;
    }
    // Prevent interfering with clicks on controls/buttons inside imageDisplay if any
    if (e.button !== 0) return; // Only main button (left-click)

    console.log("handlePanZoomMouseDown: Pan started.");
    isPanning = true;
    startX = e.clientX;
    startY = e.clientY;
    // Store the initial transform state when panning starts
    initialTranslateX = currentTransform.x;
    initialTranslateY = currentTransform.y;
    imageDisplay.style.cursor = 'grabbing';
}

function handlePanZoomMouseMove(e) {
    if (!isPanning || isDrawingBox) return;
    e.preventDefault(); // Prevent text selection, etc.

    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    // Update current transform based on drag delta
    // Note: Panning amount needs to be scaled by the inverse of the zoom level
    currentTransform.x = initialTranslateX + dx / currentTransform.k;
    currentTransform.y = initialTranslateY + dy / currentTransform.k;

    applyTransform(); // Apply the new transform
}

function handlePanZoomMouseUp(e) {
    // Do not stop panning if isDrawingBox became true during the pan (shouldn't happen with guards)
    if (!isPanning || isDrawingBox) return;
    if (e.button !== 0) return; // Only main button

    console.log("handlePanZoomMouseUp: Pan ended."); // Changed log message
    isPanning = false;
    imageDisplay.style.cursor = 'grab'; // Or 'default' or keep crosshair if drawing is next? Use 'grab' for consistency.
}

function zoom(factor, clientX = null, clientY = null) {
    if (isDrawingBox) return; // Don't zoom while drawing
    const newZoom = Math.max(0.1, Math.min(10, currentTransform.k * factor)); // Clamp zoom level

    if (clientX !== null && clientY !== null && mainImage) {
        // Zoom towards mouse pointer
        const rect = imageDisplay.getBoundingClientRect();
        // Calculate mouse position relative to the image display container
        const mouseX = clientX - rect.left;
        const mouseY = clientY - rect.top;

        // Calculate the shift needed to keep the point under the cursor stationary
        // This involves the difference in scale and the position of the cursor
        const deltaX = (mouseX / currentTransform.k - mouseX / newZoom) * newZoom;
        const deltaY = (mouseY / currentTransform.k - mouseY / newZoom) * newZoom;

        currentTransform.x += deltaX / newZoom;
        currentTransform.y += deltaY / newZoom;
    }
    // If clientX/Y are null, zoom towards center (handled by transform-origin)

    currentTransform.k = newZoom;
    applyTransform();
}

function resetView() {
    console.log("Resetting view.");
    currentTransform = { x: 0, y: 0, k: 1 };
    highlightedBoxId = null; // Clear highlight on reset
    applyTransform();
    // Trigger redraw of boxes in their original positions/state
    requestAnimationFrame(() => {
        drawExistingBoxes();
    });
    // dispatchBoxesUpdated(); // No longer needed
}

// --- Utility Functions ---
// Refine showError and showSuccess to use Tailwind/DaisyUI if applicable
function showError(message) {
    console.error("Error:", message);
    const alertsContainer = document.getElementById('alerts-container');
    if (alertsContainer) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-error shadow-lg'; // Example DaisyUI classes
        alertDiv.innerHTML = `
            <div>
              <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <span>Error! ${message}</span>
            </div>`;
        alertsContainer.appendChild(alertDiv);
        // Optional: Auto-remove alert after some time
        setTimeout(() => alertDiv.remove(), 5000);
    }
}

function showSuccess(message) {
    console.log("Success:", message);
    const alertsContainer = document.getElementById('alerts-container');
    if (alertsContainer) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success shadow-lg'; // Example DaisyUI classes
        alertDiv.innerHTML = `
            <div>
              <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <span>Success! ${message}</span>
            </div>`;
        alertsContainer.appendChild(alertDiv);
        setTimeout(() => alertDiv.remove(), 3000);
    }
}

async function downloadCurrentImage() {
    if (!imageId) {
        showError("No image loaded to download.");
        return;
    }
    try {
        const response = await fetch(`/images/${imageId}/content`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        // Try to get filename from title or fallback
        const titleElement = document.getElementById('image-title');
        const filename = titleElement ? titleElement.textContent : `image_${imageId}.jpg`;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showSuccess("Image download started.");
    } catch (error) {
        console.error('Download failed:', error);
        showError(`Failed to download image: ${error.message}`);
    }
}

// --- Bounding Box Drawing Logic ---

// Function to convert SVG coordinates relative to the overlay top-left
// to normalized image coordinates (0-1)
function svgPointToNormalized(svgX, svgY) {
    if (!mainImage || !svgOverlay || mainImage.naturalWidth === 0 || mainImage.naturalHeight === 0) {
        console.error("Cannot convert coords: Image/SVG not ready or zero dimensions.");
        return null;
    }

    // Use the current image transform state (pan/zoom)
    const zoom = currentTransform.k;
    const panX = currentTransform.x; // Pan is in *original image pixels*
    const panY = currentTransform.y;

    // Get the bounding box of the SVG overlay itself
    const svgRect = svgOverlay.getBoundingClientRect();
    // Get the bounding box of the *displayed* (transformed) image
    const imageRect = mainImage.getBoundingClientRect();

    // Calculate the offset of the image's top-left corner relative to the SVG overlay's top-left corner
    // This offset includes the effect of CSS positioning AND the transform (pan)
    const imageOffsetX = imageRect.left - svgRect.left;
    const imageOffsetY = imageRect.top - svgRect.top;

    // 1. Calculate the mouse position relative to the *displayed* image's top-left corner (in screen pixels)
    const xRelativeToDisplayedImage = svgX - imageOffsetX;
    const yRelativeToDisplayedImage = svgY - imageOffsetY;

    // 2. Convert this position to coordinates on the *original, unscaled* image
    // by dividing by the current zoom level.
    const originalX = xRelativeToDisplayedImage / zoom;
    const originalY = yRelativeToDisplayedImage / zoom;

    // 3. Normalize these original coordinates based on the image's natural dimensions.
    const normalizedX = originalX / imageNaturalWidth;
    const normalizedY = originalY / imageNaturalHeight;

     // Clamp values between 0 and 1
     return {
         x: Math.max(0, Math.min(1, normalizedX)),
         y: Math.max(0, Math.min(1, normalizedY))
     };
}


// Function to convert normalized image coordinates (0-1) to SVG coordinates
// This is primarily used by drawExistingBoxes
function normalizedPointToSvg(normalizedX, normalizedY) {
     if (!mainImage || !svgOverlay || mainImage.naturalWidth === 0 || mainImage.naturalHeight === 0) {
        console.error("Cannot convert coords: Image/SVG not ready or zero dimensions.");
        return null;
    }

    // Use the current image transform state (pan/zoom)
    const zoom = currentTransform.k;
    const panX = currentTransform.x; // Pan is in *original image pixels*
    const panY = currentTransform.y;

    // Get the bounding box of the SVG overlay itself
    const svgRect = svgOverlay.getBoundingClientRect();
    // Get the bounding box of the *displayed* (transformed) image
    const imageRect = mainImage.getBoundingClientRect();

    // Calculate the offset of the image's top-left corner relative to the SVG overlay's top-left corner
    const imageOffsetX = imageRect.left - svgRect.left;
    const imageOffsetY = imageRect.top - svgRect.top;

    // 1. Calculate pixel coordinates on the *original* image
    const originalX = normalizedX * imageNaturalWidth;
    const originalY = normalizedY * imageNaturalHeight;

    // 2. Calculate where this point is on the *scaled* image (in screen pixels relative to image top-left)
    const scaledX = originalX * zoom;
    const scaledY = originalY * zoom;

    // 3. Calculate the final SVG coordinates by adding the image's offset within the SVG overlay
    const svgX = scaledX + imageOffsetX;
    const svgY = scaledY + imageOffsetY;

    return { x: svgX, y: svgY };
}

// Helper function to dispatch box updates is removed as it's not the right approach.
// Redraws should be triggered by state changes (e.g., in handleBoxesUpdated, handleHighlightBox, resetView)
