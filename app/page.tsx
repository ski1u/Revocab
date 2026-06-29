"use client"

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { CornerDownRight, GripHorizontal } from 'lucide-react'

import { useLayoutEffect, useRef, useState } from 'react'

interface Vocab {
  word: string,
  pronunciation: string,
  definition: string
}

function Home() {
  const [input, setInput] = useState("")
  const [vocab, setVocab] = useState<Vocab | null>(null)

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

  return (
    <div className='p-8'>
      <div className='flex flex-col items-center justify-center'>
        <h1
          className='text-2xl font-bold tracking-tighter'>Revocab</h1>
        <p
          className='text-sm text-gray-500 w-2/3 text-center'
        >Learn vocab just by typing an ordinary word or defining a word. As simple as that.</p>
      </div>

      {vocab && (
        <div>
          <h1>{vocab.word}</h1>
          <p>{vocab.pronunciation}</p>
          <p>{vocab.definition}</p>
        </div>
      )}

      <Card
        className='fixed z-[11] flex items-center gap-2 p-2 shadow-lg'
        style={{left: pos.x, top: pos.y}}
        ref={cardRef}
      >
        <GripHorizontal
          className="cursor-grab shrink-0 touch-none active:cursor-grabbing"
          onPointerDown={onPointerDown}
          onPointerUp={onPointerUp}
          onPointerMove={onPointerMove}
        />
        <div className='flex items-center gap-2'>
          <Input
              className='text-sm'
              placeholder='Type or define a word'
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <Button
              size="icon"
              onClick={() => {}} // setVocab, LLM API action
            ><CornerDownRight/></Button>
        </div>
        </Card>
    </div>
  )
}

export default Home