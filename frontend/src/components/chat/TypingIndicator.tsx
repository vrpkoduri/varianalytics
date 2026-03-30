export function TypingIndicator() {
  return (
    <div className="flex items-center gap-px py-1">
      <span
        className="inline-block w-[5px] h-[5px] rounded-full bg-teal"
        style={{ animation: 'typingBounce 1.2s ease infinite' }}
      />
      <span
        className="inline-block w-[5px] h-[5px] rounded-full bg-teal"
        style={{ animation: 'typingBounce 1.2s ease infinite', animationDelay: '0.15s' }}
      />
      <span
        className="inline-block w-[5px] h-[5px] rounded-full bg-teal"
        style={{ animation: 'typingBounce 1.2s ease infinite', animationDelay: '0.3s' }}
      />
    </div>
  )
}
