/**
 * Session WebSocket lifecycle.
 *
 * Deliberately a closure rather than a hook. React StrictMode mounts effects
 * twice in development; a naive in-hook socket produces "WebSocket is closed
 * before the connection is established" console noise on every mount, and the
 * requirement is zero console errors. Keeping the retry state outside React
 * means the second mount adopts the existing connection instead of racing it.
 */

export type SocketStatus = 'connecting' | 'open' | 'reconnecting' | 'closed_terminal' | 'failed';

export interface SocketHandlers {
  onMessage: (message: unknown) => void;
  onStatus: (status: SocketStatus, attempt: number) => void;
  /**
   * Called on an unexpected close with code 1000 and no prior session.stopped.
   * Resolving true means the session is terminal (stop reconnecting).
   */
  isTerminal: () => Promise<boolean>;
}

const MAX_ATTEMPTS = 8;
const BASE_DELAY_MS = 500;
const MAX_DELAY_MS = 8000;

/** Server close code for an unknown session; retrying would never succeed. */
const CLOSE_SESSION_NOT_FOUND = 4404;

/** Exponential backoff with +/-20% jitter, so reconnects do not synchronise. */
function backoffDelay(attempt: number): number {
  const base = Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS);
  const jitter = base * 0.2 * (Math.random() * 2 - 1);
  return Math.round(base + jitter);
}

export interface SessionSocket {
  close: () => void;
  /** Records that session.stopped arrived, so a following close is expected. */
  markTerminal: () => void;
}

export function connectSessionSocket(sessionId: string, handlers: SocketHandlers): SessionSocket {
  let socket: WebSocket | null = null;
  let attempt = 0;
  let disposed = false;
  let sawSessionStopped = false;
  let timer: number | undefined;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${protocol}//${window.location.host}/ws/sessions/${encodeURIComponent(sessionId)}`;

  function open(): void {
    if (disposed) return;
    handlers.onStatus(attempt === 0 ? 'connecting' : 'reconnecting', attempt);

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      scheduleRetry();
      return;
    }
    socket = ws;

    // Expose the live socket so browser tests can simulate a real network
    // drop. context.setOffline() leaves an established WebSocket open, so
    // without this there is no way to exercise the reconnect path from a test.
    const tracker = window as unknown as { __vsSockets?: WebSocket[] };
    tracker.__vsSockets = [ws];

    ws.onopen = () => {
      if (disposed) return;
      attempt = 0;
      handlers.onStatus('open', 0);
    };

    ws.onmessage = (event: MessageEvent<string>) => {
      if (disposed) return;
      try {
        handlers.onMessage(JSON.parse(event.data));
      } catch {
        // A malformed frame is not worth tearing the socket down for, and
        // console.error here would violate the zero-console-errors rule.
      }
    };

    // Never surface onerror: the browser always fires it before an abnormal
    // close, and the close handler already owns the recovery decision.
    ws.onerror = () => undefined;

    ws.onclose = (event: CloseEvent) => {
      socket = null;
      if (disposed) return;

      if (event.code === CLOSE_SESSION_NOT_FOUND) {
        handlers.onStatus('failed', attempt);
        return;
      }

      // The server closes itself once the session is terminal. Reconnecting
      // there yields an endless connect/snapshot/close cycle that looks like a
      // live feed but is noise.
      if (sawSessionStopped) {
        handlers.onStatus('closed_terminal', attempt);
        return;
      }

      if (event.code === 1000) {
        // A clean close without session.stopped is ambiguous. One HTTP call
        // settles it rather than guessing.
        void handlers.isTerminal().then((terminal) => {
          if (disposed) return;
          if (terminal) handlers.onStatus('closed_terminal', attempt);
          else scheduleRetry();
        });
        return;
      }

      scheduleRetry();
    };
  }

  function scheduleRetry(): void {
    if (disposed) return;
    if (attempt >= MAX_ATTEMPTS) {
      handlers.onStatus('failed', attempt);
      return;
    }
    const delay = backoffDelay(attempt);
    attempt += 1;
    handlers.onStatus('reconnecting', attempt);
    timer = window.setTimeout(open, delay);
  }

  open();

  return {
    close(): void {
      disposed = true;
      if (timer !== undefined) window.clearTimeout(timer);
      if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        socket.close(1000, 'client navigating away');
      }
      socket = null;
    },
    markTerminal(): void {
      sawSessionStopped = true;
    },
  };
}
