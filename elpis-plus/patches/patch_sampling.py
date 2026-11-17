"""elpis-plus 0001: native sampling, seed and stop strings. Greedy requests keep the exact original path."""
import sys
p = sys.argv[1]
s = open(p).read()

def sub(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)

sub("from exllamav3.generator.sampler.presets import ArgmaxSampler",
    "from exllamav3.generator.sampler.presets import ArgmaxSampler, ComboSampler")

sub('''    max_tokens: int
    stream: bool
    include_usage: bool
    skip_special_tokens: bool
''', '''    max_tokens: int
    stream: bool
    include_usage: bool
    skip_special_tokens: bool
    # elpis-plus: None = greedy (the original ArgmaxSampler path, byte-identical job arguments)
    sampling: dict[str, float | int] | None = None
    seed: int | None = None
    stop: tuple[str, ...] = ()

    def is_greedy_identity(self) -> bool:
        """True when the native job is exactly the original greedy job."""
        return self.sampling is None and self.seed is None and not self.stop
''')

sub('''    temperature = body.get("temperature", 0)
    if type(temperature) not in {int, float} or temperature != 0:
        msg = "temperature must be numeric zero (greedy)"
        raise APIError(msg)
    for name, identity in GREEDY_IDENTITY.items():
        if name in body and (
            type(body[name]) not in {int, float} or body[name] != identity
        ):
            msg = f"{name} must be numeric {identity} (greedy identity)"
            raise APIError(msg)
''', '''    sampling = parse_sampling(body)
    seed = None
    if body.get("seed") is not None:
        if type(body["seed"]) is not int or not 0 <= body["seed"] < 2**63:
            msg = "seed must be a non-negative integer"
            raise APIError(msg)
        seed = body["seed"] if sampling is not None else None  # greedy ignores the seed
    stop = parse_stop(body.get("stop"))
''')

sub('''    return Options(max_tokens, stream, include_usage, skip)
''', '''    return Options(max_tokens, stream, include_usage, skip, sampling, seed, stop)


# elpis-plus sampling limits (OpenAI-compatible names; repetition_penalty / top_k / min_p as in vLLM)
SAMPLING_RANGES: dict[str, tuple[float, float]] = {
    "temperature": (0.0, 2.0),
    "top_p": (0.0, 1.0),
    "min_p": (0.0, 1.0),
    "frequency_penalty": (-2.0, 2.0),
    "presence_penalty": (-2.0, 2.0),
    "repetition_penalty": (0.0, 2.0),
}
MAX_STOP_STRINGS = 8
MAX_STOP_CHARS = 256


def parse_sampling(body: dict[str, JSON]) -> dict[str, float | int] | None:
    """Validate sampling controls. None when the request is greedy (temperature 0 or top_k 1 and every
    penalty at its identity), so greedy requests keep the original fused argmax / tree-verify path."""
    values: dict[str, float | int] = {}
    for name, (lo, hi) in SAMPLING_RANGES.items():
        if name in body and body[name] is not None:
            v = body[name]
            if type(v) not in {int, float} or not lo <= v <= hi or v != v:
                msg = f"{name} must be a number in [{lo:g}, {hi:g}]"
                raise APIError(msg)
            values[name] = float(v)
    top_k = body.get("top_k")
    if top_k is not None:
        if type(top_k) is not int or top_k < -1 or top_k > 1000:
            msg = "top_k must be an integer in [-1, 1000] (0 or -1 disables it)"
            raise APIError(msg)
        values["top_k"] = max(top_k, 0)
    temperature = values.get("temperature", 0.0)
    penalties = (values.get("frequency_penalty", 0.0), values.get("presence_penalty", 0.0),
                 values.get("repetition_penalty", 1.0))
    if (temperature == 0.0 or values.get("top_k") == 1) and penalties == (0.0, 0.0, 1.0):
        return None
    if temperature == 0.0 and penalties != (0.0, 0.0, 1.0):
        msg = "penalties require temperature > 0 (greedy decoding is served on the exact argmax path)"
        raise APIError(msg)
    return values


def parse_stop(value: JSON) -> tuple[str, ...]:
    """Validate the OpenAI `stop` field: a string or a list of up to MAX_STOP_STRINGS nonempty strings."""
    if value is None:
        return ()
    items = [value] if isinstance(value, str) else value
    if not isinstance(items, list) or len(items) > MAX_STOP_STRINGS or not all(
        isinstance(x, str) and 0 < len(x) <= MAX_STOP_CHARS for x in items
    ):
        msg = f"stop must be a nonempty string or a list of at most {MAX_STOP_STRINGS} nonempty strings"
        raise APIError(msg)
    return tuple(dict.fromkeys(items))


def build_sampler(options: Options) -> object:
    """The original ArgmaxSampler for greedy requests; a ComboSampler otherwise."""
    if options.sampling is None:
        return ArgmaxSampler()
    s = options.sampling
    return ComboSampler(
        rep_p=s.get("repetition_penalty", 1.0),
        freq_p=s.get("frequency_penalty", 0.0),
        pres_p=s.get("presence_penalty", 0.0),
        temperature=s.get("temperature", 1.0),
        min_p=s.get("min_p", 0.0),
        top_k=int(s.get("top_k", 0)),
        top_p=s.get("top_p", 1.0),
    )
''')

sub('''    "skip_special_tokens",
    "n",
} | set(GREEDY_IDENTITY)''', '''    "skip_special_tokens",
    "n",
    "top_k",
    "seed",
    "stop",
} | set(GREEDY_IDENTITY)''')

sub('''        job = Job(
            input_ids=ids,
            max_new_tokens=pending.options.max_tokens,
            sampler=ArgmaxSampler(),
            stop_conditions=self.stop_ids,
            decode_special_tokens=not pending.options.skip_special_tokens,
            identifier=pending.identifier,
        )''', '''        options = pending.options
        if options.is_greedy_identity():
            job = Job(
                input_ids=ids,
                max_new_tokens=options.max_tokens,
                sampler=ArgmaxSampler(),
                stop_conditions=self.stop_ids,
                decode_special_tokens=not options.skip_special_tokens,
                identifier=pending.identifier,
            )
        else:
            # elpis-plus: sampled / stop-string jobs take the generator's serial verify path (the DFlash2 chain draft is
            # accepted while the sampled target token matches it, which keeps the target distribution exact)
            job = Job(
                input_ids=ids,
                max_new_tokens=options.max_tokens,
                sampler=build_sampler(options),
                seed=options.seed if options.seed is not None else int.from_bytes(os.urandom(4), "little"),
                stop_conditions=[*self.stop_ids, *options.stop],
                decode_special_tokens=not options.skip_special_tokens,
                identifier=pending.identifier,
            )''')
open(p, "w").write(s)
print("patched")
