use serde::{Deserialize, Serialize};
use std::sync::OnceLock;

pub const TICK_MS: u64 = 50;
pub const DT: f32 = TICK_MS as f32 / 1000.0;
pub const RECRUIT_COST: i32 = 65;
pub const MAX_RANK: u8 = 4;
pub const MAX_TIER: u8 = 3;
pub const STORY_WAVES: u8 = 12;
pub type Point = [f32; 2];

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Catalog {
    pub themes: Vec<Theme>,
    pub actors: Vec<Actor>,
    pub enemies: Vec<EnemyKind>,
    pub challenges: Vec<Challenge>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Theme {
    pub id: String,
    pub name: String,
    pub map: String,
    pub caption: String,
    pub accent: String,
    pub unlock: u8,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Actor {
    pub id: String,
    pub theme: String,
    pub kind: String,
    pub name: String,
    pub role: String,
    pub note: String,
    pub attack: String,
    pub skill: Option<String>,
    pub cost: i32,
    pub unlock: u8,
    pub damage: f32,
    pub range: f32,
    pub period: u64,
    pub effect: f32,
    pub color: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct EnemyKind {
    pub id: String,
    pub name: String,
    pub hp: f32,
    pub speed: f32,
    pub armor: f32,
    pub leak: i32,
    pub color: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Challenge {
    pub id: String,
    pub name: String,
    pub detail: String,
    pub unlock: u8,
    pub waves: u8,
    pub reward: f32,
}

static CATALOG: OnceLock<Catalog> = OnceLock::new();

pub fn catalog() -> &'static Catalog {
    CATALOG.get_or_init(|| {
        serde_json::from_str(include_str!("../../../public/assets/catalog.json"))
            .expect("the bundled catalog must be valid")
    })
}

pub fn actor(id: &str) -> Option<&'static Actor> {
    catalog().actors.iter().find(|a| a.id == id)
}

pub fn enemy_kind(id: &str) -> &'static EnemyKind {
    catalog()
        .enemies
        .iter()
        .find(|a| a.id == id)
        .unwrap_or(&catalog().enemies[0])
}

const LEFT_PATH: [Point; 6] = [
    [-12.3, -6.0],
    [-7.1, -6.0],
    [-7.1, 3.45],
    [-4.8, 5.2],
    [-2.1, 5.2],
    [0., 7.25],
];

pub fn path(theme: &str, lane: usize) -> [Point; 6] {
    let mut points = LEFT_PATH;
    match theme {
        "rome" => {
            points[1] = [-8.3, -5.8];
            points[2] = [-8.3, 3.4];
        }
        "japan" => {
            points[1] = [-6.85, -4.8];
            points[2] = [-7.65, 3.1];
            points[3] = [-5., 5.15];
        }
        _ => {}
    }
    if lane > 0 {
        for point in &mut points {
            point[0] *= -1.;
        }
    }
    points
}

pub fn distance(a: Point, b: Point) -> f32 {
    (a[0] - b[0]).hypot(a[1] - b[1])
}

pub fn path_len(theme: &str, lane: usize) -> f32 {
    path(theme, lane)
        .windows(2)
        .map(|p| distance(p[0], p[1]))
        .sum()
}

pub fn path_pos(theme: &str, lane: usize, mut progress: f32) -> Point {
    let points = path(theme, lane);
    for segment in points.windows(2) {
        let length = distance(segment[0], segment[1]);
        if progress <= length {
            let part = (progress / length).clamp(0., 1.);
            return [
                segment[0][0] + (segment[1][0] - segment[0][0]) * part,
                segment[0][1] + (segment[1][1] - segment[0][1]) * part,
            ];
        }
        progress -= length;
    }
    points[5]
}

pub const SLOTS: [Point; 24] = [
    [-10.45, -3.4],
    [-8.95, -3.4],
    [-5.25, -3.4],
    [-3.65, -3.4],
    [-10.45, -1.1],
    [-8.95, -1.1],
    [-5.25, -1.1],
    [-3.65, -1.1],
    [-10.45, 1.2],
    [-8.95, 1.2],
    [-5.25, 1.2],
    [-3.65, 1.2],
    [10.45, -3.4],
    [8.95, -3.4],
    [5.25, -3.4],
    [3.65, -3.4],
    [10.45, -1.1],
    [8.95, -1.1],
    [5.25, -1.1],
    [3.65, -1.1],
    [10.45, 1.2],
    [8.95, 1.2],
    [5.25, 1.2],
    [3.65, 1.2],
];

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Setup {
    pub theme: String,
    pub challenge: String,
    pub levels: Vec<u8>,
    pub seed: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Game {
    pub theme: String,
    pub challenge: String,
    pub wave_limit: u8,
    pub wave: u8,
    pub phase: Phase,
    pub tick: u64,
    pub wave_tick: u64,
    pub phase_until: u64,
    pub life: i32,
    pub max_life: i32,
    pub players: Vec<Player>,
    pub pieces: Vec<Piece>,
    pub enemies: Vec<Enemy>,
    pub shots: Vec<Shot>,
    pub events: Vec<Event>,
    pub next_id: u32,
    pub rng: u32,
    pub spawned: u16,
    pub kills: u32,
    pub leaks: u32,
    pub prepared: Vec<bool>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    Lobby,
    Prep,
    Combat,
    Won,
    Lost,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Player {
    pub level: u8,
    pub gold: i32,
    pub recruits: u32,
    pub merges: u32,
    pub casts: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Piece {
    pub id: u32,
    pub actor: String,
    pub owner: usize,
    pub slot: usize,
    pub tier: u8,
    pub rank: u8,
    pub ready: u64,
    pub cast_ready: u64,
    pub moved_until: u64,
    pub buff_until: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Enemy {
    pub id: u32,
    pub kind: String,
    pub lane: usize,
    pub progress: f32,
    pub pos: Point,
    pub hp: f32,
    pub max_hp: f32,
    pub slow_until: u64,
    pub slow: f32,
    pub haste_until: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Shot {
    pub id: u32,
    pub source: u32,
    pub enemy: u32,
    pub from: Point,
    pub to: Point,
    pub attack: String,
    pub started: u64,
    pub impact: u64,
    pub damage: f32,
    pub effect: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub id: u32,
    pub tick: u64,
    pub kind: String,
    pub actor: String,
    pub source: u32,
    pub pos: Point,
    pub power: f32,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Action {
    Start,
    Ready,
    Recruit { slot: Option<usize> },
    Place { actor: String, slot: usize },
    Move { id: u32, slot: usize },
    Merge { id: u32 },
    Upgrade { id: u32 },
    Sell { id: u32 },
    Cast { id: u32, slot: Option<usize> },
    Forfeit,
}

pub fn upgrade_price(rank: u8, tier: u8) -> i32 {
    55 + i32::from(rank) * 32 + i32::from(tier - 1) * 18
}

impl Game {
    pub fn new(setup: Setup) -> Result<Self, &'static str> {
        if setup.levels.is_empty() || setup.levels.len() > 2 {
            return Err("Eine Partie braucht einen oder zwei Spieler.");
        }
        let theme = catalog()
            .themes
            .iter()
            .find(|t| t.id == setup.theme)
            .ok_or("Diese Karte gibt es nicht.")?;
        let challenge = catalog()
            .challenges
            .iter()
            .find(|c| c.id == setup.challenge)
            .ok_or("Diese Herausforderung gibt es nicht.")?;
        let solo = setup.levels.len() == 1;
        let (initial_gold, max_life) = match (setup.challenge.as_str(), solo) {
            ("scarcity", _) => (210, 16),
            (_, true) => (345, 25),
            _ => (310, 22),
        };
        Ok(Self {
            theme: theme.id.clone(),
            challenge: challenge.id.clone(),
            wave_limit: challenge.waves,
            wave: 0,
            phase: Phase::Lobby,
            tick: 0,
            wave_tick: 0,
            phase_until: 0,
            life: max_life,
            max_life,
            players: setup
                .levels
                .into_iter()
                .map(|level| Player {
                    level: level.max(1),
                    gold: initial_gold,
                    recruits: 0,
                    merges: 0,
                    casts: 0,
                })
                .collect(),
            pieces: Vec::new(),
            enemies: Vec::new(),
            shots: Vec::new(),
            events: Vec::new(),
            next_id: 1,
            rng: setup.seed.max(1),
            spawned: 0,
            kills: 0,
            leaks: 0,
            prepared: Vec::new(),
        })
    }

    pub fn finished(&self) -> bool {
        matches!(self.phase, Phase::Won | Phase::Lost)
    }

    fn id(&mut self) -> u32 {
        let id = self.next_id;
        self.next_id += 1;
        id
    }

    fn draw(&mut self, max: usize) -> usize {
        self.rng ^= self.rng << 13;
        self.rng ^= self.rng >> 17;
        self.rng ^= self.rng << 5;
        (self.rng as usize) % max
    }

    fn event(&mut self, kind: &str, actor: &str, source: u32, pos: Point, power: f32) {
        let id = self.id();
        self.events.push(Event {
            id,
            tick: self.tick,
            kind: kind.into(),
            actor: actor.into(),
            source,
            pos,
            power,
        });
    }

    fn valid_slot(&self, player: usize, slot: usize) -> bool {
        slot < SLOTS.len() && (self.players.len() == 1 || player == slot / 12)
    }

    fn free_slot(&self, player: usize, slot: Option<usize>) -> Result<usize, &'static str> {
        let available =
            |slot| self.valid_slot(player, slot) && !self.pieces.iter().any(|p| p.slot == slot);
        slot.filter(|s| available(*s))
            .or_else(|| {
                if slot.is_some() {
                    return None;
                }
                // A recruited unit starts near the lane that is fastest to reach.
                [
                    2, 6, 10, 3, 7, 11, 1, 5, 9, 0, 4, 8, 14, 18, 22, 15, 19, 23, 13, 17, 21, 12,
                    16, 20,
                ]
                .into_iter()
                .find(|s| available(*s))
            })
            .ok_or("Auf diesem Feld ist kein Platz.")
    }

    fn piece_index(&self, player: usize, id: u32) -> Result<usize, &'static str> {
        self.pieces
            .iter()
            .position(|p| p.owner == player && p.id == id)
            .ok_or("Diese Figur gehört dir nicht mehr.")
    }

    fn spend(&mut self, player: usize, amount: i32) -> Result<(), &'static str> {
        if self.players[player].gold < amount {
            return Err("Dafür fehlt dir Gold.");
        }
        self.players[player].gold -= amount;
        Ok(())
    }

    fn recruit_pool(&self, player: usize) -> Vec<&'static Actor> {
        let theme = &self.theme;
        let level = self.players[player].level;
        let entry_level = catalog()
            .themes
            .iter()
            .find(|t| t.id == *theme)
            .map_or(1, |t| t.unlock);
        catalog()
            .actors
            .iter()
            .filter(|a| {
                a.theme == *theme && a.kind == "troop" && a.unlock <= level.max(entry_level)
            })
            .collect()
    }

    fn add_piece(&mut self, player: usize, slot: usize, actor: &str, tier: u8) {
        let id = self.id();
        self.pieces.push(Piece {
            id,
            actor: actor.into(),
            owner: player,
            slot,
            tier,
            rank: 1,
            ready: self.tick + 3,
            cast_ready: self.tick,
            moved_until: 0,
            buff_until: 0,
        });
        self.event(
            if tier > 1 { "merge" } else { "place" },
            actor,
            id,
            SLOTS[slot],
            f32::from(tier),
        );
    }

    pub fn apply(&mut self, player: usize, command: Action) -> Result<(), &'static str> {
        if player >= self.players.len() || self.finished() {
            return Err("Diese Partie ist bereits abgeschlossen.");
        }
        if self.phase == Phase::Lobby && !matches!(command, Action::Start | Action::Forfeit) {
            return Err("Starte zuerst die Partie.");
        }
        match command {
            Action::Start => {
                if player != 0 || self.phase != Phase::Lobby {
                    return Err("Die Partie kann nur einmal vom Gastgeber gestartet werden.");
                }
                self.prepare(0);
            }
            Action::Ready => {
                if self.phase != Phase::Prep {
                    return Err("Die Welle läuft bereits.");
                }
                if !self.prepared[player] {
                    self.prepared[player] = true;
                }
                if self.prepared.iter().all(|ready| *ready) {
                    self.phase_until = self.tick + 1;
                    self.advance(1);
                }
            }
            Action::Recruit { slot } => {
                let slot = self.free_slot(player, slot)?;
                let pool = self.recruit_pool(player);
                if pool.is_empty() {
                    return Err("Es sind keine Rekruten freigeschaltet.");
                }
                self.spend(player, RECRUIT_COST)?;
                let choice = self.draw(pool.len());
                self.add_piece(player, slot, &pool[choice].id, 1);
                self.players[player].recruits += 1;
            }
            Action::Place { actor: id, slot } => {
                let definition = actor(&id).ok_or("Diese Figur gibt es nicht.")?;
                if definition.kind == "troop" || definition.theme != self.theme {
                    return Err("Diese Figur kann hier nicht gebaut werden.");
                }
                let entry_level = catalog()
                    .themes
                    .iter()
                    .find(|t| t.id == self.theme)
                    .map_or(1, |t| t.unlock);
                if definition.unlock > self.players[player].level.max(entry_level) {
                    return Err("Das schaltest du auf einem höheren Profillevel frei.");
                }
                if definition.kind == "hero"
                    && self.pieces.iter().any(|p| {
                        p.owner == player && actor(&p.actor).is_some_and(|a| a.kind == "hero")
                    })
                {
                    return Err("Du kannst jeweils einen Helden aufstellen.");
                }
                self.free_slot(player, Some(slot))?;
                self.spend(player, definition.cost)?;
                self.add_piece(player, slot, &id, 1);
            }
            Action::Move { id, slot } => {
                let index = self.piece_index(player, id)?;
                let piece = &self.pieces[index];
                if actor(&piece.actor).is_some_and(|a| a.kind == "building") {
                    return Err("Gebäude bleiben an ihrem Bauplatz.");
                }
                if !self.valid_slot(player, slot) {
                    return Err("Das Feld liegt außerhalb deiner Bauzone.");
                }
                if piece.slot == slot {
                    return Ok(());
                }
                if piece.moved_until > self.tick {
                    return Err("Die Figur ist noch unterwegs.");
                }
                let previous = piece.slot;
                if let Some(other) = self.pieces.iter().position(|p| p.slot == slot) {
                    let target = &mut self.pieces[other];
                    if target.owner != player
                        || target.moved_until > self.tick
                        || actor(&target.actor).is_some_and(|a| a.kind == "building")
                    {
                        return Err("Der Zielplatz ist belegt.");
                    }
                    target.slot = previous;
                    target.moved_until = self.tick + 10;
                }
                let piece = &mut self.pieces[index];
                piece.slot = slot;
                piece.moved_until = self.tick + 10;
                let kind = piece.actor.clone();
                self.event("move", &kind, id, SLOTS[slot], 0.);
            }
            Action::Merge { id } => {
                let index = self.piece_index(player, id)?;
                let main = &self.pieces[index];
                if main.tier >= MAX_TIER || actor(&main.actor).is_none_or(|a| a.kind != "troop") {
                    return Err("Nur Truppen unter Rang III lassen sich verschmelzen.");
                }
                let mut ids = vec![id];
                ids.extend(
                    self.pieces
                        .iter()
                        .filter(|p| {
                            p.owner == player
                                && p.id != id
                                && p.actor == main.actor
                                && p.tier == main.tier
                        })
                        .take(2)
                        .map(|p| p.id),
                );
                if ids.len() != 3 {
                    return Err("Du brauchst drei gleiche Truppen desselben Rangs.");
                }
                let (slot, tier) = (main.slot, main.tier + 1);
                let pool = self.recruit_pool(player);
                let pick = self.draw(pool.len());
                self.pieces.retain(|p| !ids.contains(&p.id));
                self.add_piece(player, slot, &pool[pick].id, tier);
                self.players[player].merges += 1;
            }
            Action::Upgrade { id } => {
                let index = self.piece_index(player, id)?;
                let piece = &self.pieces[index];
                if piece.rank >= MAX_RANK {
                    return Err("Diese Figur ist vollständig ausgebaut.");
                }
                let price = upgrade_price(piece.rank, piece.tier);
                self.spend(player, price)?;
                let piece = &mut self.pieces[index];
                piece.rank += 1;
                let (kind, pos, power) = (
                    piece.actor.clone(),
                    SLOTS[piece.slot],
                    f32::from(piece.rank),
                );
                self.event("upgrade", &kind, id, pos, power);
            }
            Action::Sell { id } => {
                let index = self.piece_index(player, id)?;
                let piece = self.pieces.remove(index);
                let price = actor(&piece.actor).map_or(RECRUIT_COST, |a| a.cost);
                self.players[player].gold +=
                    price / 2 + 15 * i32::from(piece.rank - 1) + 25 * i32::from(piece.tier - 1);
                self.event("sell", &piece.actor, id, SLOTS[piece.slot], 0.);
            }
            Action::Cast { id, slot } => self.cast(player, id, slot)?,
            Action::Forfeit => {
                self.phase = Phase::Lost;
                self.phase_until = self.tick;
            }
        }
        Ok(())
    }

    fn cast(&mut self, player: usize, id: u32, slot: Option<usize>) -> Result<(), &'static str> {
        let index = self.piece_index(player, id)?;
        let hero = &self.pieces[index];
        let definition = actor(&hero.actor).ok_or("Dieser Held ist nicht verfügbar.")?;
        let skill = definition
            .skill
            .as_deref()
            .ok_or("Nur Helden besitzen eine Spezialfähigkeit.")?;
        if self.phase != Phase::Combat || hero.cast_ready > self.tick {
            return Err("Die Fähigkeit ist gerade nicht bereit.");
        }
        let origin = SLOTS[hero.slot];
        let closest = self
            .enemies
            .iter()
            .filter(|e| distance(e.pos, origin) < 9.)
            .max_by(|a, b| a.progress.total_cmp(&b.progress))
            .map(|e| e.pos);
        let target = slot
            .and_then(|s| SLOTS.get(s).copied())
            .or(closest)
            .unwrap_or(origin);
        if distance(target, origin) > 9.5 {
            return Err("Das liegt außerhalb der Reichweite.");
        }
        let (radius, damage, slow, duration) = match skill {
            "phalanx" => (3.9, 75., 0.83, 95),
            "meteor" => (3.65, 155., 0., 0),
            "salvo" => (4.2, 120., 0.25, 38),
            "oath" => (4.7, 45., 0.72, 100),
            "mist" => (4.65, 58., 0.89, 135),
            _ => (3.4, 174., 0.38, 75),
        };
        let rank_bonus = 1. + f32::from(hero.rank - 1) * 0.28;
        self.pieces[index].cast_ready =
            self.tick + 520 - u64::from(self.pieces[index].rank - 1) * 30;
        let tick = self.tick;
        for enemy in &mut self.enemies {
            if distance(enemy.pos, target) <= radius {
                enemy.hp -= damage * rank_bonus;
                if slow > 0. {
                    enemy.slow = slow;
                    enemy.slow_until = tick + duration;
                }
            }
        }
        if skill == "oath" {
            self.life = (self.life + 3).min(self.max_life);
        }
        if skill == "salvo" {
            for piece in &mut self.pieces {
                if distance(SLOTS[piece.slot], target) <= radius + 1.5 {
                    piece.buff_until = tick + 120;
                }
            }
        }
        if skill == "thunder" {
            if let Some(slot) = slot.filter(|slot| {
                self.valid_slot(player, *slot) && !self.pieces.iter().any(|p| p.slot == *slot)
            }) {
                self.pieces[index].slot = slot;
            }
        }
        self.players[player].casts += 1;
        self.event("cast", skill, id, target, radius);
        self.remove_dead();
        Ok(())
    }

    pub fn advance(&mut self, ticks: u32) {
        for _ in 0..ticks.min(2400) {
            if matches!(self.phase, Phase::Lobby | Phase::Won | Phase::Lost)
                || (self.phase == Phase::Prep && self.phase_until == 0)
            {
                break;
            }
            self.tick += 1;
            if self.tick % 20 == 0 {
                self.events.retain(|event| event.tick + 100 >= self.tick);
            }
            if self.phase == Phase::Prep {
                if self.tick >= self.phase_until {
                    self.begin_wave();
                }
                continue;
            }
            self.wave_tick += 1;
            self.spawn_wave();
            self.move_enemies();
            self.fire();
            self.resolve_shots();
            self.remove_dead();
            if self.life <= 0 {
                self.phase = Phase::Lost;
                continue;
            }
            if self.spawned >= self.wave_size() && self.enemies.is_empty() {
                self.shots.clear();
                if self.wave >= self.wave_limit {
                    self.phase = Phase::Won;
                    self.event("victory", "", 0, [0., 7.0], 0.);
                } else {
                    let bonus = if self.challenge == "scarcity" { 29 } else { 65 };
                    for player in &mut self.players {
                        player.gold += bonus + i32::from(self.wave) * 4;
                    }
                    self.prepare(120);
                }
            }
        }
    }

    fn prepare(&mut self, wait: u64) {
        self.phase = Phase::Prep;
        self.phase_until = if wait == 0 { 0 } else { self.tick + wait };
        self.prepared = vec![false; self.players.len()];
    }

    fn begin_wave(&mut self) {
        self.wave += 1;
        self.wave_tick = 0;
        self.spawned = 0;
        self.phase = Phase::Combat;
        self.event("wave", "", 0, [0., -6.], f32::from(self.wave));
    }

    fn wave_size(&self) -> u16 {
        let base = 7 + u16::from(self.wave) * 2;
        (if self.players.len() == 2 {
            base + 3
        } else {
            base
        })
        .min(44)
    }

    fn spawn_wave(&mut self) {
        let interval = if self.challenge == "rush" { 10 } else { 12 };
        if self.spawned >= self.wave_size() || self.wave_tick % interval != 1 {
            return;
        }
        self.spawned += 1;
        let last = self.spawned == self.wave_size();
        let boss = last
            && (self.wave == self.wave_limit
                || self.wave % 4 == 0
                || (self.challenge == "siege" && self.wave % 2 == 0));
        let kind = if boss {
            if self.wave == self.wave_limit {
                "titan"
            } else {
                "golem"
            }
        } else if self.wave >= 5 && self.spawned % 9 == 0 {
            "herald"
        } else if self.wave >= 4 && self.spawned % 5 == 0 {
            "wisp"
        } else if (self.wave >= 3 || self.challenge == "siege") && self.spawned % 4 == 0 {
            "brute"
        } else if self.wave >= 2 && self.spawned % 3 == 0 {
            "hound"
        } else {
            "reaver"
        };
        let lane = if self.players.len() == 1 && self.wave <= 2 {
            0
        } else {
            (usize::from(self.spawned) + usize::from(self.wave)) % 2
        };
        let def = enemy_kind(kind);
        let growth = 1. + f32::from(self.wave - 1) * 0.095;
        let team_scale = if self.players.len() == 2 { 1.12 } else { 0.79 };
        let hp = def.hp * growth * team_scale * if self.challenge == "siege" { 1.18 } else { 1. };
        let id = self.id();
        self.enemies.push(Enemy {
            id,
            kind: kind.into(),
            lane,
            progress: 0.,
            pos: path_pos(&self.theme, lane, 0.),
            hp,
            max_hp: hp,
            slow_until: 0,
            slow: 0.,
            haste_until: 0,
        });
        if boss {
            self.event("boss", kind, id, self.enemies.last().unwrap().pos, hp);
        }
    }

    fn move_enemies(&mut self) {
        let tick = self.tick;
        let theme = &self.theme;
        let lengths = [path_len(theme, 0), path_len(theme, 1)];
        let rush = if self.challenge == "rush" { 1.27 } else { 1. };
        let heralds: Vec<_> = self
            .enemies
            .iter()
            .filter(|e| e.kind == "herald")
            .map(|e| e.pos)
            .collect();
        let mut leaks = Vec::new();
        self.enemies.retain_mut(|e| {
            let def = enemy_kind(&e.kind);
            if tick % 12 == 0 && heralds.iter().any(|p| distance(*p, e.pos) < 2.8) {
                e.haste_until = tick + 15;
            }
            let haste = if e.haste_until > tick { 1.18 } else { 1. };
            let rage = if e.kind == "titan" && e.hp < e.max_hp * 0.43 {
                1.33
            } else {
                1.
            };
            let slow = if e.slow_until > tick { 1. - e.slow } else { 1. };
            e.progress += def.speed * rush * haste * rage * slow * DT;
            e.pos = path_pos(theme, e.lane, e.progress);
            if e.progress >= lengths[e.lane] {
                leaks.push((e.id, def.leak));
                false
            } else {
                true
            }
        });
        for (id, lost) in leaks {
            self.life = (self.life - lost).max(0);
            self.leaks += 1;
            self.event("leak", "", id, [0., 7.1], lost as f32);
        }
    }

    fn fire(&mut self) {
        let tick = self.tick;
        let auras: Vec<_> = self
            .pieces
            .iter()
            .filter_map(|piece| {
                let def = actor(&piece.actor)?;
                (def.attack == "rally").then_some((piece.id, SLOTS[piece.slot], def.effect))
            })
            .collect();
        let mut fired = Vec::new();
        for piece in &mut self.pieces {
            if piece.ready > tick || piece.moved_until > tick {
                continue;
            }
            let Some(def) = actor(&piece.actor) else {
                continue;
            };
            let origin = SLOTS[piece.slot];
            let range =
                def.range + f32::from(piece.rank - 1) * 0.23 + f32::from(piece.tier - 1) * 0.45;
            let Some(enemy) = self
                .enemies
                .iter()
                .filter(|e| e.hp > 0. && distance(origin, e.pos) <= range)
                .max_by(|a, b| a.progress.total_cmp(&b.progress))
            else {
                continue;
            };
            let aura = auras
                .iter()
                .any(|(id, pos, radius)| *id != piece.id && distance(*pos, origin) <= *radius);
            let boost = if aura || piece.buff_until > tick {
                4
            } else {
                0
            };
            let tier = [1., 2.65, 6.95][usize::from(piece.tier - 1)];
            let rank = 1. + f32::from(piece.rank - 1) * 0.42;
            piece.ready = tick
                + def
                    .period
                    .saturating_sub(boost + u64::from(piece.rank - 1))
                    .max(7);
            let travel = if def.attack == "guard" {
                3
            } else {
                (distance(origin, enemy.pos) * 1.7).round() as u64 + 3
            };
            fired.push(Shot {
                id: 0,
                source: piece.id,
                enemy: enemy.id,
                from: origin,
                to: enemy.pos,
                attack: def.attack.clone(),
                started: tick,
                impact: tick + travel,
                damage: def.damage * tier * rank,
                effect: def.effect,
            });
        }
        for mut shot in fired {
            shot.id = self.id();
            self.shots.push(shot);
        }
    }

    fn resolve_shots(&mut self) {
        let tick = self.tick;
        let mut impacts = Vec::new();
        self.shots.retain_mut(|shot| {
            if shot.impact >= tick {
                if let Some(target) = self.enemies.iter().find(|e| e.id == shot.enemy) {
                    shot.to = target.pos;
                }
                if shot.impact == tick {
                    impacts.push(shot.clone());
                }
            }
            // A short visual tail lets snapshots show even very quick attacks once.
            shot.impact + 15 >= tick
        });
        for shot in impacts {
            let mut damage_shown = 0.;
            for enemy in &mut self.enemies {
                let is_target = enemy.id == shot.enemy;
                if !is_target
                    && (shot.attack != "sun" || distance(enemy.pos, shot.to) > shot.effect)
                {
                    continue;
                }
                let armor = enemy_kind(&enemy.kind).armor;
                let pierce = if shot.attack == "pierce" || shot.attack == "sun" {
                    0.14
                } else {
                    0.
                };
                let damage = shot.damage
                    * (1. - (armor - pierce).max(0.))
                    * if is_target { 1. } else { 0.56 };
                if is_target {
                    damage_shown = damage;
                }
                enemy.hp -= damage;
                if matches!(shot.attack.as_str(), "guard" | "frost") {
                    if enemy.slow_until <= tick || shot.effect >= enemy.slow {
                        enemy.slow = shot.effect;
                        enemy.slow_until = tick + 40;
                    }
                }
            }
            self.event("impact", &shot.attack, shot.enemy, shot.to, damage_shown);
        }
    }

    fn remove_dead(&mut self) {
        let mut dead = Vec::new();
        self.enemies.retain(|enemy| {
            if enemy.hp > 0. {
                return true;
            }
            dead.push((enemy.id, enemy.kind.clone(), enemy.pos));
            false
        });
        for (id, kind, pos) in dead {
            self.kills += 1;
            let shared = if self.players.len() == 2 { 6 } else { 12 };
            let reward = if kind == "titan" || kind == "golem" {
                55
            } else {
                shared
            };
            for player in &mut self.players {
                player.gold += if self.challenge == "scarcity" {
                    reward * 2 / 3
                } else {
                    reward
                };
            }
            self.event("death", &kind, id, pos, reward as f32);
        }
    }
}

#[cfg(target_arch = "wasm32")]
mod wasm {
    use super::*;
    use wasm_bindgen::prelude::*;

    fn encode<T: Serialize>(value: &T) -> Result<String, JsError> {
        serde_json::to_string(value).map_err(|e| JsError::new(&e.to_string()))
    }

    #[wasm_bindgen]
    pub fn create_game(setup: &str) -> Result<String, JsError> {
        let setup = serde_json::from_str(setup).map_err(|e| JsError::new(&e.to_string()))?;
        Game::new(setup)
            .map_err(JsError::new)
            .and_then(|game| encode(&game))
    }

    #[wasm_bindgen]
    pub fn advance_game(game: &str, ticks: u32) -> Result<String, JsError> {
        let mut game: Game =
            serde_json::from_str(game).map_err(|e| JsError::new(&e.to_string()))?;
        game.advance(ticks);
        encode(&game)
    }

    #[wasm_bindgen]
    pub fn apply_action(game: &str, player: usize, action: &str) -> Result<String, JsError> {
        let mut game: Game =
            serde_json::from_str(game).map_err(|e| JsError::new(&e.to_string()))?;
        let action: Action =
            serde_json::from_str(action).map_err(|e| JsError::new(&e.to_string()))?;
        game.apply(player, action).map_err(JsError::new)?;
        encode(&game)
    }

    #[wasm_bindgen]
    pub fn board_slots() -> Result<String, JsError> {
        encode(&SLOTS)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn game() -> Game {
        Game::new(Setup {
            theme: "aegean".into(),
            challenge: "campaign".into(),
            levels: vec![3, 3],
            seed: 773,
        })
        .unwrap()
    }

    #[test]
    fn three_recruits_merge_and_cannot_touch_the_partner_zone() {
        let mut game = game();
        game.apply(0, Action::Start).unwrap();
        for slot in 0..3 {
            game.add_piece(0, slot, "hoplite", 1);
        }
        let id = game.pieces[0].id;
        assert!(game.apply(1, Action::Merge { id }).is_err());
        game.apply(0, Action::Merge { id }).unwrap();
        assert_eq!(game.pieces.len(), 1);
        assert_eq!(game.pieces[0].tier, 2);
        assert!(
            game.apply(
                0,
                Action::Move {
                    id: game.pieces[0].id,
                    slot: 12
                }
            )
            .is_err()
        );
    }

    #[test]
    fn buildings_are_fixed_and_both_players_ready_the_wave() {
        let mut game = game();
        game.apply(0, Action::Start).unwrap();
        game.apply(
            0,
            Action::Place {
                actor: "ballista".into(),
                slot: 2,
            },
        )
        .unwrap();
        let id = game.pieces[0].id;
        assert!(game.apply(0, Action::Move { id, slot: 3 }).is_err());
        game.apply(0, Action::Ready).unwrap();
        assert_eq!(game.phase, Phase::Prep);
        game.apply(1, Action::Ready).unwrap();
        assert_eq!(game.phase, Phase::Combat);
        game.advance(400);
        assert!(game.kills > 0);
        assert!(game.players[0].gold > 310 - 145);
    }

    #[test]
    fn simulation_is_reproducible_across_checkpoints() {
        let mut first = game();
        first.apply(0, Action::Start).unwrap();
        first.apply(0, Action::Recruit { slot: Some(2) }).unwrap();
        first.apply(0, Action::Ready).unwrap();
        first.apply(1, Action::Ready).unwrap();
        let saved = serde_json::to_string(&first).unwrap();
        let mut second: Game = serde_json::from_str(&saved).unwrap();
        first.advance(650);
        for _ in 0..13 {
            second.advance(50);
        }
        assert_eq!(
            serde_json::to_string(&first).unwrap(),
            serde_json::to_string(&second).unwrap()
        );
    }
}
