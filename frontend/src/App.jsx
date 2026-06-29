import { useEffect, useState } from 'react'

export default function App() {
  // Three pieces of state describe the request lifecycle.
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadHello() {
      // TODO(human): fetch '/api/hello', read the JSON body, and update state.
      // On success -> setMessage(data.message). On failure -> setError(...).
      // Make sure setLoading(false) runs whether the request succeeds or fails.
    }

    loadHello()
  }, [])

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: '2rem' }}>
      <h1>ksept-lab</h1>
      {loading && <p>Loading…</p>}
      {error && <p style={{ color: 'crimson' }}>Error: {error}</p>}
      {message && <p>{message}</p>}
    </main>
  )
}
