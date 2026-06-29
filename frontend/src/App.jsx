import { useEffect, useState } from 'react'

export default function App() {
  // Three pieces of state describe the request lifecycle.
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadHello() {
      try {
        const res = await fetch('/api/hello')              // 1. 주문 넣기
        if (!res.ok) throw new Error(`HTTP ${res.status}`) // 3. 제대로 나왔나 확인
        const data = await res.json()                      // 2. 포장 풀기
        setMessage(data.message)                           // 성공: 메시지를 상태에 넣기
      } catch (err) {
        setError(err.message)                              // 실패: 에러 메시지를 상태에 넣기
      } finally {
        setLoading(false)                                  // 항상: 로딩 표시 끄기
      }
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
