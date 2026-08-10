# MOSQUITO AI - MOTOR

**Spikes become movement.**

`mosquito-motor` is the wing and proboscis of the system: the layer that takes
spike rates from [`mosquito-brain`](https://github.com/MosquitoAGI/mosquito-brain)
and turns them into cursor displacement, clicks, scrolls and retreats.

    MOTOR_X -> dx      MOTOR_Y -> dy
    CLICK   -> contact SCROLL  -> travel
    BACK    -> retreat

## Design rule

The motor layer has no opinions. It does not decide to click - it executes
what the behavior layer releases. Rate in, displacement out, clamped every
tick.

| action | mapping | clamp |
| --- | --- | --- |
| MOTOR_X | lateral rate - opposite rate | +/- 18 px/tick |
| MOTOR_Y | vertical rate - opposite rate | +/- 18 px/tick |
| CLICK | threshold crossing | one click per settle |
| SCROLL | integral of rate | +/- 400 px/tick |
| BACK | threshold crossing | one action per episode |

## Layout

| file | role |
| --- | --- |
| `mapping.py` | action enum and spike-to-action wiring |
| `controller.py` | rates to displacement, rate limiting, caps |
| `cursor.py` | position state and interpolation |
| `mouse.py` | click execution with settle delay |
| `scroll.py` | wheel deltas |

## Status

v0.3.0

- [x] displacement mapping with per-tick caps
- [x] output rate limit (drop to 60 Hz)
- [x] smooth interpolation between ticks
- [x] click only after the position settles
- [ ] release policy tests against recorded hunts

## Where it fits

| repo | role |
| --- | --- |
| [`mosquito-brain`](https://github.com/MosquitoAGI/mosquito-brain) | upstream spikes |
| [`mosquito-behavior`](https://github.com/MosquitoAGI/mosquito-behavior) | release decisions |
| [`mosquito-browser`](https://github.com/MosquitoAGI/mosquito-browser) | the surface being driven |
| [`mosquito-simulation`](https://github.com/MosquitoAGI/mosquito-simulation) | replay of motor traces |

## License

MIT - see `LICENSE`.
