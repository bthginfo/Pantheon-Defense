//! Local prediction of the server simulation.
//!
//! The server stays authoritative and sends snapshots a few times per second.
//! Between snapshots the browser advances the same deterministic simulation at
//! 20 ticks per second and applies the player's own commands immediately.
//! Commands that the server has not confirmed yet are replayed on top of every
//! new snapshot, so the board never waits for a network round trip.

use pantheon_simulation::{self as sim, Action, Game, Phase};
use std::cell::RefCell;
use wasm_bindgen::prelude::*;

const TICKS_PER_SECOND: f64 = 20.;
/// Longest stretch the browser simulates on its own before it waits for the server.
const MAX_CATCH_UP: u64 = 240;
/// Larger clock differences jump directly to the server time.
const SNAP_TICKS: f64 = 30.;

struct Pending {
    nonce: String,
    tick: u64,
    player: usize,
    action: String,
}

#[derive(Default)]
struct Predictor {
    room: String,
    authority: Option<Game>,
    local: Option<Game>,
    clock: f64,
    stepped_at: f64,
    pending: Vec<Pending>,
    revision: u64,
    rendered: u64,
}

thread_local! {
    static PREDICTOR: RefCell<Predictor> = RefCell::new(Predictor::default());
}

fn now_ms() -> f64 {
    js_sys::Date::now()
}

fn ticking(game: &Game) -> bool {
    game.phase == Phase::Combat || (game.phase == Phase::Prep && game.phase_until > 0)
}

fn catch_up(game: &mut Game, target: u64) {
    if ticking(game) && target > game.tick {
        game.advance((target - game.tick).min(MAX_CATCH_UP) as u32);
    }
}

impl Predictor {
    fn step(&mut self, now: f64) {
        let elapsed = ((now - self.stepped_at) / 1000.).clamp(0., 0.5);
        self.stepped_at = now;
        let Some(local) = self.local.as_mut() else {
            return;
        };
        if !ticking(local) {
            self.clock = local.tick as f64;
            return;
        }
        self.clock += elapsed * TICKS_PER_SECOND;
        let target = self.clock.floor() as u64;
        if target > local.tick {
            let before = local.tick;
            catch_up(local, target);
            if local.tick != before {
                self.revision += 1;
            }
        }
        // A paused or finished game must not build up time it would replay later.
        if (local.tick as f64) + 1. < self.clock {
            self.clock = local.tick as f64 + self.clock.fract();
        }
    }

    fn rebuild(&mut self) {
        let Some(authority) = &self.authority else {
            return;
        };
        let mut game = authority.clone();
        self.pending.sort_by_key(|pending| pending.tick);
        for pending in &self.pending {
            if pending.tick > game.tick {
                catch_up(&mut game, pending.tick);
            }
            if let Ok(action) = serde_json::from_str::<Action>(&pending.action) {
                let mut trial = game.clone();
                if trial.apply(pending.player, action).is_ok() {
                    game = trial;
                }
            }
        }
        catch_up(&mut game, self.clock.floor() as u64);
        self.local = Some(game);
        self.revision += 1;
    }

    fn load(&mut self, room: &str, game: Game, acks: &[String]) {
        let now = now_ms();
        if self.room != room || self.local.is_none() {
            self.room = room.into();
            self.pending.clear();
            self.clock = game.tick as f64;
            self.stepped_at = now;
        } else {
            self.step(now);
        }
        self.pending.retain(|pending| !acks.contains(&pending.nonce));
        if ticking(&game) {
            // Snapshots leave the server about one tick before they arrive here.
            let server = game.tick as f64 + 1.;
            let error = server - self.clock;
            if error.abs() > SNAP_TICKS {
                self.clock = server;
            } else {
                self.clock += error * if error > 0. { 0.6 } else { 0.25 };
            }
        } else {
            self.clock = game.tick as f64;
        }
        self.authority = Some(game);
        self.rebuild();
    }
}

/// Feeds a server snapshot. `acks` lists the command nonces the server has applied.
#[wasm_bindgen]
pub fn predict_load(room: &str, state: &str, acks: &str) -> bool {
    let Ok(game) = serde_json::from_str::<Game>(state) else {
        return false;
    };
    let acks: Vec<String> = serde_json::from_str(acks).unwrap_or_default();
    PREDICTOR.with(|cell| cell.borrow_mut().load(room, game, &acks));
    crate::show_board();
    true
}

/// Applies a command to the local game right away and returns its tick.
#[wasm_bindgen]
pub fn predict_apply(nonce: &str, player: usize, action: &str) -> Result<f64, JsError> {
    PREDICTOR.with(|cell| {
        let mut predictor = cell.borrow_mut();
        predictor.step(now_ms());
        let parsed: Action = serde_json::from_str(action)
            .map_err(|_| JsError::new("Diese Aktion konnte nicht gelesen werden."))?;
        let local = predictor
            .local
            .as_ref()
            .ok_or_else(|| JsError::new("Die Partie lädt noch."))?;
        let mut trial = local.clone();
        trial.apply(player, parsed).map_err(JsError::new)?;
        let tick = trial.tick;
        predictor.local = Some(trial);
        predictor.pending.push(Pending {
            nonce: nonce.into(),
            tick,
            player,
            action: action.into(),
        });
        predictor.revision += 1;
        Ok(tick as f64)
    })
}

/// Forgets a command the server rejected and rebuilds the local game without it.
#[wasm_bindgen]
pub fn predict_drop(nonce: &str) {
    PREDICTOR.with(|cell| {
        let mut predictor = cell.borrow_mut();
        predictor.pending.retain(|pending| pending.nonce != nonce);
        predictor.rebuild();
    });
}

/// Advances to the current time and returns the revision of the local game.
#[wasm_bindgen]
pub fn predict_revision() -> f64 {
    PREDICTOR.with(|cell| {
        let mut predictor = cell.borrow_mut();
        predictor.step(now_ms());
        predictor.revision as f64
    })
}

/// The predicted game as JSON, including the hero ritual reports.
#[wasm_bindgen]
pub fn predict_state() -> Option<String> {
    PREDICTOR.with(|cell| {
        let mut predictor = cell.borrow_mut();
        predictor.step(now_ms());
        predictor
            .local
            .as_ref()
            .and_then(|game| sim::snapshot_json(game).ok())
    })
}

pub(crate) fn reset() {
    PREDICTOR.with(|cell| *cell.borrow_mut() = Predictor::default());
}

/// Hands the renderer a fresh copy whenever the local game changed.
pub(crate) fn frame() -> Option<(String, Game)> {
    PREDICTOR.with(|cell| {
        let mut predictor = cell.borrow_mut();
        predictor.step(now_ms());
        if predictor.revision == predictor.rendered {
            return None;
        }
        predictor.rendered = predictor.revision;
        let room = predictor.room.clone();
        predictor.local.clone().map(|game| (room, game))
    })
}
