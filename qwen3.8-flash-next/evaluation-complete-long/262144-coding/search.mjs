export class SearchController {
  constructor(fetcher) {
    this.fetcher = fetcher;
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
    // Token identifying the most recent search request. Responses from
    // older requests are discarded so they cannot overwrite newer state.
    this._requestToken = 0;
    // Generation counter incremented on reset so that requests completing
    // after a reset cannot repopulate the cleared rows.
    this._generation = 0;
  }

  async search(query, page = 1) {
    this.query = query;
    this.page = page;
    this.loading = true;
    const token = ++this._requestToken;
    const generation = this._generation;
    let rows;
    try {
      rows = await this.fetcher(query, page);
    } catch (err) {
      // Only clear loading if this request is still the latest one and no
      // reset happened while it was in flight.
      if (token === this._requestToken && generation === this._generation) {
        this.loading = false;
      }
      throw err;
    }
    // Stale response (a newer search was started) or a reset happened while
    // in flight: do not touch rows/loading.
    if (token !== this._requestToken || generation !== this._generation) {
      return this.rows;
    }
    this.rows = rows;
    this.loading = false;
    return this.rows;
  }

  reset() {
    this._generation++;
    this._requestToken++; // Invalidate any in-flight requests.
    this.query = '';
    this.page = 1;
    this.rows = [];
    this.loading = false;
  }
}