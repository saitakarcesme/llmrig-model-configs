export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    this._requestId = 0;
    this._resetId = 0;
  }

  async search(query, page = 1) {
    // Preserve latest requested state immediately.
    this.query = query;
    this.page = page;
    this.loading = true;

    const requestId = ++this._requestId;
    const resetId = this._resetId;

    let rows;
    try {
      rows = await this.fetcher(query, page);
    } catch (err) {
      // Only clear loading if this is still the latest request and no reset occurred.
      if (requestId === this._requestId && resetId === this._resetId) {
        this.loading = false;
      }
      throw err;
    }

    // Discard stale responses: a newer search was started, or a reset happened
    // after this request was issued.
    if (requestId !== this._requestId || resetId !== this._resetId) {
      return this.rows;
    }

    this.rows = rows;
    this.loading = false;
    return this.rows;
  }

  reset() {
    this._resetId++;
    this._requestId++; // invalidate any in-flight requests
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}