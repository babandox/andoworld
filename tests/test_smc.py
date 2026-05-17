from andoworldstate.smc import Particle, SequentialMonteCarlo


def test_smc_normalizes_particle_weights_to_sum_to_one():
    particles = [Particle(state="a", weight=2.0), Particle(state="b", weight=6.0)]
    smc = SequentialMonteCarlo(particles)

    smc.normalize_weights()

    assert [p.weight for p in smc.particles] == [0.25, 0.75]


def test_smc_effective_sample_size_uses_inverse_sum_squared_weights():
    particles = [Particle(state="a", weight=0.5), Particle(state="b", weight=0.5)]
    smc = SequentialMonteCarlo(particles)

    assert smc.effective_sample_size() == 2.0


def test_smc_systematic_resampling_replicates_particles_by_normalized_weight():
    particles = [Particle(state="a", weight=0.1), Particle(state="b", weight=0.9)]
    smc = SequentialMonteCarlo(particles)

    resampled = smc.systematic_resample(start=0.05)

    assert [p.state for p in resampled] == ["a", "b"]
    assert [p.weight for p in resampled] == [0.5, 0.5]
