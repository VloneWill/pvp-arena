import { useEffect, useRef } from "react";

/**
 * Hook to manage polling for match state.
 * Automatically clears interval on unmount or when matchId changes.
 * 
 * @param {number|null} matchId - Match ID to poll, or null to stop
 * @param {Function} pollFn - Function to call on each poll
 * @param {number} intervalMs - Polling interval in milliseconds (default: 1000)
 */
export function useMatchPolling(matchId, pollFn, intervalMs = 1000) {
  const intervalRef = useRef(null);
  const pollFnRef = useRef(pollFn);

  // Keep the latest pollFn in a ref so we don't need to restart polling when it changes
  useEffect(() => {
    pollFnRef.current = pollFn;
  }, [pollFn]);

  useEffect(() => {
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Start polling if we have a matchId and pollFn
    if (matchId && pollFnRef.current) {
      intervalRef.current = setInterval(() => {
        pollFnRef.current?.();
      }, intervalMs);
    }

    // Cleanup on unmount or when dependencies change
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [matchId, intervalMs]);
}

/**
 * Hook to manage polling for matchmaking status.
 * Separate from match polling to avoid conflicts.
 */
export function useMatchmakingPolling(isWaiting, pollFn, intervalMs = 1000) {
  const intervalRef = useRef(null);
  const pollFnRef = useRef(pollFn);

  // Keep the latest pollFn in a ref so we don't need to restart polling when it changes
  useEffect(() => {
    pollFnRef.current = pollFn;
  }, [pollFn]);

  useEffect(() => {
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Start polling if waiting
    if (isWaiting && pollFnRef.current) {
      intervalRef.current = setInterval(() => {
        pollFnRef.current?.();
      }, intervalMs);
    }

    // Cleanup on unmount or when dependencies change
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isWaiting, intervalMs]);
}
