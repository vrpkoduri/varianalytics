interface NettingAlertProps {
  message: string
}

export function NettingAlert({ message }: NettingAlertProps) {
  return (
    <div className="my-2 px-2.5 py-1.5 rounded-md bg-purple-surface border-l-2 border-purple text-[10px]">
      <b className="text-purple">Netting detected:</b>{' '}
      <span className="text-tx-secondary">{message}</span>
    </div>
  )
}
