import { isValidProtocolEvent, ProtocolEvent } from "./protocol";

type EventHandler = (event: ProtocolEvent) => void;

const handlers = new Set<EventHandler>();

export function publish(event: ProtocolEvent): void {
  if (!isValidProtocolEvent(event)) {
    throw new Error("Invalid ProtocolEvent");
  }

  for (const handler of handlers) {
    handler(event);
  }
}

export function subscribe(handler: EventHandler): () => void {
  handlers.add(handler);

  return () => {
    handlers.delete(handler);
  };
}
