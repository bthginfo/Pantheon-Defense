export const materials = Object.freeze({
  training: 'Trainingsmarken',
  blueprints: 'Baupläne',
  shards: 'Heldensplitter',
  runedust: 'Runenstaub',
  cores: 'Urkerne',
  seals: 'Siegel',
});

export const waveMaterials = ['training', 'blueprints', 'shards', 'runedust', 'cores'];
const costs = {
  troop: ['training', [3, 5, 8]],
  building: ['blueprints', [2, 4, 6]],
  hero: ['shards', [2, 4, 6]],
};

export function masteryPayment(kind, rank, balances = {}, seals = 0) {
  const primary = costs[kind];
  if (primary && (balances[primary[0]] ?? 0) >= primary[1][rank]) {
    return { material: primary[0], amount: primary[1][rank], affordable: true };
  }
  if (!primary || seals >= rank + 1) {
    return { material: 'seals', amount: rank + 1, affordable: seals >= rank + 1 };
  }
  return { material: primary[0], amount: primary[1][rank], affordable: false };
}

export function difficultyProgress(stage, stages, profile) {
  const prior = stages.find(candidate => candidate.rank === stage.rank - 1);
  const wins = profile?.campaignWins?.[prior?.id] ?? 0;
  const ranks = Object.values(profile?.masteries ?? {}).reduce((sum, rank) => sum + rank, 0);
  return { prior, wins, ranks, unlocked: wins >= stage.clears && ranks >= stage.mastery };
}
