export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    // Monotonic tokens to detect stale responses. The search token guards
    // rows/loading against superseded searches; the reset token additionally
    // prevents requests that completed after a reset from repopulating rows.
    this._searchToken = 0;
    this._resetToken = 0;
  }

  async search(query, page = 1) {
    // Preserve latest requested state immediately.
    this.query = query;
    this.page = page;
    this.loading = true;

    const searchToken = ++this._searchToken;
    const resetToken = this._resetToken;

    let rows;
    try {
      rows = await this.fetcher(query, page);
    } catch (err) {
      // Only clear loading if this request is still the current one and no
      // reset happened while it was in flight.
      if (searchToken === this._searchToken && resetToken === this._resetToken) {
        this.loading = false;
      }
      throw err;
    }

    // Drop the response if a newer search superseded it, or if reset() was
    // called after this request started.
    if (searchToken !== this._searchToken || resetToken !== this._resetToken) {
      return this.rows;
    }

    this.rows = rows;
    this.loading = false;
    return this.rows;
  }

  reset() {
    this._resetToken++;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}