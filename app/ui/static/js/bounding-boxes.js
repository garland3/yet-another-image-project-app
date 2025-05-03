/**
 * Bounding Box Manager
 * Handles drawing, editing, and managing bounding boxes on images
 */
function boundingBoxManager() {
  return {
    boxes: [],
    classes: [],
    isDrawing: false,
    drawingComplete: false,
    editingBox: null,
    selectedClassId: '',
    newBoxComment: '',
    loading: true,
    canvas: null,
    ctx: null,
    image: null,
    imageElement: null,
    startX: 0,
    startY: 0,
    endX: 0,
    endY: 0,
    canvasRect: null,
    scale: 1,
    
    init() {
      this.loadClasses();
      this.loadBoxes();
      this.setupCanvas();
    },
    
    async loadClasses() {
      try {
        const projectId = new URLSearchParams(window.location.search).get('project');
        if (!projectId) return;
        
        const response = await fetch(`/projects/${projectId}/classes`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        this.classes = await response.json();
      } catch (error) {
        console.error('Error loading image classes:', error);
        showError('Failed to load image classes. Please try again later.');
      }
    },
    
    async loadBoxes() {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        const response = await fetch(`/images/${imageId}/boxes`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        this.boxes = await response.json();
      } catch (error) {
        console.error('Error loading bounding boxes:', error);
        showError('Failed to load bounding boxes. Please try again later.');
      }
    },
    
    setupCanvas() {
      // Create a container for the canvas
      const container = document.getElementById('bounding-box-canvas-container');
      if (!container) return;
      
      // Clear any existing content
      container.innerHTML = '';
      
      // Create canvas element
      this.canvas = document.createElement('canvas');
      this.canvas.className = 'bounding-box-canvas';
      container.appendChild(this.canvas);
      
      // Get the context
      this.ctx = this.canvas.getContext('2d');
      
      // Load the image
      this.loadImage();
      
      // Add event listeners for drawing
      this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
      this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
      this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
      this.canvas.addEventListener('click', this.handleClick.bind(this));
      
      // Add touch support
      this.canvas.addEventListener('touchstart', this.handleTouchStart.bind(this));
      this.canvas.addEventListener('touchmove', this.handleTouchMove.bind(this));
      this.canvas.addEventListener('touchend', this.handleTouchEnd.bind(this));
    },
    
    async loadImage() {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        // Get the image URL
        const response = await fetch(`/images/${imageId}/download/`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const urlData = await response.json();
        
        if (!urlData || !urlData.url) {
          throw new Error('Invalid URL data received from server');
        }
        
        // Create a new image element
        this.imageElement = new Image();
        this.imageElement.crossOrigin = 'anonymous';
        
        // Set up load event
        this.imageElement.onload = () => {
          // Set canvas dimensions to match the image
          this.canvas.width = this.imageElement.width;
          this.canvas.height = this.imageElement.height;
          
          // Draw the image on the canvas
          this.ctx.drawImage(this.imageElement, 0, 0);
          
          // Draw existing bounding boxes
          this.drawBoxes();
          
          // Update loading state
          this.loading = false;
        };
        
        // Set image source
        this.imageElement.src = urlData.url;
        
      } catch (error) {
        console.error('Error loading image for canvas:', error);
        showError('Failed to load image for bounding box editor. Please try again later.');
        this.loading = false;
      }
    },
    
    drawBoxes() {
      if (!this.ctx || !this.canvas) return;
      
      // Clear the canvas and redraw the image
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.ctx.drawImage(this.imageElement, 0, 0);
      
      // Draw each box
      this.boxes.forEach(box => {
        // Get the class for this box
        const boxClass = this.classes.find(cls => cls.id === box.image_class_id);
        
        // Set the color based on the class
        const color = this.getColorForClass(box.image_class_id);
        
        // Calculate coordinates
        const x = box.x_min * this.canvas.width;
        const y = box.y_min * this.canvas.height;
        const width = (box.x_max - box.x_min) * this.canvas.width;
        const height = (box.y_max - box.y_min) * this.canvas.height;
        
        // Draw the box
        this.ctx.strokeStyle = color;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, y, width, height);
        
        // Draw the label
        if (boxClass) {
          this.ctx.fillStyle = color;
          this.ctx.font = '12px Arial';
          this.ctx.fillRect(x, y - 20, boxClass.name.length * 7 + 10, 20);
          this.ctx.fillStyle = 'white';
          this.ctx.fillText(boxClass.name, x + 5, y - 5);
        }
      });
      
      // If we're currently drawing, draw the current box
      if (this.isDrawing) {
        this.ctx.strokeStyle = 'red';
        this.ctx.lineWidth = 2;
        
        const width = this.endX - this.startX;
        const height = this.endY - this.startY;
        
        this.ctx.strokeRect(this.startX, this.startY, width, height);
      }
    },
    
    getColorForClass(classId) {
      // Generate a color based on the class ID
      // This ensures the same class always gets the same color
      if (!classId) return 'red';
      
      // Simple hash function to convert class ID to a number
      let hash = 0;
      for (let i = 0; i < classId.length; i++) {
        hash = classId.charCodeAt(i) + ((hash << 5) - hash);
      }
      
      // Convert to RGB
      const r = (hash & 0xFF0000) >> 16;
      const g = (hash & 0x00FF00) >> 8;
      const b = hash & 0x0000FF;
      
      return `rgb(${r}, ${g}, ${b})`;
    },
    
    startDrawing() {
      this.isDrawing = true;
      this.drawingComplete = false;
    },
    
    cancelDrawing() {
      this.isDrawing = false;
      this.drawingComplete = false;
      this.startX = 0;
      this.startY = 0;
      this.endX = 0;
      this.endY = 0;
      this.selectedClassId = '';
      this.newBoxComment = '';
      
      // Redraw the canvas
      this.drawBoxes();
    },
    
    handleMouseDown(e) {
      if (!this.isDrawing) return;
      
      // Get canvas position
      this.canvasRect = this.canvas.getBoundingClientRect();
      
      // Set start position
      this.startX = e.clientX - this.canvasRect.left;
      this.startY = e.clientY - this.canvasRect.top;
      
      // Reset end position
      this.endX = this.startX;
      this.endY = this.startY;
    },
    
    handleMouseMove(e) {
      if (!this.isDrawing || !this.canvasRect) return;
      
      // Update end position
      this.endX = e.clientX - this.canvasRect.left;
      this.endY = e.clientY - this.canvasRect.top;
      
      // Redraw
      this.drawBoxes();
    },
    
    handleMouseUp(e) {
      if (!this.isDrawing || !this.canvasRect) return;
      
      // Update end position
      this.endX = e.clientX - this.canvasRect.left;
      this.endY = e.clientY - this.canvasRect.top;
      
      // Check if the box is too small
      const width = Math.abs(this.endX - this.startX);
      const height = Math.abs(this.endY - this.startY);
      
      if (width < 10 || height < 10) {
        // Box is too small, cancel drawing
        this.cancelDrawing();
        return;
      }
      
      // Normalize coordinates (make sure start is top-left, end is bottom-right)
      const normalizedCoords = this.normalizeCoordinates(this.startX, this.startY, this.endX, this.endY);
      this.startX = normalizedCoords.startX;
      this.startY = normalizedCoords.startY;
      this.endX = normalizedCoords.endX;
      this.endY = normalizedCoords.endY;
      
      // Drawing is complete, show the form to add class and comment
      this.drawingComplete = true;
      this.isDrawing = false;
    },
    
    handleClick(e) {
      if (this.isDrawing || this.drawingComplete) return;
      
      // Check if we clicked on a box
      const canvasRect = this.canvas.getBoundingClientRect();
      const x = e.clientX - canvasRect.left;
      const y = e.clientY - canvasRect.top;
      
      // Check each box
      for (let i = 0; i < this.boxes.length; i++) {
        const box = this.boxes[i];
        
        // Calculate coordinates
        const boxX = box.x_min * this.canvas.width;
        const boxY = box.y_min * this.canvas.height;
        const boxWidth = (box.x_max - box.x_min) * this.canvas.width;
        const boxHeight = (box.y_max - box.y_min) * this.canvas.height;
        
        // Check if the click is inside the box
        if (x >= boxX && x <= boxX + boxWidth && y >= boxY && y <= boxY + boxHeight) {
          // We clicked on this box, edit it
          this.editBox(box);
          return;
        }
      }
    },
    
    handleTouchStart(e) {
      if (!this.isDrawing) return;
      
      // Prevent default to avoid scrolling
      e.preventDefault();
      
      // Get canvas position
      this.canvasRect = this.canvas.getBoundingClientRect();
      
      // Set start position from the first touch
      const touch = e.touches[0];
      this.startX = touch.clientX - this.canvasRect.left;
      this.startY = touch.clientY - this.canvasRect.top;
      
      // Reset end position
      this.endX = this.startX;
      this.endY = this.startY;
    },
    
    handleTouchMove(e) {
      if (!this.isDrawing || !this.canvasRect) return;
      
      // Prevent default to avoid scrolling
      e.preventDefault();
      
      // Update end position from the first touch
      const touch = e.touches[0];
      this.endX = touch.clientX - this.canvasRect.left;
      this.endY = touch.clientY - this.canvasRect.top;
      
      // Redraw
      this.drawBoxes();
    },
    
    handleTouchEnd(e) {
      if (!this.isDrawing || !this.canvasRect) return;
      
      // Check if the box is too small
      const width = Math.abs(this.endX - this.startX);
      const height = Math.abs(this.endY - this.startY);
      
      if (width < 10 || height < 10) {
        // Box is too small, cancel drawing
        this.cancelDrawing();
        return;
      }
      
      // Normalize coordinates (make sure start is top-left, end is bottom-right)
      const normalizedCoords = this.normalizeCoordinates(this.startX, this.startY, this.endX, this.endY);
      this.startX = normalizedCoords.startX;
      this.startY = normalizedCoords.startY;
      this.endX = normalizedCoords.endX;
      this.endY = normalizedCoords.endY;
      
      // Drawing is complete, show the form to add class and comment
      this.drawingComplete = true;
      this.isDrawing = false;
    },
    
    normalizeCoordinates(startX, startY, endX, endY) {
      // Make sure start is top-left, end is bottom-right
      return {
        startX: Math.min(startX, endX),
        startY: Math.min(startY, endY),
        endX: Math.max(startX, endX),
        endY: Math.max(startY, endY)
      };
    },
    
    async saveBox() {
      try {
        if (!this.selectedClassId) {
          showError('Please select a class for the bounding box.');
          return;
        }
        
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        // Convert coordinates to relative values (0-1)
        const x_min = this.startX / this.canvas.width;
        const y_min = this.startY / this.canvas.height;
        const x_max = this.endX / this.canvas.width;
        const y_max = this.endY / this.canvas.height;
        
        const response = await fetch(`/images/${imageId}/boxes?image_class_id=${this.selectedClassId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            x_min,
            y_min,
            x_max,
            y_max,
            comment: this.newBoxComment
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }
        
        const newBox = await response.json();
        
        // Add the new box to the list
        this.boxes.push(newBox);
        
        // Reset drawing state
        this.cancelDrawing();
        
        // Redraw the canvas
        this.drawBoxes();
        
        showSuccess('Bounding box added successfully!');
      } catch (error) {
        console.error('Error saving bounding box:', error);
        showError(`Failed to save bounding box: ${error.message}`);
      }
    },
    
    editBox(box) {
      this.editingBox = { ...box };
    },
    
    cancelEdit() {
      this.editingBox = null;
    },
    
    async updateBox() {
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId || !this.editingBox) return;
        
        const response = await fetch(`/images/${imageId}/boxes/${this.editingBox.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            image_class_id: this.editingBox.image_class_id,
            comment: this.editingBox.comment
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }
        
        const updatedBox = await response.json();
        
        // Update the box in the list
        const index = this.boxes.findIndex(box => box.id === updatedBox.id);
        if (index !== -1) {
          this.boxes[index] = updatedBox;
        }
        
        this.editingBox = null;
        
        // Redraw the canvas
        this.drawBoxes();
        
        showSuccess('Bounding box updated successfully!');
      } catch (error) {
        console.error('Error updating bounding box:', error);
        showError(`Failed to update bounding box: ${error.message}`);
      }
    },
    
    async deleteBox(id) {
      if (!confirm('Are you sure you want to delete this bounding box?')) return;
      
      try {
        const imageId = new URLSearchParams(window.location.search).get('id');
        if (!imageId) return;
        
        const response = await fetch(`/images/${imageId}/boxes/${id}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Remove the box from the list
        this.boxes = this.boxes.filter(box => box.id !== id);
        
        // If we were editing this box, cancel the edit
        if (this.editingBox && this.editingBox.id === id) {
          this.editingBox = null;
        }
        
        // Redraw the canvas
        this.drawBoxes();
        
        showSuccess('Bounding box deleted successfully!');
      } catch (error) {
        console.error('Error deleting bounding box:', error);
        showError(`Failed to delete bounding box: ${error.message}`);
      }
    },
    
    getClassName(classId) {
      const cls = this.classes.find(c => c.id === classId);
      return cls ? cls.name : 'Unknown';
    }
  };
}
