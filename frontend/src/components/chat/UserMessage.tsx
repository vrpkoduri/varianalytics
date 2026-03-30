interface UserMessageProps {
  text: string
}

export function UserMessage({ text }: UserMessageProps) {
  return (
    <div className="flex justify-end mt-3.5">
      <div className="max-w-[65%] p-3 text-[11px] rounded-[14px_14px_4px_14px] bg-card border border-border text-tx-primary">
        {text}
      </div>
    </div>
  )
}
