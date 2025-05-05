/**
 * Bounding Box Manager (Alpine.js Component)
 * Handles loading classes and existing boxes, selecting a class for drawing,
 * initiating/cancelling drawing mode via events sent to view.js,
 * receiving completed drawing coordinates from view.js, and handling CRUD operations for boxes.
 */
function boundingBoxManager() {
  return {
    boxes: [],          // Array of box objects from the backend { id, x_min, ..., image_class_id }
    classes: [],        // Array of class objects from the backend { id, name, color, project_id }
    selectedClassId: null, // ID of the class currently selected for drawing
    selectedBoxId: null, // Initialize selectedBoxId
    editingBox: null,   // Holds a copy of the box being edited (if any)
    viewIsInDrawingMode: false, // Tracks if view.js is in drawing mode (controlled by events)
    projectId: window.projectId, // Get project ID from global scope
    imageId: window.imageId,     // Get image ID from global scope
    loading: {          // Loading states
      classes: false,
      boxes: false
    },
    // NOTE: isDrawing state and drawing coordinate logic are now managed in view.js

    // --- Initialization ---
    init() {
      console.log("Initializing boundingBoxManager...");
      // Ensure IDs are available
      if (!this.projectId) console.error("BoundingBoxManager: Project ID not found on init!");
      if (!this.imageId) console.error("BoundingBoxManager: Image ID not found on init!");
      
      this.loadClasses();
      this.loadBoxes();

      // Listen for drawing completion event from view.js
      // detail: { normalizedCoords: { x_min, y_min, x_max, y_max }, classId: string }
      document.addEventListener('drawingComplete', (event) => {
        this.handleDrawingComplete(event.detail);
      });

      // Listen for view.js drawing state changes
      document.addEventListener('viewDrawingStarted', () => {
          console.log("boundingBoxManager: Received viewDrawingStarted event.");
          this.viewIsInDrawingMode = true;
      });
      document.addEventListener('viewDrawingEnded', () => {
          console.log("boundingBoxManager: Received viewDrawingEnded event.");
          this.viewIsInDrawingMode = false;
      });

      // Listen for box selection event from view.js (for editing/highlighting)
      // detail: { boxId: string | null }
      document.addEventListener('boxSelected', (event) => this.handleBoxSelected(event));

      // Watch for changes in selectedClassId to potentially start drawing
      this.$watch('selectedClassId', (newClassId) => {
        if (newClassId !== null && !this.viewIsInDrawingMode && !this.editingBox) {
          const selectedClass = this.classes.find(c => c.id === newClassId);
          if (selectedClass) {
            this.startDrawing(selectedClass);
          }
        }
      });
    },

    // --- Data Loading ---
    async loadClasses() {
      if (this.loading.classes) return;
      this.loading.classes = true;
      console.log("Loading classes...");
      try {
        if (!this.projectId) {
          const errorMsg = 'Project ID missing';
          console.error(`Error loading image classes: ${errorMsg}`);
          showError('Failed to load image classes.'); // Use global showError
          return;
        }

        const response = await fetch(`/projects/${this.projectId}/classes`);
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        this.classes = await response.json();
        console.log("Classes loaded:", this.classes);

        // Automatically select the first class if available and none is selected
        if (this.classes.length > 0 && !this.selectedClassId) {
            this.selectedClassId = this.classes[0].id;
            console.log("Auto-selected first class:", this.selectedClassId);
        }
      } catch (error) {
        console.error('Error loading image classes:', error);
        showError('Failed to load image classes.');
      } finally {
        this.loading.classes = false;
      }
    },

    async loadBoxes() {
      if (this.loading.boxes) return;
      this.loading.boxes = true;
      console.log("Loading existing boxes...");
      try {
        if (!this.imageId) {
          const errorMsg = 'Image ID missing';
          console.error(`Error loading bounding boxes: ${errorMsg}`);
          showError('Failed to load bounding boxes.'); // Use global showError
          return;
        }

        const response = await fetch(`/images/${this.imageId}/boxes`);
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        this.boxes = await response.json();
        console.log("Boxes loaded:", this.boxes);

        // Notify view.js to draw these boxes
        this.dispatchBoxesUpdated();
      } catch (error) {
        console.error('Error loading bounding boxes:', error);
        showError('Failed to load bounding boxes.');
      } finally {
        this.loading.boxes = false;
      }
    },

    // --- Drawing Mode Control ---
    startDrawing(selectedClass) {
      // Called by the "Draw Box" button @click event
      console.log("boundingBoxManager: startDrawing called.");
      if (!selectedClass) {
          showError("Please select a class first before drawing.");
          console.log("boundingBoxManager: No class selected.");
          return;
      }
       if (!this.classes || this.classes.length === 0) {
          showError("No classes defined for this project. Cannot draw boxes.");
           console.log("boundingBoxManager: No classes defined.");
          return;
      }

      console.log(`boundingBoxManager: Dispatching 'startDrawingMode' for class ${selectedClass.id} (${selectedClass.name})`);
      // Notify view.js to enter drawing mode
      document.dispatchEvent(new CustomEvent('startDrawingMode', {
          detail: {
              classId: selectedClass.id,
              className: selectedClass.name,
              color: this.getColorForClass(selectedClass.id) // Provide color for drawing feedback
          }
      }));
      // Note: The actual 'isDrawing' state is now managed by view.js
    },

    cancelDrawing() {
      // Called by the "Cancel" button @click event (which appears when view.js is in drawing mode)
      console.log("boundingBoxManager: cancelDrawing called. Dispatching 'cancelDrawingMode'.");
      // Notify view.js to exit drawing mode
      document.dispatchEvent(new CustomEvent('cancelDrawingMode'));
    },

    // --- Handling Completed Drawing ---
    handleDrawingComplete(detail) {
      // Received final coordinates from view.js
      console.log("boundingBoxManager: 'drawingComplete' event received:", detail);
      const { x_min, y_min, x_max, y_max } = detail.normalizedCoords;
      const classId = detail.classId;

      if (!classId || x_min === undefined || y_min === undefined || x_max === undefined || y_max === undefined) {
          console.error("boundingBoxManager: Invalid data received from drawingComplete event.", detail);
          showError("Failed to save box: Invalid drawing data received.");
          return;
      }

      // Optional: Verify classId matches selectedClassId, though view.js should send the one used
      if (classId !== this.selectedClassId) {
          console.warn(`boundingBoxManager: Drawing completed for class ${classId}, but selected class was ${this.selectedClassId}. Saving with ${classId}.`);
          // You might want to update selectedClassId here if that's the desired behavior
          // this.selectedClassId = classId;
      }

      this.saveBox(x_min, y_min, x_max, y_max, classId);
    },

    // --- CRUD Operations ---
    async saveBox(x_min, y_min, x_max, y_max, classId) {
      console.log(`boundingBoxManager: Attempting to save box for class ${classId}:`, { x_min, y_min, x_max, y_max });
      try {
        if (!classId) throw new Error('Class ID is missing.');
        if (!this.imageId) throw new Error("Image ID missing");

        // Basic validation (ensure min < max)
        if (x_min >= x_max || y_min >= y_max) {
            console.warn("boundingBoxManager: Attempting to save box with zero or negative dimensions.", { x_min, y_min, x_max, y_max });
             // Depending on requirements, either throw error or allow (backend might handle)
             // throw new Error("Box dimensions are invalid.");
             showError("Box has zero or negative size. Not saved.");
             // Ensure view.js cleans up even if save fails
             document.dispatchEvent(new CustomEvent('cancelDrawingMode')); // Make sure view.js exits drawing state
             return;
        }


        const response = await fetch(`/images/${this.imageId}/boxes?image_class_id=${classId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ x_min, y_min, x_max, y_max, comment: '' }) // Add comment field if needed later
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: `HTTP error! Status: ${response.status}` }));
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }

        const newBox = await response.json();
        console.log("boundingBoxManager: Box saved successfully:", newBox);
        this.boxes.push(newBox); // Add to local list
        this.dispatchBoxesUpdated(); // Notify view.js
        showSuccess('Bounding box added!');

      } catch (error) {
        console.error('Error saving bounding box:', error);
        showError(`Failed to save bounding box: ${error.message}`);
        // Ensure view.js cleans up drawing state on error
        document.dispatchEvent(new CustomEvent('cancelDrawingMode'));
      }
    },

     // TODO: Implement editBox, updateBox later if needed for sidebar editing form
    editBox(boxId) {
        const box = this.boxes.find(b => b.id === boxId);
        if (box) {
            console.log("boundingBoxManager: Setting up edit for box:", box);
            this.editingBox = { ...box }; // Create a copy for editing form
            // Notify view.js to highlight the box being edited
            document.dispatchEvent(new CustomEvent('highlightBox', { detail: { boxId: box.id } }));
            // Need UI for editing: e.g., a modal or form bound to this.editingBox
            // showModal('edit-box-modal'); // Example
        } else {
            console.warn("boundingBoxManager: Box not found for editing:", boxId);
        }
    },

    cancelEdit() {
        console.log("boundingBoxManager: Cancelling edit.");
        this.editingBox = null;
        // Notify view.js to remove any highlighting
        document.dispatchEvent(new CustomEvent('highlightBox', { detail: { boxId: null } }));
        // hideModal('edit-box-modal'); // Example
    },

    async updateBox() {
        if (!this.editingBox) return;
        console.log("boundingBoxManager: Attempting to update box:", this.editingBox.id);
        try {
            const { id, image_class_id, comment } = this.editingBox; // Extract relevant fields
             if (!this.imageId || !id) throw new Error("Missing image ID or box ID for update.");

            const payload = { image_class_id, comment: comment || '' };
            console.log("Update payload:", payload);

            const response = await fetch(`/images/${this.imageId}/boxes/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

             if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `HTTP error! Status: ${response.status}` }));
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            }

            const updatedBox = await response.json();
            console.log("boundingBoxManager: Box updated successfully:", updatedBox);

            const index = this.boxes.findIndex(box => box.id === updatedBox.id);
            if (index !== -1) {
                this.boxes.splice(index, 1, updatedBox); // Update local list
            }
            this.dispatchBoxesUpdated(); // Notify view.js
            this.cancelEdit(); // Close edit UI
            showSuccess('Bounding box updated!');

        } catch (error) {
            console.error('Error updating bounding box:', error);
            showError(`Failed to update bounding box: ${error.message}`);
        }
    },


    async deleteBox(id) {
      // Can be called from a button in the sidebar list, or potentially triggered by view.js
      if (!confirm('Are you sure you want to delete this bounding box?')) return;
      console.log("boundingBoxManager: Attempting to delete box:", id);
      try {
        if (!this.imageId) throw new Error("Image ID missing");

        const response = await fetch(`/images/${this.imageId}/boxes/${id}`, { method: 'DELETE' });

        if (!response.ok && response.status !== 204) { // 204 No Content is success
            const errorData = await response.json().catch(() => ({ detail: `HTTP error! Status: ${response.status}` }));
            throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }

        console.log("boundingBoxManager: Box delete request successful for ID:", id);
        this.boxes = this.boxes.filter(box => box.id !== id); // Remove from local list
        this.dispatchBoxesUpdated(); // Notify view.js

        if (this.editingBox && this.editingBox.id === id) {
            this.cancelEdit(); // Close edit UI if deleting the edited box
        }
        showSuccess('Bounding box deleted!');

      } catch (error) {
        console.error('Error deleting bounding box:', error);
        showError(`Failed to delete bounding box: ${error.message}`);
      }
    },

    // --- Utility ---
    getClassName(classId) {
        const classObj = this.classes.find(cls => cls.id === classId);
        return classObj ? classObj.name : 'Unknown';
    },

    getColorForClass(classId) {
        if (!classId) return '#FF0000'; // Default red
        const classObj = this.classes.find(cls => cls.id === classId);
        if (classObj && classObj.color) {
            return classObj.color.startsWith('#') ? classObj.color : `#${classObj.color}`;
        }
        // Fallback color generation
        let hash = 0;
        for (let i = 0; i < classId.length; i++) { hash = classId.charCodeAt(i) + ((hash << 5) - hash); }
        const color = (hash & 0x00FFFFFF).toString(16).toUpperCase();
        return '#' + '00000'.substring(0, 6 - color.length) + color;
    },

    // Helper to notify view.js about box data updates (load, add, update, delete)
    dispatchBoxesUpdated() {
        const boxesWithDetails = this.boxes.map(box => ({
            ...box,
            className: this.getClassName(box.image_class_id),
            color: this.getColorForClass(box.image_class_id)
        }));
        console.log("boundingBoxManager: Dispatching 'boxesUpdated' event with:", boxesWithDetails.length, "boxes");
        document.dispatchEvent(new CustomEvent('boxesUpdated', { detail: { boxes: boxesWithDetails } }));
    },

    handleBoxSelected(event) {
      this.selectedBoxId = event.detail.boxId;
      console.log("Selected box ID:", this.selectedBoxId);
      // Optionally trigger highlight in view.js
      document.dispatchEvent(new CustomEvent('highlightBox', { detail: { boxId: this.selectedBoxId }}));
    },

     // --- Computed Properties for UI Binding (Example) ---
     get isLoading() {
       return this.loading.classes || this.loading.boxes;
     }

  }; // End of return object
} // End of function boundingBoxManager
