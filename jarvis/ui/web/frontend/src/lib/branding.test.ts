import { describe, expect, it } from "vitest";

import {
  OFFICIAL_REPO_LABEL,
  OFFICIAL_REPO_SLUG,
  OFFICIAL_REPO_URL,
  PRODUCT_NAME,
} from "@/lib/branding";

describe("branding identity", () => {
  it("keeps the current frontend values byte-for-byte", () => {
    expect(PRODUCT_NAME).toBe("Personal Jarvis");
    expect(OFFICIAL_REPO_SLUG).toBe("Dodaios/Dodaios");
    expect(OFFICIAL_REPO_URL).toBe(
      "https://github.com/Dodaios/Dodaios",
    );
    expect(OFFICIAL_REPO_LABEL).toBe(
      "github.com/Dodaios/Dodaios",
    );
  });
});
