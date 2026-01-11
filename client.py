import tkinter as tk
from tkinter import scrolledtext, Entry, Button, END
import requests
import json

class ChatApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("SQL Data Science Assistant")
        self.root.geometry("800x600")

        # Conversation history
        self.conversation_history = []

        # Create UI elements
        self.create_widgets()

    def create_widgets(self):
        # Chat display area
        self.chat_display = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            state='disabled',
            bg="#f0f0f0",
            font=("Arial", 12)
        )
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Input frame
        input_frame = tk.Frame(self.root)
        input_frame.pack(padx=10, pady=10, fill=tk.X)

        # Message entry
        self.message_entry = Entry(
            input_frame,
            font=("Arial", 12),
            width=70
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.message_entry.bind("<Return>", self.send_message)

        # Send button
        send_button = Button(
            input_frame,
            text="Send",
            command=self.send_message,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12)
        )
        send_button.pack(side=tk.RIGHT)

        # Clear button
        clear_button = Button(
            input_frame,
            text="Clear",
            command=self.clear_conversation,
            bg="#f44336",
            fg="white",
            font=("Arial", 10)
        )
        clear_button.pack(side=tk.RIGHT, padx=(0, 5))

    def send_message(self, event=None):
        user_message = self.message_entry.get()
        if not user_message.strip():
            return

        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Display user message
        self.display_message("You: " + user_message, "#ffffff")

        # Clear the entry field
        self.message_entry.delete(0, END)

        # Disable UI during API call
        self.toggle_ui_state(False)

        # Send to server in a separate thread to prevent GUI freezing
        self.root.after(100, self.process_server_response)

    def process_server_response(self):
        try:
            # Prepare payload with instruction about plaintext output
            payload = {
                "conversationHistory": [
                    {
                        "role": "system",
                        "content": "All responses must be in plaintext format only. Do not use any markdown, HTML, or other markup languages as the output will be displayed as plain text without any formatting."
                    }
                ] + self.conversation_history
            }

            # Send request to server
            response = requests.post(
                "http://localhost:8000/chat",
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload)
            )

            if response.status_code == 200:
                bot_response = response.text

                # Add bot response to conversation history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": bot_response
                })

                # Display bot response
                self.display_message("Assistant: " + bot_response, "#e0f7fa")
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                self.display_message("System: " + error_msg, "#ffebee")
                print(error_msg)

        except requests.exceptions.ConnectionError:
            error_msg = "Could not connect to server. Please make sure the server is running on http://localhost:8000"
            self.display_message("System: " + error_msg, "#ffebee")
            print(error_msg)
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            self.display_message("System: " + error_msg, "#ffebee")
            print(error_msg)
        finally:
            # Re-enable UI
            self.toggle_ui_state(True)

    def display_message(self, message, bg_color):
        self.chat_display.config(state='normal', bg=bg_color)
        self.chat_display.insert(tk.END, message + "\n\n")
        self.chat_display.config(state='disabled')
        self.chat_display.yview(tk.END)  # Auto-scroll to bottom

    def toggle_ui_state(self, enabled):
        state = 'normal' if enabled else 'disabled'
        self.message_entry.config(state=state)

        # Find and update the send button
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button) and child.cget("text") == "Send":
                        child.config(state=state)

    def clear_conversation(self):
        self.conversation_history = []
        self.chat_display.config(state='normal')
        self.chat_display.delete(1.0, END)
        self.chat_display.config(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApplication(root)
    root.mainloop()