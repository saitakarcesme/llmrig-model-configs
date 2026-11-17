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
      if (requestId === this._requestSeq && resetId === this._resetSeq) {
        this.rows = rows;
        this.loading = false;
      }
      return this.rows;
    } catch (err) {
      if (requestId === this._requestSeq && resetId === this._resetSeq) {
        this.loading = false;
      }
      throw err;
    }
  }

  reset() {
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    this._resetSeq++;
  }
}