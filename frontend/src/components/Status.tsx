export function Loading() {
  return <p className="muted center">Загрузка…</p>;
}

export function ErrorBox({ message }: { message: string }) {
  return <p className="error">{message}</p>;
}
