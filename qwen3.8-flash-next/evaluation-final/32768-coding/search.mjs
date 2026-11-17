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

    const id = ++this._requestId;
    const resetId = this._resetId;
    let rows;
    try {
      rows = await this.fetcher(query, page);
    } finally {
      // Clear loading only if this is still the latest request and no reset
      // occurred while it was in flight. A superseded request must not
      // clobber the loading state of a newer request.
      if (resetId === this._resetId && id === this._requestId) {
        this.loading = false;
      }
    }
    // Ignore stale responses: a newer request superseded this one, or a
    // reset happened while this request was in flight.
    if (resetId !== this._resetId || id !== this._requestId) {
      return this.rows;
    }
    this.rows = rows;
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