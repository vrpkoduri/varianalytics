import { cn } from '@/utils/theme'

interface AgentAvatarProps {
  isStreaming?: boolean
}

export function AgentAvatar({ isStreaming }: AgentAvatarProps) {
  return (
    <div
      className={cn(
        'w-6 h-6 rounded-md flex items-center justify-center shrink-0',
        isStreaming && 'animate-breathe'
      )}
      style={{ background: 'linear-gradient(135deg, #002C77, #00A8C7)' }}
    >
      <span className="text-[9px] font-[800] text-white leading-none">M</span>
    </div>
  )
}
