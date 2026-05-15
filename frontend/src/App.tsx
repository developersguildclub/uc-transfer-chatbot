import './App.css'

function App() {
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
        <div id="docs">
          <ul>
            <li>
              <a href="https://react.dev/" target="_blank">
                <img className="button" alt="" />
                Start chatting!
              </a>
            </li>
          </ul>
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
