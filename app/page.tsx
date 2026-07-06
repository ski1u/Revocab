"use client"

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { CornerDownRight, GripHorizontal, Loader2, RotateCcw } from 'lucide-react'

import { useLayoutEffect, useRef, useState } from 'react'

interface Vocab {
  word?: string,
  pronunciation?: string,
  definition?: string,
  input_from: string
}

// Tolerantly pull each string field out of still-streaming JSON, even before
// the closing quote has arrived. Keeps up as the model emits the answer.
function parsePartialVocab(buf: string): Partial<Vocab> {
  const grab = (key: string) => {
    const m = buf.match(new RegExp(`"${key}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)`))
    if (!m) return undefined
    try { return JSON.parse(`"${m[1]}"`) } catch { return m[1] }
  }
  const out: Partial<Vocab> = {}
  const w = grab("word");          if (w !== undefined) out.word = w
  const p = grab("pronunciation"); if (p !== undefined) out.pronunciation = p
  const d = grab("definition");    if (d !== undefined) out.definition = d
  return out
}

function Home() {
  const [input, setInput] = useState("")
  const [vocab, setVocab] = useState<Vocab | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [status, setStatus] = useState("")
  const lastRequestTime = useRef(0)

  const dragging = useRef(false)
  const offset = useRef({ x: 0, y: 0 })
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const cardRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    const card = cardRef.current
    if (!card) return
    const { width, height } = card.getBoundingClientRect()
    setPos({
      x: (window.innerWidth - width) / 2,
      y: (window.innerHeight - height) / 2,
    })
  }, [])

  const onPointerDown = (e: React.PointerEvent) => {
    dragging.current = true
    // offset = where inside the card you grabbed, so it doesn't jump
    offset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y }
    e.currentTarget.setPointerCapture(e.pointerId)
  }; const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging.current) return
    setPos({ x: e.clientX - offset.current.x, y: e.clientY - offset.current.y })
  }; const onPointerUp = (e: React.PointerEvent) => {
    dragging.current = false
    e.currentTarget.releasePointerCapture(e.pointerId)
  }

  const RATE_LIMIT_MS = 3000

  function isRateLimited() {
    const now = Date.now()
    if (now - lastRequestTime.current < RATE_LIMIT_MS) return true
    lastRequestTime.current = now; return false
  }

  const canSend = input.trim().length > 2 && !loading
  const canRotate = !!vocab && !loading

  // ---

  async function send(input: string) { // SEND
    if (!canSend || isRateLimited()) return
    setLoading(true)
    setVocab(null)
    setStatus("")
    const res = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: input })
    })

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()

    let sseBuffer = ""    // incomplete SSE frames across reads
    let jsonBuffer = ""   // accumulated model text

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      sseBuffer += decoder.decode(value, { stream: true })

      const frames = sseBuffer.split("\n\n")
      sseBuffer = frames.pop() ?? ""          // keep trailing partial frame

      for (const frame of frames) {
        if (!frame.trim()) continue
        const event = JSON.parse(frame.replace(/^data:\s*/, ""))

        if (event.status) setStatus(event.status)
        if (event.chunk) {
          jsonBuffer += event.chunk
          const partial = parsePartialVocab(jsonBuffer)
          if (partial.word) setVocab({ ...partial, input_from: input })
        }
        if (event.done) setVocab({ ...JSON.parse(event.reply), input_from: input })
      }
    }
    setLoading(false)
  }
  
  async function rotate() { // ROTATE
    if (!canRotate || isRateLimited()) return
    setLoading(true)
    const res = await fetch("http://localhost:8000/rotate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ word: vocab?.word, input_from: vocab?.input_from })
    }); const data = await res.json()

    setVocab({ ...JSON.parse(data.reply), input_from: vocab!.input_from })
    setLoading(false)
  }

  // ---

  return (
    <div className='p-8'>
      <div className='flex flex-col'>
        <h1
          className='text-3xl font-bold tracking-tighter'>Revocab</h1>
        <p
          className='text-sm text-gray-500 w-2/3'
        >Learn vocab just by typing an ordinary word or defining a word. As simple as that.</p>
      </div>

      {vocab ? (
      <div className='mt-20 space-y-4 h-fit'>
        <div>
          <h1 className='font-semibold text-xl text-gray-700'>{vocab.word}</h1>
          <p className='text-gray-400 italic text-sm'>{vocab.pronunciation}</p>
        </div>
        <p className='text-gray-500'>{vocab.definition}</p>
      </div>
      ) : (
      <div className='mt-20 space-y-8 h-fit'>
        <div className='space-y-2'>
          {loading && <p className='text-sm'>{status}</p>}
          <div className='w-64 h-8 rounded-2xl bg-gray-600'></div>
          <div className='w-32 h-4 rounded-2xl bg-gray-400'></div>
        </div>
        <div className='space-y-2'>
          <div className='w-64 h-4 rounded-lg bg-gray-500'></div>
          <div className='w-48 h-4 rounded-lg bg-gray-500'></div>
        </div>
      </div>
      )}

      <Card
        className='fixed z-11 flex items-center gap-2 p-2 shadow-lg w-64'
        style={{left: pos.x, top: pos.y}}
        ref={cardRef}
      >
        <GripHorizontal
          className="cursor-grab shrink-0 touch-none active:cursor-grabbing"
          onPointerDown={onPointerDown}
          onPointerUp={onPointerUp}
          onPointerMove={onPointerMove}
        />
        <div className='flex flex-col gap-2 w-full'>
          <Textarea
              className='text-sm w-full min-h-12 max-h-24'
              placeholder='Type or define a word'
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <div className='flex w-full gap-1'>
              <Button
                className='w-2/3'
                size="icon"
                disabled={!canSend}
                onClick={() => send(input)}
              >{loading && !vocab ? <Loader2 className='animate-spin' /> : <CornerDownRight/>}</Button>
              <Button
                className='w-1/3'
                size="icon"
                variant="outline"
                disabled={!canRotate}
                onClick={() => rotate()}
              >{loading && vocab ? <Loader2 className='animate-spin' /> : <RotateCcw/>}</Button>
            </div>
        </div>
        </Card>
    </div>
  )
}

export default Home