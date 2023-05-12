window.onload = function () {
    console.log('Window loaded');

    // Establish a connection with the server
    const socket = io.connect("http://" + document.domain + ":" + location.port);

    // When the connection is established
    socket.on("connect", () => {
        console.log("Connected to the server");
    });

    // Function to handle both note updates and new notes
    function handleNoteEvent(data) {
        console.log("Received note event:", data);

        if (data.is_new) {
            console.log("Handling new note event");
            // Add the new note to the E-Ink board
            // This is just an example; adapt this code based on your actual HTML structure and note representation
            const noteBox = document.querySelector(`.eink-note-box[data-group-id="${data.group_id}"]`);
            if (noteBox) {
                const newNote = document.createElement("div");
                newNote.classList.add("eink-note");
                newNote.setAttribute("data-note-id", data.note_id);
                newNote.innerHTML = `
          <p><strong>${data.note_content}</strong></p>
          <span class="eink-note-details">${data.member_name} at ${data.date_created}</span>
        `;
                noteBox.appendChild(newNote);
            }
        } else {
            console.log("Handling note update event");
            // Update the note on the E-Ink board
            const noteElement = document.querySelector(`.eink-note[data-note-id="${data.note_id}"]`);
            if (noteElement) {
                noteElement.querySelector("strong").textContent = data.note_content;
            }
        }
    }

    function handleGroupAddedEvent(data) {
        console.log("Received new group event:", data);
      
        // Add the group to the E-Ink board
        const groupElement = document.querySelector(`.eink-note-box[data-group-id="${data.group_id}"]`);
        if (!groupElement) {
          const newGroup = document.createElement("div");
          newGroup.classList.add("eink-note-box");
          newGroup.setAttribute("data-group-id", data.group_id);
          newGroup.innerHTML = `<div class="eink-note-box-title">${data.group_name}</div>`;
          document.getElementById("eink-note-box-container").appendChild(newGroup);
        }
      }

    function deleteNote(note_id) {
        fetch('/delete_note/' + note_id)
            .then((response) => {
                if (response.ok) {
                    return response.json();
                } else {
                    throw new Error('Failed to delete the note');
                }
            })
            .then((data) => {
                console.log('Note deleted:', data.note_id);
            })
            .catch((error) => {
                console.error('Error:', error);
            });
    }

    function handleGroupDeletedEvent(data) {
        console.log("Received group_deleted event:", data);

        // Remove the group from the E-Ink board
        const groupElement = document.querySelector(`.eink-note-box[data-group-id="${data.group_id}"]`);
        if (groupElement) {
            groupElement.remove();
        }
    }

    // Listen for note events from the server
    socket.on("note_update", (data) => {
        console.log("Received note_update event:", data);
        handleNoteEvent(data);
    });

    // Add a new note to the E-Ink board
    console.log('Setting up new_note listener');
    socket.on('new_note', (data) => {
        console.log('New note received', data);
        handleNoteEvent(data);
    });

    // Add logging for disconnect and reconnect events
    socket.on("disconnect", () => {
        console.log("Disconnected from the server");
    });

    socket.on("reconnect", () => {
        console.log("Reconnected to the server");
    });

    socket.on("reconnecting", (attempt) => {
        console.log("Attempting to reconnect to the server, attempt number:", attempt);
    });

    socket.on('delete_note', (data) => {
        console.log('Delete note received', data);
        const noteElement = document.querySelector(`.eink-note[data-note-id="${data.note_id}"]`);
        if (noteElement) {
            noteElement.remove();
        }
    });

    socket.on("group_deleted", (data) => {
        console.log("Received group_deleted event:", data);
        handleGroupDeletedEvent(data);
    });

    socket.on("new_group", (data) => {
        console.log("Received new_group event:", data);
        handleGroupAddedEvent(data);
    });
};
