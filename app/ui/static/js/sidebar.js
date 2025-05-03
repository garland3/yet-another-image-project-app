// Sidebar functionality for the view page
document.addEventListener('DOMContentLoaded', () => {
  // Initialize the sidebar
  initSidebar();
});

function initSidebar() {
  // Set the initial state of the sidebar
  // The sidebar is controlled by Alpine.js in the HTML
  // This function can be used to add additional functionality
  
  // Add keyboard shortcut for toggling the sidebar
  document.addEventListener('keydown', (e) => {
    // Toggle sidebar with 'S' key
    if (e.key === 's' || e.key === 'S') {
      // REMOVED call to non-existent toggleSidebar()
      // console.log("'S' key pressed - Sidebar toggle action removed."); 
    }
  });
  
  // Make sure the image display adjusts when the sidebar is toggled
  const sidebar = document.querySelector('.sidebar');
  const mainContent = document.querySelector('.image-pane'); // Updated selector
  
  if (sidebar && mainContent) {
    // Create a mutation observer to watch for changes to the sidebar's class
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          // Adjust the main content area when the sidebar is collapsed/expanded
          // REMOVED call to adjustMainContent()
          // adjustMainContent();
        }
      });
    });
    
    // Start observing the sidebar
    observer.observe(sidebar, { attributes: true });
    
    // REMOVED Initial adjustment call
    // adjustMainContent();
  }
}

// REMOVED adjustMainContent function
/*
function adjustMainContent() {
  const sidebar = document.querySelector('.sidebar');
  const mainContent = document.querySelector('.main-content');
  
  if (sidebar && mainContent) {
    const isSidebarCollapsed = sidebar.classList.contains('collapsed');
    
    // Adjust the main content area based on the sidebar state
    if (isSidebarCollapsed) {
      mainContent.style.marginRight = '30px'; // Just enough for the toggle button
    } else {
      mainContent.style.marginRight = '320px'; // Sidebar width + some padding
    }
    
    // Adjust the image display size
    const imageDisplay = document.getElementById('image-display');
    if (imageDisplay) {
      if (isSidebarCollapsed) {
        imageDisplay.style.width = 'calc(100% - 30px)';
      } else {
        imageDisplay.style.width = 'calc(100% - 320px)';
      }
    }
    
    // Trigger a resize event to make sure the image display adjusts
    window.dispatchEvent(new Event('resize'));
  }
}
*/

// Call adjustMainContent on page load to set the initial state
document.addEventListener('DOMContentLoaded', () => {
  // Set a small timeout to ensure Alpine.js has initialized
  setTimeout(() => {
    // REMOVED adjustMainContent();
  }, 100);
});
