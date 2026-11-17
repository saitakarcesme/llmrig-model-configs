export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    this._requestSeq = 0;
    this._resetSeq = 0;
  }

  async search(query, page = 1) {
    this.query = query;
    this.page = page;
    this.loading = true;
    const requestId = ++this._requestSeq;
    const resetId = this._resetSeq;
    try {
      const rows = await this.fetcher(query, page);
      // Ignore responses from stale requests (superseded by a newer query)
      // or requests that completed after a reset (must not repopulate cleared rows).
      if (requestId !== this._requestSeq || resetId !== this._resetSeq) {
        return this.rows;
      }
      this.rows = rows;
      return this.rows;
    } finally {
      // Only the latest in-flight request is allowed to clear the loading state.
      if (requestId === this._requestSeq && resetId === this._resetSeq) {
        this.loading = false;
      }
    }
  }

  reset() {
    this._resetSeq++;
    this._requestSeq++; // invalidate any in-flight requests
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}