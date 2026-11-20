import type { Role } from "@/lib/api/types";

export const ROLE_LABEL: Record<Role, string> = {
  registrar: "Registrar",
  principal: "Principal / Director",
  dean: "Dean",
  hod: "Head of Department",
  viewer: "Governing Council",
  admin: "Administrator",
};
