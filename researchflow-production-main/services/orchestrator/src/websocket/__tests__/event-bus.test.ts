import { describe, it, expect, vi } from "vitest";
import { publish, subscribe } from "../event-bus";
import { createProtocolEvent } from "../protocol";

describe("websocket event bus", () => {
  it("delivers published events to subscribers", () => {
    const handler = vi.fn();
    const unsubscribe = subscribe(handler);

    const event = createProtocolEvent("RUN_STATUS", {
      runId: "run-123",
      projectId: "proj-456",
      status: "RUNNING",
      timestamp: new Date().toISOString(),
    });

    publish(event);

    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith(event);

    unsubscribe();
  });

  it("stops delivering after unsubscribe", () => {
    const handler = vi.fn();
    const unsubscribe = subscribe(handler);

    const event = createProtocolEvent("RUN_STATUS", {
      runId: "run-789",
      projectId: "proj-456",
      status: "COMPLETED",
      timestamp: new Date().toISOString(),
    });

    unsubscribe();
    publish(event);

    expect(handler).not.toHaveBeenCalled();
  });

  it("throws on invalid protocol events", () => {
    const invalidEvent = {
      type: "RUN_STATUS",
      timestamp: new Date().toISOString(),
      payload: {
        runId: "run-123",
        status: "RUNNING",
        timestamp: new Date().toISOString(),
      },
    };

    expect(() => publish(invalidEvent as any)).toThrow("Invalid ProtocolEvent");
  });
});
