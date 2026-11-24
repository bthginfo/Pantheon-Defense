use super::*;
use std::sync::OnceLock;

pub const CIRCUIT_RULES: u8 = 2;
const TILES: [Point; 32] = [
    [-4.35, -6.70],
    [-1.47, -6.70],
    [1.47, -6.70],
    [4.35, -6.70],
    [-4.35, -5.0],
    [-1.47, -5.0],
    [1.47, -5.0],
    [4.35, -5.0],
    [-4.35, -3.30],
    [-1.47, -3.30],
    [1.47, -3.30],
    [4.35, -3.30],
    [-4.35, -1.60],
    [-1.47, -1.60],
    [1.47, -1.60],
    [4.35, -1.60],
    [-4.35, 1.60],
    [-1.47, 1.60],
    [1.47, 1.60],
    [4.35, 1.60],
    [-4.35, 3.30],
    [-1.47, 3.30],
    [1.47, 3.30],
    [4.35, 3.30],
    [-4.35, 5.0],
    [-1.47, 5.0],
    [1.47, 5.0],
    [4.35, 5.0],
    [-4.35, 6.70],
    [-1.47, 6.70],
    [1.47, 6.70],
    [4.35, 6.70],
];
const DRAW_ORDER: [usize; 32] = [
    16, 19, 20, 23, 24, 27, 28, 31, 0, 3, 4, 7, 8, 11, 12, 15, 17, 18, 21, 22, 25, 26, 29, 30, 1,
    2, 5, 6, 9, 10, 13, 14,
];

pub fn tiles_for(rules: u8) -> &'static [Point] {
    if rules >= CIRCUIT_RULES {
        &TILES
    } else {
        &SLOTS
    }
}

pub fn circuit_route(theme: &str, lane: usize) -> [Point; 9] {
    let mut route = [
        [-6.48, -6.63],
        [-4.65, -8.94],
        [4.57, -8.94],
        [6.48, -6.69],
        [6.48, 6.63],
        [4.65, 8.94],
        [-4.57, 8.94],
        [-6.48, 6.69],
    ];
    if theme == "japan" {
        route[1] = [-4.55, -8.70];
        route[5] = [4.55, 8.70];
    }
    if theme == "rome" {
        route[2] = [5.04, -8.94];
        route[6] = [-5.04, 8.94];
    }
    let start = if lane == 0 { 0 } else { 4 };
    std::array::from_fn(|index| route[(index + start) % route.len()])
}

pub fn route_point(rules: u8, theme: &str, lane: usize, progress: f32) -> Point {
    if rules < CIRCUIT_RULES {
        return path_pos(theme, lane, progress);
    }
    let routes = ROUTES.get_or_init(|| {
        ["aegean", "rome", "japan"].map(|theme| {
            [0, 1].map(|lane| {
                let points = circuit_route(theme, lane);
                let lengths = std::array::from_fn(|i| distance(points[i], points[i + 1]));
                Course {
                    points,
                    lengths,
                    total: lengths.iter().sum(),
                }
            })
        })
    });
    let index = match theme {
        "rome" => 1,
        "japan" => 2,
        _ => 0,
    };
    let course = &routes[index][usize::from(lane > 0)];
    let mut offset = progress.rem_euclid(course.total);
    for (index, length) in course.lengths.iter().enumerate() {
        if offset <= *length {
            let t = offset / length;
            let [x1, z1] = course.points[index];
            let [x2, z2] = course.points[index + 1];
            return [x1 + t * (x2 - x1), z1 + t * (z2 - z1)];
        }
        offset -= length;
    }
    course.points[0]
}

struct Course {
    points: [Point; 9],
    lengths: [f32; 8],
    total: f32,
}

static ROUTES: OnceLock<[[Course; 2]; 3]> = OnceLock::new();

pub fn squad_damage(tier: u8, rank: u8, count: u8, mastery: u8, temper: u8, circuit: bool) -> f32 {
    let rarity = if circuit {
        [1., 1.38, 1.92, 2.68, 4.15][(tier.clamp(1, 5) - 1) as usize]
    } else {
        [1., 2.65, 6.95][(tier.clamp(1, 3) - 1) as usize]
    };
    let rank = 1. + f32::from(rank.saturating_sub(1)) * if circuit { 0.24 } else { 0.42 };
    rarity
        * rank
        * (1. + f32::from(mastery) * 0.07)
        * (1. + f32::from(temper) * 0.12)
        * f32::from(count.max(1))
}

impl Game {
    pub fn on_circuit(&self) -> bool {
        self.rule_version >= CIRCUIT_RULES
    }

    pub fn tiles(&self) -> &'static [Point] {
        tiles_for(self.rule_version)
    }

    pub fn tile_owner(&self, slot: usize) -> usize {
        if self.on_circuit() {
            1 - slot.min(31) / 16
        } else {
            slot / 12
        }
    }

    pub(crate) fn circuit_free(&self, player: usize, slot: Option<usize>) -> Option<usize> {
        let available =
            |slot| self.valid_slot(player, slot) && !self.pieces.iter().any(|p| p.slot == slot);
        match slot {
            Some(slot) => available(slot).then_some(slot),
            None => DRAW_ORDER.into_iter().find(|slot| available(*slot)),
        }
    }

    pub fn summon_cost(&self, player: usize) -> i32 {
        if !self.on_circuit() {
            return if self.challenge == "levy" {
                50
            } else {
                RECRUIT_COST
            };
        }
        let base: i32 = if self.challenge == "levy" { 21 } else { 26 };
        (base
            + i32::try_from(self.players[player].recruits)
                .unwrap_or(60)
                .min(46)
                * 2)
        .min(118)
    }

    pub fn forge_cost(&self, player: usize, tier: u8) -> i32 {
        33 + 16 * i32::from(tier.saturating_sub(1))
            + 24 * i32::from(self.players[player].temper[usize::from(tier.clamp(1, 5) - 1)])
    }

    fn circuit_pool(&self, player: usize, tier: u8) -> Vec<&'static Actor> {
        self.recruit_pool(player)
            .into_iter()
            .filter(|actor| actor.rarity == tier)
            .collect()
    }

    fn find_stack(
        &self,
        player: usize,
        actor: &str,
        tier: u8,
        slot: Option<usize>,
    ) -> Option<usize> {
        self.pieces.iter().position(|piece| {
            piece.owner == player
                && piece.actor == actor
                && piece.tier == tier
                && piece.stack < 3
                && slot.is_none_or(|tile| tile == piece.slot)
        })
    }

    pub(crate) fn circuit_draw(
        &mut self,
        player: usize,
        target: Option<usize>,
    ) -> Result<(), &'static str> {
        if self.players[player].reserve.len() >= 6 {
            return Err("Setze zuerst einen Rekruten aus der Reserve.");
        }
        if target.is_some_and(|slot| !self.valid_slot(player, slot)) {
            return Err("Der Platz gehört dem Mitspieler.");
        }
        let roll = self.draw(10_000);
        let favor = usize::from(self.players[player].favor);
        let tier = if roll < 85 + 60 * favor {
            5
        } else if roll < 415 + 125 * favor {
            4
        } else if roll < 1_500 + 180 * favor {
            3
        } else if roll < 4_000 + 200 * favor {
            2
        } else {
            1
        };
        let definition = self
            .roll_recruit(player, tier)
            .ok_or("Es sind keine Truppen freigeschaltet.")?;
        self.spend(player, self.summon_cost(player))?;
        self.players[player].recruits += 1;
        let id = self.reserve_recruit(player, definition);
        // A requested destination is convenient for scripted and keyboard clients. The draw has
        // already happened and stays in the reserve if that destination does not fit the unit.
        if let Some(slot) = target {
            let _ = self.deploy_recruit(player, id, slot);
        }
        if self.players[player].recruits == 5 {
            self.players[player].essence += 2;
            self.event("bounty", "", 0, [0., 0.], 2.);
        }
        Ok(())
    }

    pub(crate) fn oracle(&mut self, player: usize, tier: u8) -> Result<(), &'static str> {
        if !self.on_circuit() || !(2..=5).contains(&tier) {
            return Err("Diese Orakelziehung gibt es hier nicht.");
        }
        if self.players[player].reserve.len() >= 6 {
            return Err("Setze zuerst einen Rekruten aus der Reserve.");
        }
        let (cost, chance) = [(2, 72), (3, 49), (4, 32), (6, 18)][usize::from(tier - 2)];
        if self.players[player].essence < cost {
            return Err("Dafür fehlt dir Essenz.");
        }
        let pool = self.circuit_pool(player, tier);
        if pool.is_empty() {
            return Err("Diese Seltenheit ist noch gesperrt.");
        }
        let success = self.draw(100) < chance;
        let mut id = 0;
        if success {
            let draw = pool[self.draw(pool.len())];
            id = self.reserve_recruit(player, draw);
        }
        self.players[player].essence -= cost;
        self.event(
            if success { "oracle_hit" } else { "oracle_miss" },
            "",
            id,
            [0., 0.],
            f32::from(tier),
        );
        Ok(())
    }

    fn roll_recruit(&mut self, player: usize, tier: u8) -> Option<&'static Actor> {
        for tier in (1..=tier).rev() {
            let pool = self.circuit_pool(player, tier);
            if !pool.is_empty() {
                return Some(pool[self.draw(pool.len())]);
            }
        }
        None
    }

    fn reserve_recruit(&mut self, player: usize, actor: &Actor) -> u32 {
        let id = self.id();
        self.players[player].reserve.push(Recruit {
            id,
            actor: actor.id.clone(),
            tier: actor.rarity,
        });
        self.event("reserve", &actor.id, id, [0., 0.], f32::from(actor.rarity));
        id
    }

    pub(crate) fn deploy_recruit(
        &mut self,
        player: usize,
        id: u32,
        slot: usize,
    ) -> Result<(), &'static str> {
        if !self.on_circuit() || !self.valid_slot(player, slot) {
            return Err("Dieser Bauplatz gehört dir nicht.");
        }
        let index = self.players[player]
            .reserve
            .iter()
            .position(|recruit| recruit.id == id)
            .ok_or("Dieser Rekrut ist nicht mehr in deiner Reserve.")?;
        let recruit = &self.players[player].reserve[index];
        let stack = self.find_stack(player, &recruit.actor, recruit.tier, Some(slot));
        if stack.is_none() && self.circuit_free(player, Some(slot)).is_none() {
            return Err("Hier passen nur bis zu drei identische Truppen derselben Seltenheit.");
        }
        let recruit = self.players[player].reserve.remove(index);
        self.put_draw(player, &recruit.actor, recruit.tier, slot, stack);
        Ok(())
    }

    pub(crate) fn release_recruit(&mut self, player: usize, id: u32) -> Result<(), &'static str> {
        let index = self.players[player]
            .reserve
            .iter()
            .position(|r| r.id == id)
            .ok_or("Dieser Rekrut ist nicht mehr in deiner Reserve.")?;
        let recruit = self.players[player].reserve.remove(index);
        self.players[player].gold += 5 + 3 * i32::from(recruit.tier);
        Ok(())
    }

    fn put_draw(
        &mut self,
        player: usize,
        actor: &str,
        tier: u8,
        slot: usize,
        stack: Option<usize>,
    ) {
        if let Some(index) = stack {
            let piece = &mut self.pieces[index];
            piece.stack += 1;
            let (id, stack) = (piece.id, piece.stack);
            self.event("stack", actor, id, self.tiles()[slot], f32::from(stack));
        } else {
            self.add_piece(player, slot, actor, tier);
            let id = self.pieces.last().unwrap().id;
            self.event("draw", actor, id, self.tiles()[slot], f32::from(tier));
        }
    }

    pub(crate) fn circuit_merge(&mut self, player: usize, id: u32) -> Result<(), &'static str> {
        let index = self.piece_index(player, id)?;
        let main = &self.pieces[index];
        if main.tier >= 5 || actor(&main.actor).is_none_or(|a| a.kind != "troop") {
            return Err("Legendäre Truppen haben bereits den höchsten Rang.");
        }
        let tier = main.tier;
        let slot = main.slot;
        if main.stack != 3 {
            return Err("Verschmelze drei identische Kämpfer auf demselben Feld.");
        }
        let pool = self.circuit_pool(player, tier + 1);
        if pool.is_empty() {
            return Err("Die nächste Seltenheit ist noch gesperrt.");
        }
        let draw = pool[self.draw(pool.len())].id.as_str();
        self.pieces.remove(index);
        self.add_piece(player, slot, draw, tier + 1);
        let result = self.pieces.last().unwrap().id;
        self.event(
            "merge",
            draw,
            result,
            self.tiles()[slot],
            f32::from(tier + 1),
        );
        self.players[player].merges += 1;
        self.players[player].essence += (tier >= 2) as i32;
        if self.players[player].merges == 2 {
            self.players[player].essence += 2;
            self.event("bounty", "", 0, [0., 0.], 2.);
        }
        Ok(())
    }

    pub(crate) fn ritual(&mut self, player: usize, hero: &str) -> Result<(), &'static str> {
        let hero = actor(hero)
            .filter(|a| a.kind == "hero" && a.theme == self.theme && !a.recipe.is_empty())
            .ok_or("Dieser Held ist in dieser Schlacht nicht verfügbar.")?;
        if !self.on_circuit() || !self.accessible(player, hero) {
            return Err("Dieser Held ist noch gesperrt.");
        }
        if self
            .pieces
            .iter()
            .filter(|piece| {
                piece.owner == player && actor(&piece.actor).is_some_and(|a| a.kind == "hero")
            })
            .count()
            >= 3
        {
            return Err("Pro Aufstellung sind drei Helden möglich.");
        }
        let mut recipe = BTreeMap::<&str, u8>::new();
        for ingredient in &hero.recipe {
            *recipe.entry(ingredient).or_default() += 1;
        }
        let mut candidates: Vec<_> = self
            .pieces
            .iter()
            .filter(|piece| piece.owner == player && recipe.contains_key(piece.actor.as_str()))
            .map(|piece| {
                (
                    piece.id,
                    piece.slot,
                    piece.actor.as_str(),
                    piece.stack,
                    piece.rank,
                )
            })
            .collect();
        candidates.sort_by_key(|(id, _, _, _, rank)| (*rank, *id));
        let mut consumed = BTreeMap::new();
        let mut slotted = None;
        for (id, slot, name, count, _) in candidates {
            let amount = recipe.get_mut(name).unwrap();
            let used = (*amount).min(count);
            *amount -= used;
            if used > 0 {
                consumed.insert(id, used);
            }
            if used == count && slotted.is_none() {
                slotted = Some(slot);
            }
        }
        if recipe.values().any(|amount| *amount > 0) {
            return Err("Dir fehlen Truppen für das Heldenrezept.");
        }
        let slot = slotted
            .or_else(|| self.circuit_free(player, None))
            .ok_or("Du brauchst Platz für den Helden.")?;
        self.spend(player, 65)?;
        for piece in &mut self.pieces {
            if let Some(used) = consumed.get(&piece.id) {
                piece.stack -= used;
            }
        }
        self.pieces.retain(|p| p.stack > 0);
        self.add_piece(player, slot, &hero.id, 5);
        self.players[player].summoned += 1;
        let id = self.pieces.last().unwrap().id;
        self.event("ritual", &hero.id, id, self.tiles()[slot], 5.);
        Ok(())
    }

    pub(crate) fn accessible(&self, player: usize, actor: &Actor) -> bool {
        let entry = catalog()
            .themes
            .iter()
            .find(|theme| theme.id == self.theme)
            .map_or(1, |theme| theme.unlock);
        actor.unlock <= self.players[player].level.max(entry)
    }

    pub(crate) fn temper(&mut self, player: usize, tier: u8) -> Result<(), &'static str> {
        if !self.on_circuit() || !(1..=5).contains(&tier) {
            return Err("Diese Schmiedestufe ist nicht verfügbar.");
        }
        let index = usize::from(tier - 1);
        if self.players[player].temper[index] >= 6 {
            return Err("Dieser Rang ist vollständig geschmiedet.");
        }
        self.spend(player, self.forge_cost(player, tier))?;
        self.players[player].temper[index] += 1;
        self.event("temper", "", 0, [0., 0.], f32::from(tier));
        Ok(())
    }

    pub(crate) fn fortune(&mut self, player: usize) -> Result<(), &'static str> {
        if !self.on_circuit() || self.players[player].favor >= 5 {
            return Err("Die Anrufung ist vollständig ausgebaut.");
        }
        self.spend(player, 65 + i32::from(self.players[player].favor) * 34)?;
        self.players[player].favor += 1;
        Ok(())
    }

    pub fn wave_duration(&self) -> u64 {
        if self.challenge == "rush" {
            214
        } else if self.challenge == "endurance" {
            246
        } else {
            260
        }
    }

    pub fn pressure_limit(&self) -> usize {
        (match self.challenge.as_str() {
            "scarcity" => 34,
            "eclipse" => 43,
            _ => 45,
        }) + if self.players.len() == 2 { 19 } else { 0 }
    }

    pub(crate) fn finish_circuit_tick(&mut self) {
        if self.enemies.len() >= self.pressure_limit()
            || self
                .enemies
                .iter()
                .any(|enemy| enemy.deadline > 0 && self.tick >= enemy.deadline)
        {
            self.phase = Phase::Lost;
            self.life = 0;
            return;
        }
        if self.wave < self.wave_limit && self.wave_tick >= self.wave_duration() {
            let wave = self.wave;
            for player in &mut self.players {
                let interest = (player.gold / 18).min(22);
                player.gold += 17 + i32::from(wave / 3) + interest;
                if wave % 3 == 0 {
                    player.essence += 1;
                }
            }
            self.begin_wave();
        } else if self.wave == self.wave_limit {
            if self.spawned >= self.wave_size() && self.enemies.is_empty() {
                self.phase = Phase::Won;
                self.shots.clear();
                self.boss_cast = None;
                self.event("victory", "", 0, [0., 0.], 0.);
            } else if self.wave_tick > self.wave_duration() + 580 {
                self.phase = Phase::Lost;
                self.life = 0;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn opened(levels: Vec<u8>) -> Game {
        let mut game = Game::new(Setup {
            rule_version: CIRCUIT_RULES,
            theme: "aegean".into(),
            challenge: "campaign".into(),
            levels,
            masteries: Vec::new(),
            seed: 17655,
        })
        .unwrap();
        game.apply(0, Action::Start).unwrap();
        game
    }

    #[test]
    fn deploying_reserves_requires_a_matching_open_field_and_three_can_merge_at_level_one() {
        let mut game = opened(vec![1, 1]);
        game.apply(0, Action::Recruit { slot: None }).unwrap();
        assert!(game.pieces.is_empty());
        assert_eq!(game.players[0].reserve.len(), 1);

        let hoplite = actor("hoplite").unwrap();
        let first = game.reserve_recruit(0, hoplite);
        assert!(
            game.apply(1, Action::Deploy { id: first, slot: 0 })
                .is_err()
        );
        assert!(
            game.apply(0, Action::Deploy { id: first, slot: 0 })
                .is_err()
        );
        game.apply(
            0,
            Action::Deploy {
                id: first,
                slot: 18,
            },
        )
        .unwrap();

        let different = game.reserve_recruit(0, actor("slinger").unwrap());
        assert!(
            game.apply(
                0,
                Action::Deploy {
                    id: different,
                    slot: 18
                }
            )
            .is_err()
        );
        assert!(game.players[0].reserve.iter().any(|r| r.id == different));
        game.apply(
            0,
            Action::Deploy {
                id: different,
                slot: 20,
            },
        )
        .unwrap();
        let stack = game.pieces[0].id;
        assert!(game.apply(0, Action::Merge { id: stack }).is_err());
        for _ in 0..2 {
            let recruit = game.reserve_recruit(0, hoplite);
            game.apply(
                0,
                Action::Deploy {
                    id: recruit,
                    slot: 18,
                },
            )
            .unwrap();
        }
        assert_eq!(game.pieces[0].stack, 3);
        let extra = game.reserve_recruit(0, hoplite);
        assert!(
            game.apply(
                0,
                Action::Deploy {
                    id: extra,
                    slot: 18
                }
            )
            .is_err()
        );
        assert!(game.apply(1, Action::Merge { id: stack }).is_err());
        game.apply(0, Action::Merge { id: stack }).unwrap();
        let evolved = game.pieces.iter().find(|piece| piece.slot == 18).unwrap();
        assert_eq!((evolved.tier, evolved.stack), (2, 1));
        assert_eq!(game.players[0].merges, 1);
        assert!(game.players[0].reserve.iter().any(|r| r.id == extra));
    }

    #[test]
    fn all_factions_have_the_full_rarity_ladder_at_their_starting_level() {
        for theme in &catalog().themes {
            let game = Game::new(Setup {
                rule_version: CIRCUIT_RULES,
                theme: theme.id.clone(),
                challenge: "campaign".into(),
                levels: vec![theme.unlock],
                masteries: Vec::new(),
                seed: 42,
            })
            .unwrap();
            for tier in 1..=5 {
                assert!(
                    !game.circuit_pool(0, tier).is_empty(),
                    "{} tier {tier}",
                    theme.id
                );
            }
        }
    }

    #[test]
    fn waves_keep_the_previous_enemies_on_the_circuit() {
        let mut game = opened(vec![1]);
        game.apply(0, Action::Ready).unwrap();
        game.advance(game.wave_duration() as u32 + 1);
        assert_eq!((game.phase, game.wave), (Phase::Combat, 2));
        assert!(game.enemies.len() > usize::from(game.spawned));
        assert_eq!(game.leaks, 0);
    }
}
