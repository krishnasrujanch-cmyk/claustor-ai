export function can(role: string|undefined, action: string): boolean {
  const PERMISSIONS: Record<string, string[]> = {
    "contract.upload":         ["super_admin","dept_admin","contract_manager","business_viewer"],
    "contract.upload_version": ["super_admin","dept_admin","contract_manager"],
    "contract.delete":         ["super_admin","dept_admin"],
    "contract.reprocess":      ["super_admin","dept_admin","contract_manager"],
    "contract.assign_review":  ["super_admin","dept_admin","contract_manager"],
    "review.view_all":         ["super_admin","dept_admin","contract_manager"],
    "users.invite":            ["super_admin","dept_admin"],
    "users.delete":            ["super_admin","dept_admin"],
    "users.change_role":       ["super_admin","dept_admin"],
    "billing.manage":          ["super_admin"],
    "admin.access":            ["super_admin","dept_admin"],
  };
  if (!role) return false;
  return (PERMISSIONS[action]||[]).includes(role);
}
