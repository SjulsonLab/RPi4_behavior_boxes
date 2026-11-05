# Robust Raspberry Pi Rotary Encoder / Treadmill Acquisition System

## 1. Purpose

Replace the current `RPi.GPIO` callback-based treadmill decoder with a robust Raspberry Pi-only acquisition system suitable for use inside a busy behavioral experiment.

The primary goals are:

1. Reliably capture all rotary encoder transitions even while the rest of the Python behavioral stack is busy.
2. Decode quadrature position/direction from both channels A and B using both rising and falling edges.
3. Make **physical treadmill position/distance and speed** the primary outputs rather than raw encoder counts.
4. Isolate encoder acquisition from the main behavioral Python process using multiprocessing.
5. Ensure behavior-program stalls, CPU load, UI work, disk I/O, networking, etc. do not directly back-pressure encoder edge acquisition.
6. Detect and loudly report acquisition failures rather than silently returning plausible but incorrect treadmill values.
7. Continuously record a lightweight fixed-rate treadmill time series independently of the behavior loop.
8. Provide extensive diagnostics and testability so the system can be validated quantitatively before experimental use.
9. Keep the physical setup to a **single Raspberry Pi**, avoiding a required Teensy/microcontroller.
10. Keep the behavior-facing API simple enough for routine lab use.

The existing script should be treated as the behavioral/calibration reference, but not as an architecture to preserve. It currently uses `RPi.GPIO`, detects only rising edges on channel A, samples B later from within the Python callback, and computes speed from callback timing. It also uses an old calibration convention where `MM_PER_COUNT = 410950` corresponds to `0.41095 mm` per legacy A-rising count. fileciteturn0file0

---

# 2. Scope

## In scope

Implement:

- Pi 4 and Pi 5 compatible GPIO acquisition where practical.
- Kernel-timestamped GPIO edge capture.
- Both-edge quadrature decoding.
- Dedicated encoder acquisition process.
- Shared live encoder/treadmill state.
- Physical position/distance and speed estimates.
- Direction mapping between encoder rotation and animal locomotion.
- Health and integrity monitoring.
- Fixed-rate continuous treadmill logging.
- Diagnostic logging.
- Rolling raw-event diagnostics.
- Synthetic/unit/stress tests.
- Hardware validation tools/procedure.
- Graceful startup, zeroing, shutdown, and failure behavior.
- Documentation/configuration sufficient for another lab member to use the module.

## Out of scope

Do not make the decoder responsible for:

- deciding behavioral meaning of locomotion;
- movement/stillness thresholds specific to a task;
- reward logic;
- closed-loop behavioral rules;
- task-specific velocity filtering;
- behavioral trial structure;
- GUI design;
- video acquisition;
- neural-data acquisition;
- a microcontroller implementation;
- a real-time Linux kernel.

The acquisition system should provide accurate treadmill measurements from which any behavioral task can implement its own downstream logic.

Core design principle:

> This subsystem measures treadmill motion accurately. It does not decide what treadmill motion means behaviorally.

---

# 3. Required Architecture

Use the following logical architecture:

```text
Encoder A/B
    |
    v
Linux kernel GPIO edge capture
(libgpiod-compatible interface)
    |
    | kernel timestamped edge events
    | A/B identity
    | rising/falling
    | sequence numbers
    v
Dedicated encoder acquisition process
    |
    +--> quadrature decoder
    +--> position
    +--> speed
    +--> direction
    +--> diagnostics
    +--> health/integrity
    |
    v
Single-writer shared live state
    |
    +------------------------+
    |                        |
    v                        v
Behavior process        Logging process
reads latest state      samples state at fixed rate
when needed             default 200 Hz
```

There are therefore three distinct output paths:

### A. Live state

Used by behavioral code.

Contains current:

- position;
- speed;
- direction;
- timestamps;
- health/integrity state.

The behavior program may read this as frequently or infrequently as desired.

### B. Continuous treadmill record

Independent fixed-rate time series, default 200 Hz.

Used for later analysis.

It must not depend on the timing of the behavior loop.

### C. Diagnostics

Used to determine whether treadmill acquisition was trustworthy.

Includes:

- GPIO sequence gaps;
- inconsistent events;
- timing/backlog information;
- process health;
- logger health;
- diagnostic raw-event history;
- session summary.

These three functions must remain logically separate.

---

# 4. GPIO Backend

## Required approach

Use the Linux GPIO character-device interface via **libgpiod v2-style functionality** or an equivalent implementation that provides the same guarantees.

Do not use `RPi.GPIO` callbacks as the primary acquisition backend.

Do not silently fall back to `RPi.GPIO` if the required low-level backend is unavailable.

The program should fail clearly at initialization and provide an actionable error.

## Required edge information

Each acquired event must make available, at minimum:

- GPIO line/channel;
- rising versus falling edge;
- kernel event timestamp;
- event ordering/sequence information when supported.

Use the **monotonic clock** for GPIO event timestamps.

Both channels must be monitored for:

- rising edges;
- falling edges.

Therefore the decoder processes all four quadrature edge types:

```text
A rising
A falling
B rising
B falling
```

## Event processing

Prefer draining available events in batches rather than using one Python callback invocation per physical edge.

The acquisition process should:

1. wait for GPIO events;
2. read all/batched currently available events;
3. process them in kernel-reported order;
4. update decoder state;
5. return promptly to draining events.

The acquisition hot path must contain no:

- console printing;
- disk writes;
- network calls;
- GUI operations;
- behavioral calculations;
- unnecessary object creation;
- blocking communication with the behavior process.

---

# 5. Pi 4 / Pi 5 GPIO Resolution

Configuration should use familiar **BCM GPIO numbers** for the external API, e.g.:

```text
A = BCM17
B = BCM27
```

The implementation must resolve those to the appropriate Linux gpiochip/line at runtime.

Do not assume:

```text
/dev/gpiochip0
```

is always the correct user-facing chip.

The implementation should inspect available gpiochips/line information and select the chip representing the user-facing Raspberry Pi GPIO controller.

It must:

- work with current Pi 5/RP1 arrangements;
- work with Pi 4 where practical;
- tolerate kernel versions where gpiochip numbering differs;
- log exactly which gpiochip and line offsets were resolved;
- fail rather than guess if pin resolution is ambiguous.

At startup record:

```text
Pi model
OS version
kernel version
libgpiod/Python binding version
resolved gpiochip path
gpiochip label
A BCM pin
A resolved line
B BCM pin
B resolved line
```

---

# 6. GPIO Configuration

Preserve the old system's pull-up behavior unless calibration/testing determines otherwise.

Configuration must include the GPIO bias behavior explicitly.

Suggested default:

```text
bias = pull_up
```

Software/kernel debounce should default to:

```text
OFF
```

unless the encoder is established to be mechanical/contact-based and requires debouncing.

Do not introduce an arbitrary debounce interval for an optical/magnetic encoder. Excessive debounce could itself delete legitimate high-frequency quadrature events.

During hardware integration, determine and document:

- encoder type;
- encoder output voltage;
- whether outputs are push-pull/open-collector/etc.;
- whether external pull resistors exist;
- whether internal pull-ups are needed;
- whether any debounce is necessary.

The software configuration should expose debounce if supported, but it should not be silently enabled.

---

# 7. Quadrature Decoding

## Use full x4 quadrature decoding

The existing implementation effectively uses x1 decoding: only A-rising is counted.

The new implementation must decode all valid A/B transitions.

Define one raw encoder orientation as positive, for example:

```text
00 -> 01 -> 11 -> 10 -> 00
```

and the reverse sequence as negative:

```text
00 -> 10 -> 11 -> 01 -> 00
```

The exact choice of which physical rotation is internally called positive does not matter as long as it is consistent and tested.

Each valid single-step transition represents:

```text
+1 transition
or
-1 transition
```

## Do not read B later to determine an earlier A edge

Direction reconstruction must use the timestamped ordered edge stream.

For example, if an `A rising` event was captured, update A's logical state using that event itself.

Do not depend on:

```text
event happened
-> Python eventually runs
-> read A/B GPIO levels now
```

for normal quadrature reconstruction.

Current GPIO level reads are appropriate for initialization/resynchronization, not as a replacement for the historical state encoded in edge events.

---

# 8. Initial State Synchronization

At acquisition startup, establish the current two-bit A/B state before normal decoding.

Initialization must account for the possibility that the treadmill moves while acquisition is starting.

Do not silently assume the encoder remains stationary during initialization.

The implementation may choose the exact synchronization method, but it must guarantee one of:

1. the initial A/B state is synchronized correctly with queued edge events; or
2. initialization detects that a clean state cannot be established and retries/fails.

A race where:

```text
line is requested
edge occurs
current state is read
queued edge is then applied a second time
```

must not silently corrupt the decoder state.

A practical quiet-period/retry strategy is acceptable.

Production acquisition should not enter `READY` until initial A/B state has been established.

---

# 9. Encoder Direction vs Locomotion Direction

Do not use ambiguous constants like:

```text
FW
BW
```

The physical encoder's rotation direction and the animal's locomotion direction are different concepts.

Internally distinguish:

```text
encoder_direction
locomotion_direction
```

Use:

```text
+1
-1
0
```

where `0` means no current direction/motion.

Define:

```text
locomotion_sign = +1 or -1
```

so that:

```text
locomotion_position =
    encoder_position * locomotion_sign
```

and:

```text
locomotion_speed =
    encoder_speed * locomotion_sign
```

The public convention should be:

```text
animal/treadmill-user moving forward  = positive
animal/treadmill-user moving backward = negative
```

This removes the need for a user to remember that one physical encoder rotation corresponds to opposite treadmill-user motion.

`locomotion_sign` should be established during calibration rather than assumed from code.

Calibration procedure:

1. start diagnostic acquisition;
2. move treadmill in the direction corresponding to animal-forward locomotion;
3. inspect raw encoder displacement;
4. choose `locomotion_sign` such that reported locomotion position increases during animal-forward motion;
5. save this setting in configuration.

---

# 10. Calibration and Physical Units

Physical position/distance and speed are the canonical outputs.

Configuration should contain:

```text
mm_per_encoder_cycle
```

Derived automatically:

```text
mm_per_transition = mm_per_encoder_cycle / 4
```

Both values should be exposed in metadata/configuration for readability.

Only one needs to be stored as the authoritative calibration value.

For migration from the current code, the existing:

```text
MM_PER_COUNT = 410950
```

corresponds to:

```text
legacy mm_per_count = 0.41095 mm
```

Because the old code counts one A-rising event per quadrature cycle, the likely migration value for unchanged hardware is:

```text
mm_per_encoder_cycle = 0.41095
mm_per_transition    = 0.1027375
```

This should be treated as a migration hypothesis and physically verified before production use.

Do not blindly assume the existing calibration applies to every lab treadmill.

---

# 11. Internal Position Representation

Maintain position internally using an integer transition position.

For example:

```text
raw_transition_position: int64
```

Do not repeatedly accumulate floating-point distance.

Compute physical position as:

```text
raw_encoder_position_mm =
    raw_transition_position * mm_per_transition
```

Then:

```text
locomotion_position_mm =
    raw_encoder_position_mm * locomotion_sign
```

This avoids long-term floating-point accumulation error.

Also maintain an absolute transition accumulator if convenient:

```text
absolute_transition_total
```

This permits reporting total travelled distance separately from signed net displacement.

Recommended public distinction:

```text
position_mm
    signed displacement from current zero

distance_travelled_mm
    cumulative absolute movement from current zero
```

For compatibility, an optional `distance_mm` property may alias `position_mm`, but documentation should make its meaning explicit.

Expose diagnostic quantities if useful:

```text
transition_position
equivalent_encoder_cycles = transition_position / 4
mm_per_encoder_cycle
mm_per_transition
```

Behavior code should not depend on raw count values.

---

# 12. Zeroing

`zero()` must establish a new reported coordinate origin.

It must **not erase lifetime acquisition diagnostics**.

Implement zeroing using offsets.

Conceptually:

```text
zero_transition_offset = current_raw_transition_position
zero_absolute_offset   = current_absolute_transition_total
```

Then:

```text
position_mm =
    (raw_transition_position - zero_transition_offset)
    * mm_per_transition
    * locomotion_sign
```

and similarly for distance travelled.

Do not reset:

```text
total edge events
valid transition count
sequence-gap count
acquisition errors
max processing lag
health history
```

when `zero()` is called.

A zero command should be applied by the acquisition process at a well-defined state and acknowledged to the caller.

---

# 13. Speed

The low-level system should provide a minimally processed physical speed measurement without deciding task-specific filtering.

## Required outputs

Provide at least:

```text
last_edge_speed_mm_s
speed_mm_s
last_motion_timestamp
time_since_last_motion
```

## Edge-derived speed

For consecutive valid position-changing transitions:

```text
dt =
    current_kernel_timestamp
    - previous_valid_transition_kernel_timestamp
```

and:

```text
last_edge_speed_mm_s =
    signed_mm_per_transition / dt
```

Use **kernel event timestamps**, not Python callback/processing timestamps.

If:

```text
dt <= 0
```

treat this as a timing/integrity anomaly.

## Timeout-to-zero

For general compatibility, provide:

```text
speed_mm_s
```

which returns the most recent edge-derived speed while motion is recent and zero after a configurable inactivity timeout.

Suggested default for migration compatibility:

```text
speed_timeout_s = 0.050
```

because the previous implementation used 50 ms.

This timeout must remain configurable.

Keep:

```text
last_edge_speed_mm_s
```

available separately so the raw most-recent estimate is not destroyed when `speed_mm_s` times out to zero.

Do not add hidden smoothing or behavioral thresholds inside the acquisition layer.

If future tasks require:

- 20 ms velocity averages;
- 100 ms velocity averages;
- low-pass filtering;
- movement onset detection;
- threshold crossings;

those should be downstream calculations or explicitly separate utility functions.

---

# 14. Shared Live State

The acquisition process is the only writer of the canonical encoder state.

The behavior process and logger are readers.

A live state snapshot should contain approximately:

```text
state_version

position_mm
distance_travelled_mm

raw_transition_position
equivalent_encoder_cycles

last_edge_speed_mm_s
speed_mm_s

encoder_direction
locomotion_direction

last_edge_monotonic_ns
last_state_update_monotonic_ns

valid_transition_count
edge_event_count

sequence_gap_count
event_inconsistency_count

health_state
integrity_valid
```

It is acceptable for calculated convenience fields such as `time_since_last_motion` to be derived by the reader rather than stored.

---

# 15. Shared Memory / Synchronization Requirements

The main behavior process must never be able to hold a lock that prevents the acquisition process from consuming GPIO events.

Therefore avoid designs where:

```text
behavior acquires multiprocessing.Lock
behavior is descheduled while holding it
encoder process blocks waiting for same lock
```

Correctness of edge acquisition must not depend on behavior-process responsiveness.

Prefer a single-writer coherent-snapshot mechanism such as:

- shared memory plus version/sequence counter;
- seqlock-style publication;
- atomic replacement of a compact shared state;
- another equivalent non-backpressuring mechanism.

Exact implementation is left to Codex.

Required property:

> Readers may retry a snapshot, but the acquisition process must not wait indefinitely for a reader.

Snapshots must be internally coherent; torn combinations such as a new position with an old timestamp must not be returned as valid state.

---

# 16. Multiprocessing

Use a dedicated process for encoder acquisition.

Do not rely on an ordinary Python thread as the primary isolation mechanism.

Reasons/requirements:

- separate Python interpreter/GIL;
- behavior code cannot monopolize the acquisition interpreter;
- GPIO processing remains isolated from behavior implementation;
- acquisition can be independently monitored.

CPU affinity is optional.

Real-time scheduling is optional.

The initial implementation should not require:

- a real-time Linux kernel;
- root-only scheduler configuration;
- manual CPU pinning.

Correctness should first be obtained using:

- kernel event buffering;
- efficient event draining;
- multiprocessing isolation;
- minimal acquisition hot path.

Affinity/priority may later be exposed as optional performance tuning if stress tests demonstrate value.

---

# 17. Event Buffers

Use a reasonably generous kernel event buffer.

Make event buffer size configurable.

Suggested initial default:

```text
event_buffer_size = 8192
```

if supported by the installed libgpiod/kernel interface.

The exact default may be adjusted after determining the real encoder event rate.

When maximum expected transition frequency is known, ensure buffer size provides substantial scheduling-latency headroom.

Record configured buffer parameters in session metadata.

If the backend constrains/caps the requested size, record the effective behavior if discoverable.

Most importantly, event-buffer overflow/loss must become observable through sequence-gap diagnostics rather than silently corrupting position.

---

# 18. Sequence Numbers and Acquisition Integrity

Use GPIO event sequence numbers when available.

Track:

```text
global sequence number
per-line sequence number
```

A discontinuity should be recorded as a sequence gap.

For example:

```text
101
102
105
```

means events were not observed by the decoder between 102 and 105.

Track at minimum:

```text
global_sequence_gap_count
A_sequence_gap_count
B_sequence_gap_count
estimated_missing_event_count
```

Do not silently correct sequence gaps.

A sequence gap means exact encoder position can no longer be guaranteed.

Set:

```text
integrity_valid = False
```

and latch the integrity failure.

The program may resynchronize the current A/B logical state so later events can continue to be decoded for diagnostics, but it must not pretend that absolute position across the missing interval is known.

Do not automatically infer missing direction/counts from previous motion.

---

# 19. Event Consistency Checks

Because each kernel event explicitly identifies its line and edge type, maintain expected logical state for A and B.

Examples of inconsistencies:

```text
A rising reported while decoder already believes A is high
A falling reported while decoder already believes A is low
timestamp moves backward
event ordering violates sequence numbering
decoder state cannot be reconciled with requested resynchronization
```

Track such conditions separately from sequence gaps.

Do not lump all problems into a generic "missed callback" counter.

At minimum distinguish:

## Signal/quadrature-related diagnostics

```text
valid_transition_count
encoder_direction_reversal_count
event_state_inconsistency_count
debounce/rejected-event count if applicable
```

## Acquisition/software diagnostics

```text
global_sequence_gap_count
per_line_sequence_gap_count
estimated_missing_event_count
max_processing_lag
acquisition_process_restart_count
logger_error_count
```

This distinction is important because wiring/electrical problems and CPU/software backlog require different troubleshooting.

---

# 20. Processing Lag

Because GPIO events use a monotonic kernel timestamp, compare event timestamp to the acquisition process's current monotonic time when processing it.

Conceptually:

```text
processing_lag_ns =
    process_monotonic_ns - event_timestamp_ns
```

Track:

```text
latest_processing_lag
maximum_processing_lag
mean processing lag
useful percentiles if inexpensive
```

Do not update expensive online percentile structures inside the hottest per-edge path if that creates meaningful overhead.

It is acceptable to maintain:

- count;
- sum;
- max;
- histogram/binned statistics;

and calculate detailed summary metrics later.

Large processing lag alone does not necessarily mean events were lost because the kernel buffer can preserve them.

Therefore:

```text
large lag -> warning/degraded diagnostic
sequence gap -> actual integrity failure
```

These should remain conceptually distinct.

---

# 21. Health States

Use explicit subsystem health states.

Recommended states:

```text
STARTING
READY
DEGRADED
FAILED
STOPPED
```

Also maintain:

```text
integrity_valid: bool
```

because process health and trajectory integrity are related but not identical.

Examples:

## STARTING

- process created;
- GPIO being resolved/claimed;
- initial A/B synchronization occurring.

Behavior must not begin treadmill-dependent execution yet.

## READY

- GPIO acquired;
- decoder synchronized;
- process heartbeat active;
- no known integrity loss.

## DEGRADED

Examples:

- processing lag exceeds configured warning threshold;
- fixed-rate logger failed but live acquisition remains intact;
- nonfatal diagnostic issue.

A degraded state must be logged and visible.

## FAILED

Examples:

- acquisition process exited;
- GPIO line claim failed;
- heartbeat is stale;
- event sequence gap means position is no longer trustworthy;
- unrecoverable state inconsistency;
- backend error prevents further acquisition.

`FAILED` must never silently look like zero speed/stationary treadmill.

## STOPPED

Normal requested shutdown.

---

# 22. Failure Policy

Support configurable behavior when treadmill acquisition is required by a task:

```text
failure_policy:
    pause
    abort
    warn
```

Recommended default:

```text
pause
```

For passive treadmill logging, users may configure:

```text
warn
```

Silent failure is never an allowed mode.

The encoder library itself does not need to understand how a particular behavior program implements a pause.

Instead expose a clear integration mechanism such as:

- a latched shared failure event;
- a health-check method;
- a typed exception;
- a callback/hook;
- equivalent mechanism.

Behavior code declaring treadmill data as required must check/respond to this failure condition.

For example:

```text
decoder.require_healthy()
```

could raise a specific treadmill-integrity exception when health is `FAILED`.

Exact API naming is left to implementation.

---

# 23. Integrity Failure Should Latch

Once exact encoder position is known to have been compromised:

```text
integrity_valid = False
```

must remain latched.

Do not automatically restore integrity simply because later events look normal.

Normal `zero()` should not silently clear a prior acquisition failure.

Recovery should require an explicit acquisition restart or similarly explicit re-arm/resynchronization action.

This ensures users cannot accidentally hide a failure by zeroing the treadmill.

---

# 24. Acquisition Process Heartbeat

Absence of encoder movement cannot distinguish:

```text
animal stationary
```

from:

```text
encoder process dead
```

Therefore the acquisition process must update an independent heartbeat periodically even when no GPIO events occur.

Behavior/logger side should monitor:

```text
last_heartbeat_monotonic_ns
```

If heartbeat age exceeds a configured threshold:

```text
health = FAILED
```

and the configured failure policy should be triggered.

---

# 25. Startup Handshake

`start()` should not merely spawn a process and immediately return success.

Required sequence:

```text
behavior requests start
        |
        v
acquisition process launches
        |
        v
GPIO backend/version validated
        |
        v
GPIO chip/lines resolved
        |
        v
A/B lines claimed
        |
        v
initial state synchronized
        |
        v
shared state initialized
        |
        v
heartbeat running
        |
        v
health = READY
        |
        v
start() reports success
```

Use a configurable startup timeout.

If startup fails:

- raise an actionable error;
- include the underlying cause;
- release any acquired resources;
- do not start the behavioral experiment.

---

# 26. Graceful Shutdown

Normal shutdown sequence:

```text
experiment requests stop
        |
        v
acquisition receives stop command
        |
        v
finish/drain appropriate pending work
        |
        v
publish final state
        |
        v
diagnostics finalized
        |
        v
logger flushes buffered data
        |
        v
GPIO lines released
        |
        v
health = STOPPED
        |
        v
process exits
```

`close()` should be idempotent.

Repeated `stop()`/`close()` calls should not corrupt state or raise unnecessary errors.

Do not rely solely on daemon-process termination or interpreter shutdown for resource cleanup.

---

# 27. Control Commands

The behavior side may need to send infrequent control commands such as:

```text
zero
stop
request diagnostic status
```

A lightweight pipe/queue/control mechanism is acceptable.

Control communication must not be used for individual encoder edges.

The acquisition process must prioritize draining edge events over low-priority control work.

A `zero()` command should receive an acknowledgement so callers know it was applied.

---

# 28. Continuous Fixed-Rate Treadmill Record

Enable continuous treadmill-state recording by default.

Suggested default:

```text
enabled = True
rate_hz = 200
```

Make the rate configurable.

200 Hz corresponds to one state sample every 5 ms and should remain inexpensive compared with normal video/neural-data workloads.

This is **not** the GPIO acquisition rate.

Encoder edge events continue to be processed at their full native rate.

The logger merely samples the latest decoded shared state at 200 Hz.

---

# 29. Logger Process

Disk logging must not run in the encoder acquisition hot path.

Prefer:

```text
separate low-priority logging process
```

that reads shared state.

The logger must never back-pressure edge acquisition.

If communication is needed between acquisition and logger:

- use bounded/nonblocking mechanisms;
- never allow a full logging queue to stall GPIO event consumption.

Buffered/chunked disk writes are required.

Do not issue one physical disk write for every 5 ms sample.

The exact file format is left to Codex, but prefer:

- simple;
- appendable/incremental;
- robust to abnormal termination;
- reasonably compact;
- easy to load from Python;
- minimal dependency burden.

Avoid formats requiring the entire experiment to remain in RAM until shutdown.

---

# 30. Fixed-Rate Logger Timing

Use monotonic deadline scheduling.

Do not implement the entire timing loop as repeated:

```text
sleep(0.005)
```

with accumulated drift.

Conceptually:

```text
next_sample_time += period
sleep/wait until next_sample_time
sample latest coherent state
```

If the logger is late:

- record the actual sample timestamp;
- increment a logger lateness/missed-sample diagnostic;
- do not fabricate timestamps;
- do not generate a burst of duplicate "catch-up" samples simply to preserve row count.

---

# 31. Continuous Record Fields

At minimum, each normal fixed-rate record should include:

```text
sample_monotonic_ns
position_mm
distance_travelled_mm
speed_mm_s
last_edge_monotonic_ns
health/integrity status
state_version or equivalent
```

Useful optional fields:

```text
last_edge_speed_mm_s
locomotion_direction
raw_transition_position
```

Avoid repeating large diagnostic structures every 5 ms.

Detailed diagnostics belong in metadata/event/summary logs.

---

# 32. Timebase and Alignment

Use monotonic time as the primary internal clock because GPIO edge timestamps use the monotonic event clock.

At experiment start, record an association between:

```text
monotonic_ns
system realtime / UTC time
```

so treadmill data can be aligned with behavior/external records.

Consider recording additional timebase anchors periodically or at least at session end.

Do not use wall-clock timestamps for edge interval calculations because wall time may be adjusted.

Core calculations must use monotonic time.

---

# 33. Diagnostic Event Log

Maintain a lower-rate/event-driven diagnostic log separate from the 200 Hz treadmill file.

Record important events such as:

```text
startup
GPIO mapping
READY
zero commands
DEGRADED state
FAILED state
sequence gaps
state inconsistencies
logger failures
heartbeat failures
shutdown
```

Each diagnostic entry should include a monotonic timestamp and enough context to investigate the event.

---

# 34. Rolling Raw-Event Ring Buffer

Maintain an in-memory ring buffer of recent raw/decoded GPIO events.

Suggested initial size:

```text
4096-10000 events
```

Make it configurable.

Each retained event should contain enough information to reconstruct what occurred, approximately:

```text
kernel timestamp
processing timestamp
line A/B
rising/falling
global sequence number
line sequence number
AB state before
AB state after
decoded transition delta
processing lag
diagnostic flags
```

Do not continuously write every raw GPIO edge to disk during normal experiments.

When an integrity error occurs, preserve/dump the recent ring-buffer contents for debugging.

Dumping must not block the acquisition hot path.

Possible approaches:

- transfer a copy to the logging/diagnostic process;
- preserve it until acquisition pauses;
- write after failure has latched.

Exact implementation is flexible.

---

# 35. Optional Full Raw-Edge Debug Mode

Provide an optional development mode that logs every raw GPIO event.

Default:

```text
raw_edge_logging = False
```

This mode is useful for:

- hardware validation;
- stress testing;
- diagnosing wiring/signal problems.

It is not required for ordinary behavioral sessions.

---

# 36. End-of-Session Diagnostic Summary

Generate a compact acquisition integrity summary containing at least:

```text
session runtime

total GPIO edge events
valid quadrature transitions
positive transitions
negative transitions
direction reversals

global sequence gaps
A sequence gaps
B sequence gaps
estimated missing events
state inconsistencies

maximum observed transition rate
mean processing lag
maximum processing lag
useful processing-lag percentiles

heartbeat failures
acquisition process failures
logger failures
logger missed/late samples

final health state
integrity_valid

resolved GPIO configuration
calibration values
software/backend versions
```

This summary should make it easy to determine whether a treadmill record was trustworthy without manually inspecting logs.

---

# 37. Configuration

Use an explicit configuration object/file rather than burying all experimental values as module constants.

Conceptually support:

```text
a_bcm_pin
b_bcm_pin

gpio_bias
debounce_period

mm_per_encoder_cycle
locomotion_sign

speed_timeout_s

event_buffer_size

continuous_log_enabled
continuous_log_rate_hz

raw_edge_logging_enabled
diagnostic_ring_buffer_size

heartbeat_interval
heartbeat_failure_timeout

processing_lag_warning_threshold

failure_policy

continuous_logger_required
```

Configuration validation should occur before acquisition starts.

Invalid values must cause clear startup errors.

Examples:

```text
mm_per_encoder_cycle <= 0
locomotion_sign not in {-1,+1}
same GPIO configured for A and B
negative timeout
invalid logging rate
```

---

# 38. Behavior-Facing API

Keep routine use simple.

The API should conceptually provide:

```python
decoder = TreadmillDecoder(config)

decoder.start()

state = decoder.snapshot()

decoder.zero()

decoder.require_healthy()

decoder.stop()
decoder.close()
```

Exact names/classes can differ if there is a strong implementation reason.

`snapshot()` must be cheap.

Normal behavior code should not need to know:

- gpiochip identifiers;
- libgpiod event objects;
- multiprocessing implementation;
- quadrature transition tables;
- logger internals.

A snapshot should provide directly useful physical quantities.

---

# 39. Suggested State Object

A dataclass or similarly typed structure is preferred.

Conceptually:

```python
TreadmillState(
    position_mm,
    distance_travelled_mm,

    speed_mm_s,
    last_edge_speed_mm_s,

    encoder_direction,
    locomotion_direction,

    last_edge_monotonic_ns,
    last_state_update_monotonic_ns,

    raw_transition_position,
    equivalent_encoder_cycles,

    valid_transition_count,
    edge_event_count,

    sequence_gap_count,
    event_inconsistency_count,

    health,
    integrity_valid,
    state_version,
)
```

Fields may be adjusted, but preserve the distinction between:

- physical values;
- timestamps;
- diagnostics;
- health.

---

# 40. Separation for Testability

GPIO acquisition and quadrature decoding must be separable.

The quadrature decoder should be testable using synthetic events without:

- Raspberry Pi hardware;
- `/dev/gpiochip`;
- multiprocessing;
- actual wall-clock timing.

Conceptually:

```text
EdgeSource
    |
    v
generic edge-event representation
    |
    v
QuadratureDecoder
    |
    v
Treadmill state
```

A synthetic `EdgeSource` or equivalent injection mechanism should allow exactly the same decoder logic to be exercised in automated tests.

Do not bury quadrature state changes directly inside libgpiod callback/glue code.

---

# 41. Synthetic Edge Representation

Synthetic tests should be able to construct events containing:

```text
timestamp_ns
channel
edge_type
global_sequence_number
line_sequence_number
```

The production backend can adapt libgpiod events into this internal representation or otherwise expose an equivalent testable interface.

---

# 42. Unit Tests: Quadrature Decoder

Exhaustively test all normal direction/state cases.

Include:

### Forward sequence

```text
00 -> 01 -> 11 -> 10 -> 00
```

### Reverse sequence

```text
00 -> 10 -> 11 -> 01 -> 00
```

Test:

- one cycle;
- many cycles;
- partial cycles;
- starting from each of the four possible AB states;
- immediate direction reversal;
- repeated direction reversals;
- long forward motion;
- long reverse motion;
- randomized but valid motion traces.

Verify exact:

```text
transition_position
position_mm
distance_travelled_mm
direction
```

---

# 43. Unit Tests: Event Failures

Synthetic tests must deliberately inject:

```text
global sequence gaps
per-line sequence gaps
duplicate/inconsistent rising edges
duplicate/inconsistent falling edges
timestamp regression
zero/nonpositive dt
out-of-order events
malformed channel IDs
```

Verify that:

- diagnostics increment correctly;
- integrity is invalidated when appropriate;
- failure state latches;
- position is not silently "corrected";
- the decoder can continue diagnostically after resynchronization if designed to do so.

---

# 44. Unit Tests: Calibration and Sign

Verify:

```text
mm_per_transition == mm_per_encoder_cycle / 4
```

Verify both:

```text
locomotion_sign = +1
locomotion_sign = -1
```

Verify animal-forward convention.

Verify that swapping locomotion sign changes signed position/speed but not:

```text
absolute transition count
distance_travelled_mm
event diagnostics
```

---

# 45. Unit Tests: Speed

Generate synthetic transitions at known timing.

Test multiple known physical speeds.

Example test values may include:

```text
10 mm/s
50 mm/s
100 mm/s
500 mm/s
```

provided they are compatible with the configured calibration.

Verify:

- speed magnitude;
- speed sign;
- direction changes;
- first edge behavior when no previous dt exists;
- timeout-to-zero;
- `last_edge_speed_mm_s` remains available after timeout;
- no speed calculation uses Python processing delay.

Tolerance should be near numerical precision for ideal synthetic timestamps.

---

# 46. Unit Tests: Zeroing

Test:

- zero while stationary;
- zero during continuous motion;
- zero after direction reversal;
- multiple zeros;
- diagnostics preserved across zero;
- lifetime raw transition position preserved;
- reported position resets cleanly.

---

# 47. Unit Tests: Shared State

Verify that concurrent readers never observe a torn state.

Stress-test publication while repeatedly reading snapshots.

Properties:

```text
position
timestamp
transition count
state version
```

must correspond to one coherent publication.

Readers may retry.

Writer/acquisition must not block indefinitely on readers.

---

# 48. Unit Tests: Health and Heartbeat

Test:

- normal heartbeat;
- acquisition process intentionally killed;
- stale heartbeat;
- GPIO initialization failure;
- sequence-gap integrity failure;
- logger failure;
- graceful stop.

Verify transitions between:

```text
STARTING
READY
DEGRADED
FAILED
STOPPED
```

Verify failure policy behavior.

---

# 49. Unit Tests: Continuous Logger

Using simulated shared state, verify:

- nominal 200 Hz scheduling;
- timestamp monotonicity;
- buffered writes;
- graceful flush;
- abnormal shutdown resilience where practical;
- late logger cycles;
- missed-sample accounting;
- no fake catch-up samples;
- logger failure does not block acquisition.

---

# 50. High-Volume Synthetic Test

Generate millions of valid quadrature transitions.

Use:

- variable speeds;
- direction changes;
- pauses;
- bursts near maximum expected rates.

At the end require exact equality between generated and decoded transition displacement.

This should be runnable without Raspberry Pi GPIO hardware.

Memory use should remain bounded.

No event history other than deliberately bounded diagnostic buffers should grow indefinitely.

---

# 51. Multiprocessing Stress Test

Implement a software stress test exercising the actual process architecture.

Run:

```text
synthetic edge source
    ->
real acquisition/decoder process
    ->
real shared state
    ->
real logger
```

while the simulated behavior process intentionally performs workloads such as:

```text
CPU-heavy Python loops
disk I/O
console/logging output
network-like I/O if convenient
periodic long sleeps
GUI-like update workload if relevant
```

Test the design property:

> Behavior timing may become poor, but encoder acquisition remains exact.

Verify:

```text
generated transition displacement
==
decoded transition displacement
```

and:

```text
sequence gaps == 0
integrity_valid == True
```

under representative worst-case behavioral load.

---

# 52. Pathological Load Test

Optionally test severe system saturation such as:

- CPU saturation across most/all cores;
- heavy disk traffic;
- competing processes.

This is useful for finding system limits.

Do not necessarily make pathological all-core saturation a production acceptance criterion unless it resembles realistic behavioral workloads.

Record where:

- processing lag rises;
- buffers begin filling;
- sequence loss first appears.

---

# 53. Hardware Information Required Before Final Validation

When lab access is available, determine and document:

```text
encoder manufacturer/model if identifiable
encoder type
cycles per revolution if available

roller/wheel circumference
or directly calibrated mm per encoder cycle

maximum plausible treadmill speed

expected maximum encoder cycles/sec
expected maximum transitions/sec

GPIO output voltage/electrical interface

A/B BCM pins

locomotion_sign

pull-up/debounce requirements
```

If the encoder specifications cannot be found, empirically calibrate them.

---

# 54. Expected Edge Rate Calculation

Once physical calibration is known:

```text
mm_per_transition =
    mm_per_encoder_cycle / 4
```

Then:

```text
expected_transition_rate_hz =
    expected_speed_mm_s / mm_per_transition
```

Calculate a maximum physically plausible transition rate.

Record it in configuration/metadata.

Use this value to establish hardware stress-test targets.

---

# 55. Hardware Validation Source

For final validation, use a known-good external quadrature source where possible.

Examples:

- microcontroller test firmware;
- hardware quadrature generator;
- other deterministic external signal generator.

The generator should know exactly how many transitions it emits.

A Python process on the same Pi generating GPIO edges is acceptable for convenient development tests but should not be the sole final validation source because its timing is itself Linux-scheduled.

---

# 56. Hardware Rate Sweep

Run the physical GPIO decoder while generating known quadrature input at approximately:

```text
0.25 x maximum expected rate
0.5  x maximum expected rate
1.0  x maximum expected rate
2.0  x maximum expected rate
```

Optionally continue:

```text
4.0 x
```

to characterize additional headroom.

Run these tests while the Pi simultaneously executes representative worst-case behavior workloads.

---

# 57. Core Hardware Acceptance Criterion

At **at least 2x the maximum physically expected encoder transition rate** under representative full behavioral load:

```text
generated net transition position
==
decoded net transition position
```

and:

```text
global sequence gaps == 0
per-line unexplained sequence gaps == 0
event inconsistencies == 0
integrity_valid == True
```

Target **zero lost transitions**, not merely a low percentage error.

If this cannot be achieved, do not silently relax the correctness target.

Investigate:

- buffer sizing;
- event-draining implementation;
- accidental blocking work;
- process priority/affinity;
- GPIO signal quality;
- electrical problems.

Only after the Pi-only design has been quantitatively characterized should a microcontroller fallback be reconsidered.

---

# 58. Direction-Reversal Hardware Test

Physical validation must include:

- continuous one-direction motion;
- reverse direction;
- repeated rapid direction changes;
- very slow motion;
- starts/stops;
- partial rotations.

Verify both net position and locomotion sign.

---

# 59. Long-Duration Soak Test

Run the acquisition system with representative behavior workload for at least:

```text
max(
    2 hours,
    1.5 x longest expected behavioral-session duration
)
```

using repeated/continuous encoder activity.

At completion require:

```text
generated/known position == decoded position
sequence gaps == 0
unexplained event inconsistencies == 0
integrity_valid == True
acquisition process alive
logger alive
memory use stable
no growing event backlog
no unbounded data structures
```

Inspect processing-lag statistics.

---

# 60. Full Behavioral-System Validation

The final test must run the actual intended behavioral stack, not merely a standalone treadmill script.

Include representative concurrent operations such as whatever applies to the lab system:

- behavioral control;
- user input;
- stimulus control;
- display/GUI;
- network activity;
- logging;
- camera/video coordination;
- experiment-state transitions.

This test is required because the failure being addressed reportedly appeared when the rotary decoder was incorporated into the full behavior program.

---

# 61. Resource Monitoring During Validation

Benchmark and report approximately:

```text
encoder acquisition CPU %
logger CPU %
behavior CPU %
memory use
disk-write rate
maximum processing lag
typical processing lag
maximum observed encoder event rate
```

Do not optimize prematurely, but verify that the implementation has comfortable resource headroom on:

- Raspberry Pi 5 target systems;
- Raspberry Pi 4B where practical.

---

# 62. Optional Performance Tuning

If representative stress tests reveal insufficient scheduling headroom, investigate in this order:

1. ensure no blocking/nonessential work occurs in acquisition;
2. read edge events efficiently in batches;
3. increase/configure kernel event buffering;
4. optimize shared-state publication;
5. reduce acquisition object allocation;
6. increase acquisition process scheduling priority modestly;
7. optionally set CPU affinity;
8. characterize real-time scheduler options only if necessary.

Do not add complexity such as real-time scheduling before demonstrating that it is required.

---

# 63. Logging Storage Budget

Measure actual file size during testing.

At 200 Hz, a compact numeric record should be small relative to typical experimental video/ephys data, but confirm rather than assume.

Report:

```text
MB/hour
```

for the chosen format.

If storage is unexpectedly large:

- reduce redundant fields;
- use compact numeric types where safe;
- use chunked/compressed storage if appropriate.

Do not lower temporal resolution solely to compensate for inefficient serialization before fixing the serialization.

---

# 64. Metadata

Each treadmill recording should include or reference metadata sufficient to reproduce interpretation:

```text
session identifier if available
software version / git commit if available
Pi model
OS/kernel
GPIO backend version

A/B pins
resolved GPIO lines
bias/debounce settings

mm_per_encoder_cycle
mm_per_transition
locomotion_sign

speed timeout

continuous log rate
event buffer size

timebase anchor(s)

start health
end health
integrity_valid
```

---

# 65. Error Messages

Errors should be actionable.

Bad:

```text
GPIO initialization failed
```

Better:

```text
Unable to resolve BCM17 and BCM27 to the user-facing GPIO controller.
Detected gpiochips:
...
Check GPIO configuration and libgpiod installation.
```

Bad:

```text
Encoder error
```

Better:

```text
Treadmill encoder integrity lost:
global GPIO event sequence jumped from 143829 to 143832.
At least 2 edge events were not received.
Absolute treadmill position after this point is not guaranteed.
```

The goal is to make troubleshooting possible for a lab member who did not write the module.

---

# 66. Dependency/Environment Handling

Target a current libgpiod v2-compatible Python API.

At startup or installation, verify required functionality exists.

Specifically require equivalents of:

```text
both-edge input requests
monotonic event timestamps
edge type
line identity
global sequence number
per-line sequence number
configurable event buffering
```

If the installed binding is too old or incompatible, fail clearly.

Do not silently downgrade to an architecture that loses kernel timestamps/sequence diagnostics.

Provide installation/environment notes appropriate for the Raspberry Pi OS version used by the lab.

Keep dependencies minimal.

---

# 67. Migration From Existing Decoder

Preserve conceptual ease of use but do not preserve known architectural weaknesses.

Old concepts:

```text
counts
distance_mm
run_speed_mms
direction
snapshot()
zero()
start()
stop()
```

New system should retain simple equivalents for:

```text
position/distance
speed
direction
snapshot
zero
start
stop
```

Raw counts are no longer the primary user-facing measurement.

Document that:

- old decoder was x1;
- new decoder is x4;
- raw count numbers therefore should not be expected to match;
- physical calibration is converted appropriately;
- physical position/speed are the meaningful comparison.

If the same hardware calibration is confirmed, migrate:

```text
old 0.41095 mm per A-rising count
```

to:

```text
0.41095 mm per encoder cycle
0.1027375 mm per x4 transition
```

---

# 68. Do Not Preserve the Existing Direction Naming

Do not carry over:

```text
FW = -1
BW = 1
```

because those names mix encoder rotation and animal locomotion.

Use explicit:

```text
encoder_direction
locomotion_direction
locomotion_sign
```

instead.

---

# 69. What Must Never Happen

The implementation must never:

1. infer an old edge's quadrature state by simply reading GPIO much later without accounting for queued events;
2. use Python processing time instead of kernel event time for edge intervals;
3. send every edge through the main behavior process;
4. require behavior to service a queue fast enough to avoid edge loss;
5. allow disk I/O to stall the acquisition process;
6. allow a behavior-held lock to stall edge acquisition indefinitely;
7. silently reset integrity after an event loss;
8. silently estimate/correct missing transitions;
9. report an acquisition-process crash as zero treadmill speed;
10. silently fall back to the old `RPi.GPIO` callback strategy;
11. hard-code gpiochip numbering without runtime verification;
12. silently enable debounce;
13. treat raw x4 transitions as if they were equivalent to old x1 count values.

---

# 70. Deliverables

Codex implementation should produce:

## Core implementation

Robust treadmill/encoder module containing:

- GPIO acquisition backend;
- quadrature decoder;
- multiprocessing acquisition;
- shared state;
- health monitoring;
- zero/start/stop lifecycle;
- speed/position calculations.

## Continuous logger

- fixed-rate logger;
- configurable rate;
- buffered incremental storage;
- metadata;
- diagnostic summary.

## Diagnostic system

- health event log;
- sequence-gap detection;
- processing-lag metrics;
- rolling raw-event buffer;
- optional raw-edge debug logging.

## Automated tests

- pure quadrature unit tests;
- speed tests;
- failure injection tests;
- zero tests;
- shared-state concurrency tests;
- heartbeat tests;
- logger tests;
- high-volume synthetic tests;
- multiprocessing stress tests.

## Hardware validation utility

A small program/mode that:

- starts acquisition;
- prints useful live diagnostics;
- displays raw encoder direction;
- helps determine `locomotion_sign`;
- shows transition rate;
- shows sequence gaps/inconsistencies;
- summarizes integrity at shutdown.

## Stress-test utility

Tool/script for running acquisition while generating substantial CPU/I/O load and reporting whether any acquisition errors occur.

## Documentation

Include:

- setup;
- dependency requirements;
- GPIO configuration;
- calibration;
- sign calibration;
- logging;
- health/failure policy;
- how to run unit tests;
- how to run hardware validation;
- how to interpret diagnostic summaries;
- migration notes from the current decoder.

---

# 71. Suggested Implementation Order

Implement in this order.

## Phase 1 — Pure decoder

Build:

- generic edge representation;
- quadrature state machine;
- calibration/sign mapping;
- position/distance;
- edge-derived speed;
- sequence/integrity tracking.

Complete pure unit tests before GPIO integration.

## Phase 2 — GPIO backend

Add:

- libgpiod integration;
- dynamic GPIO-chip resolution;
- both-edge capture;
- initial state synchronization;
- batch edge reading;
- event sequence checks.

Test standalone on Pi.

## Phase 3 — Multiprocessing

Move acquisition to dedicated process.

Add:

- startup handshake;
- heartbeat;
- coherent shared state;
- zero/control channel;
- graceful shutdown.

Run concurrency tests.

## Phase 4 — Continuous logger

Add separate logging process.

Implement:

- 200 Hz default schedule;
- buffered incremental writes;
- metadata;
- timebase anchors;
- logger diagnostics.

## Phase 5 — Health/diagnostics

Add:

- explicit health states;
- latched integrity loss;
- failure policy hooks;
- diagnostic event log;
- rolling raw-event ring buffer;
- end-session summary.

## Phase 6 — Synthetic stress validation

Run:

- millions of synthetic events;
- multiprocessing load;
- logger load;
- process-failure injection.

## Phase 7 — Hardware calibration/validation

When hardware is available:

- identify encoder parameters;
- verify mm/cycle;
- determine locomotion sign;
- determine max plausible event rate;
- run external quadrature rate sweep;
- run full-system soak test.

Do not declare production-ready before Phase 7 passes.

---

# 72. Production Acceptance Criteria

The system is ready for behavioral experiments only when all of the following are true:

### Functional

- Both A and B channels decode correctly.
- Both rising and falling edges are used.
- Forward/backward animal locomotion sign is correct.
- Physical position calibration is verified.
- Speed calculations use kernel timestamps.
- Zeroing behaves correctly.

### Isolation

- Behavior workload cannot directly block acquisition.
- Logger workload cannot directly block acquisition.
- Acquisition runs in its own process.
- Shared-state reads are coherent.

### Integrity

- Event sequence gaps are detected.
- State inconsistencies are detected.
- Integrity loss latches.
- Acquisition-process death is distinguishable from stationary treadmill.
- No silent failure path exists.

### Logging

- Continuous record works at default 200 Hz.
- File is incrementally written.
- Storage rate is measured and acceptable.
- Logger timing failures are visible.
- Diagnostic summary is produced.

### Synthetic validation

- Millions of generated valid transitions decode exactly.
- Failure injection produces expected health/integrity states.
- CPU/I/O stress does not corrupt synthetic acquisition.

### Hardware validation

At >=2x maximum expected physical encoder transition rate while representative behavior workload runs:

```text
zero lost transitions
zero unexplained sequence gaps
zero unexplained state inconsistencies
integrity_valid == True
```

### Soak test

Long-duration full-system run completes with:

```text
no position drift
no event loss
no process failure
no unbounded memory growth
no growing backlog
stable continuous logging
```

---

# 73. Final Design Principle

The original system asked Python to react quickly enough to a physical GPIO edge that the encoder state would still be valid when Python examined it.

The new system should instead treat the kernel-captured edge stream as the historical record of what physically occurred.

Python may process that record somewhat later without changing the event's timestamp or ordering.

Multiprocessing then isolates interpretation from the behavioral program, and the fixed-rate shared-state/logging layers isolate downstream consumers from raw edge rate.

The intended separation is:

```text
physical edge capture
        !=
quadrature interpretation
        !=
behavioral use
        !=
continuous data logging
```

Each layer should be independently testable and observable.

That separation, together with explicit event-loss diagnostics and quantitative stress testing, is the central requirement of this rewrite.