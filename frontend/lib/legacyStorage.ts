// Vidura was called FinSight. Saved browser state used `fs_*` keys; it now uses `vd_*`.
// Reads go through these helpers so nothing saved under the old key is lost: the old value is
// copied to the new key the first time it is read, and the old key is removed.

const OLD_PREFIX = "fs_";
const NEW_PREFIX = "vd_";

/** The pre-rebrand name of a `vd_*` storage key. */
export const legacyKey = (key: string): string =>
  key.startsWith(NEW_PREFIX) ? OLD_PREFIX + key.slice(NEW_PREFIX.length) : key;

/** Read `key`, falling back to (and migrating) the value saved under its old `fs_*` name. */
export function getItemMigrating(storage: Storage, key: string): string | null {
  const current = storage.getItem(key);
  if (current !== null) return current;
  const old = legacyKey(key);
  if (old === key) return null;
  const legacy = storage.getItem(old);
  if (legacy === null) return null;
  try {
    storage.setItem(key, legacy);
    storage.removeItem(old);
  } catch {
    /* storage full or blocked: the value is still returned for this read */
  }
  return legacy;
}
