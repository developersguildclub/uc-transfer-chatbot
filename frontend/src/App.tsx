import { useState } from "react";
import './App.css'

function App() {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");

  async function sendMessage() {
    if (!message.trim()) return;

    try {
      const response = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: message,
        }),
      });

      const data = await response.json();
      setReply(data.reply);
    } catch (error) {
      console.error("Error sending message:", error);
      setReply("Error connecting to backend.");
    }
  }

  return (
    <>
      <section id="center">
        <div className="hero">
        </div>
        <div>
          <h1>Transfer to your dream UC</h1>
          <p>
            with an AI advisor in your corner.
          </p>
          <p>Ask any question about GPA requirements, ASSIST.org, deadlines, and more</p>
        </div>
      </section>
      <section id="next-steps">
        <div style={{ marginTop: "2rem" }}>
          <input
            type="text"
            placeholder="Ask something..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            style={{
              padding: "12px",
              width: "300px",
              borderRadius: "8px",
              border: "1px solid #ccc",
              marginRight: "8px",
            }}
          />

          <button
            onClick={sendMessage}
            style={{
              padding: "12px 18px",
              borderRadius: "8px",
              cursor: "pointer",
            }}
          >
            Send
          </button>

          {reply && (
            <div style={{ marginTop: "1rem" }}>
              <strong>Backend reply:</strong>
              <p>{reply}</p>
            </div>
          )}
        </div>
        <div id="social">
          <ul>
            <li>
              <a href="https://github.com/developersguildclub/uc-transfer-chatbot" target="_blank">
                <svg
                  className="button-icon"
                  role="presentation"
                  aria-hidden="true"
                >
                  <use href="/icons.svg#github-icon"></use>
                </svg>
                GitHub
              </a>
            </li>
            <li>
              <a href="https://discord.gg/nqbudRdstm" target="_blank">
                <svg
                  className="button-icon"
                  role="presentation"
                  aria-hidden="true"
                >
                  <use href="/icons.svg#discord-icon"></use>
                </svg>
                Discord
              </a>
            </li>
          </ul>
        </div>
      </section>

      <div className="ticks"></div>
      <section id="spacer"></section>
    </>
  )
}

export default App
