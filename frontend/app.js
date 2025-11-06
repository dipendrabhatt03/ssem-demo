// API Configuration
const API_URL = 'http://localhost:8000';

// DOM Elements
const noteForm = document.getElementById('noteForm');
const noteTitleInput = document.getElementById('noteTitle');
const noteContentInput = document.getElementById('noteContent');
const notesList = document.getElementById('notesList');
const statusElement = document.getElementById('status');

// Check API health on load
async function checkHealth() {
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();

        if (data.status === 'healthy') {
            statusElement.textContent = '✓ Connected to backend and database';
            statusElement.className = 'status healthy';
        } else {
            throw new Error('Unhealthy');
        }
    } catch (error) {
        statusElement.textContent = '✗ Cannot connect to backend';
        statusElement.className = 'status error';
    }
}

// Fetch and display all notes
async function loadNotes() {
    try {
        const response = await fetch(`${API_URL}/notes`);
        const data = await response.json();

        if (data.notes.length === 0) {
            notesList.innerHTML = '<p class="empty-state">No notes yet. Create your first note above!</p>';
            return;
        }

        notesList.innerHTML = data.notes.map(note => createNoteCard(note)).join('');

        // Add event listeners to delete buttons
        document.querySelectorAll('.btn-delete').forEach(button => {
            button.addEventListener('click', () => deleteNote(button.dataset.id));
        });
    } catch (error) {
        console.error('Error loading notes:', error);
        notesList.innerHTML = '<p class="empty-state">Error loading notes. Please check if the backend is running.</p>';
    }
}

// Create note card HTML
function createNoteCard(note) {
    const date = new Date(note.created_at).toLocaleString();

    return `
        <div class="note-card">
            <div class="note-header">
                <h3 class="note-title">${escapeHtml(note.title)}</h3>
                <span class="note-date">${date}</span>
            </div>
            <p class="note-content">${escapeHtml(note.content)}</p>
            <div class="note-actions">
                <button class="btn-delete" data-id="${note.id}">Delete</button>
            </div>
        </div>
    `;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Create a new note
async function createNote(title, content) {
    try {
        const response = await fetch(`${API_URL}/notes`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ title, content }),
        });

        if (!response.ok) {
            throw new Error('Failed to create note');
        }

        // Reload notes after creating
        await loadNotes();

        // Clear form
        noteForm.reset();
    } catch (error) {
        console.error('Error creating note:', error);
        alert('Failed to create note. Please try again.');
    }
}

// Delete a note
async function deleteNote(noteId) {
    if (!confirm('Are you sure you want to delete this note?')) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/notes/${noteId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error('Failed to delete note');
        }

        // Reload notes after deleting
        await loadNotes();
    } catch (error) {
        console.error('Error deleting note:', error);
        alert('Failed to delete note. Please try again.');
    }
}

// Form submit handler
noteForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = noteTitleInput.value.trim();
    const content = noteContentInput.value.trim();

    if (title && content) {
        await createNote(title, content);
    }
});

// Initialize app
checkHealth();
loadNotes();

// Refresh notes every 30 seconds
setInterval(loadNotes, 30000);
