import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Without vitest's `globals: true`, testing-library's automatic afterEach-based
// unmounting never registers, so each test's rendered DOM silently accumulates
// across the whole file. Explicit cleanup here is what makes render() isolated per test.
afterEach(() => {
  cleanup();
});
