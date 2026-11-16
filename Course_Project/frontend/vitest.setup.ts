import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Vitest does not expose globals here, so Testing Library cannot register its own cleanup.
// Without this, one test's rendered output is still on the page during the next.
afterEach(cleanup);
