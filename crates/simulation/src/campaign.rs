use super::{Game, catalog};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Difficulty {
    pub id: String,
    pub name: String,
    pub detail: String,
    pub rank: u8,
    pub hp: f32,
    pub speed: f32,
    pub boss_hp: f32,
    pub pressure: i32,
    pub reward: f32,
    pub clears: u8,
    pub mastery: u8,
}

pub fn difficulty(id: &str) -> Option<&'static Difficulty> {
    catalog().difficulties.iter().find(|stage| stage.id == id)
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct FieldSign {
    pub id: String,
    pub gold: [i32; 2],
    pub essence: [i32; 2],
    pub boss_damage: [f32; 2],
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct EquippedFieldSign {
    pub id: String,
    pub rank: u8,
}

impl EquippedFieldSign {
    pub(crate) fn bonus(&self) -> Option<(&'static FieldSign, usize)> {
        let rank = usize::from(self.rank.checked_sub(1)?);
        if rank >= 2 {
            return None;
        }
        catalog()
            .field_signs
            .iter()
            .find(|sign| sign.id == self.id)
            .map(|sign| (sign, rank))
    }
}

#[derive(Debug, Default, Clone, Deserialize, Serialize)]
#[serde(default)]
pub struct Spoils {
    pub training: u16,
    pub blueprints: u16,
    pub shards: u16,
    pub runedust: u16,
    pub cores: u16,
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RewardMaterial {
    Training,
    Blueprints,
    Shards,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct WaveReward {
    pub wave: u8,
    pub gold: i32,
    pub essence: i32,
    pub material: RewardMaterial,
    pub amount: u16,
    #[serde(default)]
    pub runedust: u16,
    #[serde(default)]
    pub cores: u16,
}

#[derive(Debug, Default, Clone, Deserialize, Serialize)]
pub struct Treasury {
    pub wave: u8,
    pub spoils: Spoils,
    pub latest: Option<WaveReward>,
}

impl Game {
    pub fn difficulty_config(&self) -> Option<&'static Difficulty> {
        self.difficulty.as_deref().and_then(difficulty)
    }

    pub fn enemy_speed_multiplier(&self) -> f32 {
        self.difficulty_config().map_or(1., |stage| stage.speed)
    }

    pub(crate) fn regional_formation(&self, fallback: &'static str, boss: bool) -> &'static str {
        let Some(stage) = self.difficulty_config() else {
            return fallback;
        };
        let Some(region) = catalog()
            .themes
            .iter()
            .find(|region| region.id == self.theme)
        else {
            return fallback;
        };
        if boss {
            let index = if self.wave == self.wave_limit {
                usize::from(stage.rank)
            } else if self.wave >= 24 && stage.rank >= 2 {
                usize::from(stage.rank - 1)
            } else if self.wave >= 18 || stage.rank >= 3 {
                1
            } else {
                0
            };
            return region.boss_pack.get(index).map_or(fallback, String::as_str);
        }
        if region.wave_pack.is_empty() {
            return fallback;
        }
        if self.challenge == "eclipse" && matches!(fallback, "moth" | "warden") {
            let family = catalog().enemies.iter().find(|enemy| enemy.id == fallback);
            if let Some(family) = family {
                return region
                    .wave_pack
                    .iter()
                    .filter_map(|id| catalog().enemies.iter().find(|enemy| enemy.id == *id))
                    .find(|enemy| enemy.family() == family.family())
                    .map_or(fallback, |enemy| enemy.id.as_str());
            }
        }
        // Later waves keep their evolved formation. Higher ranks reinforce it with elites sooner.
        let last = region.wave_pack.len() - 1;
        let band = usize::from(self.wave.saturating_sub(1) / 5);
        let lead = (band + usize::from(stage.rank >= 3)).min(last);
        let index = if self.spawned.is_multiple_of(4) {
            lead.saturating_sub(1)
        } else if self.spawned.is_multiple_of(7) {
            (lead + usize::from(stage.rank)).min(last)
        } else {
            lead
        };
        region.wave_pack[index].as_str()
    }

    pub(crate) fn reward_wave(&mut self, final_wave: bool) {
        let wave = self.wave;
        let rank = self.difficulty_config().map_or(0, |stage| stage.rank);
        let Some(treasury) = self.treasury.as_mut() else {
            if !final_wave {
                for player in &mut self.players {
                    player.gold += 17 + i32::from(wave / 3) + (player.gold / 18).min(22);
                    player.essence += i32::from(wave.is_multiple_of(3));
                }
            }
            return;
        };
        if wave <= treasury.wave {
            return;
        }

        let gold = 17 + i32::from(wave / 3) + i32::from(rank) * 3;
        let material = if final_wave || wave.is_multiple_of(6) {
            RewardMaterial::Shards
        } else if wave.is_multiple_of(4) {
            RewardMaterial::Blueprints
        } else {
            RewardMaterial::Training
        };
        let essence = if final_wave || wave.is_multiple_of(6) {
            2 + i32::from(rank >= 3)
        } else {
            i32::from(wave.is_multiple_of(3))
        };
        let amount = 1 + u16::from(rank / 2) + u16::from(final_wave);
        let runedust = if rank >= 1 && (wave.is_multiple_of(5) || final_wave) {
            1 + u16::from(rank / 2) + u16::from(final_wave)
        } else {
            0
        };
        let cores = if rank >= 2 && (wave.is_multiple_of(6) || final_wave) {
            u16::from(rank - 1) + u16::from(final_wave)
        } else {
            0
        };
        match material {
            RewardMaterial::Training => treasury.spoils.training += amount,
            RewardMaterial::Blueprints => treasury.spoils.blueprints += amount,
            RewardMaterial::Shards => treasury.spoils.shards += amount,
        }
        treasury.spoils.runedust += runedust;
        treasury.spoils.cores += cores;
        treasury.wave = wave;
        treasury.latest = Some(WaveReward {
            wave,
            gold,
            essence,
            material,
            amount,
            runedust,
            cores,
        });
        for player in &mut self.players {
            player.gold += gold + (player.gold / 18).min(22);
            player.essence += essence;
        }
    }
}
