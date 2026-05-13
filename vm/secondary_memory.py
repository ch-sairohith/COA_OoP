class SecondaryMemory:
    """
    Simulates disk / swap space.

    When a physical frame is evicted, its byte content is saved here
    indexed by VPN. When the same VPN is faulted in again, the data
    is restored from here into the new frame — so nothing is lost.

    Without this, an evicted page's data would be gone forever, which
    would give wrong results if the test bench re-accesses evicted pages.
    """

    def __init__(self, page_size: int):
        self.page_size = page_size
        self._store: dict[int, bytearray] = {}   # VPN → saved bytes

        # Stats
        self.swap_outs = 0   # pages written to swap
        self.swap_ins  = 0   # pages restored from swap

    def has_page(self, vpn: int) -> bool:
        """True if this VPN was previously evicted and is sitting in swap."""
        return vpn in self._store

    def save(self, vpn: int, data: bytes):
        """
        Save a page's byte content to swap.
        Called right before its physical frame is reused for another VPN.
        """
        self._store[vpn] = bytearray(data)
        self.swap_outs += 1

    def restore(self, vpn: int) -> bytearray | None:
        """
        Retrieve and remove a page's saved content from swap.
        Called on a page fault when the VPN was previously evicted.
        Returns None if this VPN was never evicted (fresh page).
        """
        data = self._store.pop(vpn, None)
        if data is not None:
            self.swap_ins += 1
        return data
