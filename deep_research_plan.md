Architecting a Geopolitical Predictive Simulation Engine: Advanced Mathematical Frameworks for Sequential Monte Carlo Agent-Based Models
The integration of Agent-Based Modeling (ABM) with Graph Databases (Neo4j) and Sequential Monte Carlo (SMC) Particle Filtering represents a foundational paradigm shift in computational political science and generative social science. Foundational theoretical baselines incorporating Bruce Bueno de Mesquita's spatial expected utility models, Daniel Kahneman's prospect theory, Nassim Nicholas Taleb's non-ergodic constraints, and Philip Tetlock's Bayesian updating provide a robust starting architecture for modeling bounded rationality and risk assessment. However, to evolve a simulation engine into a highly deterministic, probabilistic mathematical system capable of continuous, automated data assimilation across thousands of parallel graph trajectories, the theoretical baseline must be expanded. Modeling the genesis of civil violence, the collapse of state structures, the topological propagation of behavioral contagions, and the noncompensatory nature of elite political survival requires an orchestration of deeper mathematical frameworks.
The objective of this report is to define seven state-of-the-art theoretical frameworks that extend the current simulation architecture. Instead of relying on brute-force parallel Monte Carlo models, the architecture executes as an SMC Particle Filter. The simulation maintains  independent parallel graph worlds, representing "Particles." As live open-source data—ranging from GDELT event streams to World Bank demographic APIs—enters the system, the particle filtering algorithm recalculates the importance weights of each parallel world. Trajectories that diverge from the hard empirical data are systematically culled, while particles that correctly track the unfolding geopolitical state are mutated and replicated. Every theory detailed herein is strictly translatable into deterministic or probabilistic mathematics, completely avoiding subjective human-in-the-loop scoring or the use of large language models as direct agents within the simulation loop.
1. Joshua Epstein & Generative Social Science
The Theorist & The Core Concept
Joshua Epstein’s framework, formalized in his seminal work Agent_Zero: Toward Neurocognitive Foundations for Generative Social Science, introduces a mathematically rigorous, triadic model of agent behavior.1 Epstein departs from purely rational-actor frameworks and standard behavioral imitation models by endowing software agents with distinct, interacting affective (emotional), cognitive (deliberative), and social (contagion) modules.1 The core conceptual thesis is that macroscopic collective phenomena—spanning fields such as social conflict, public health, financial panics, and civil violence—emerge dynamically from the localized interaction of these neurocognitively grounded software agents.1 Epstein’s model operationalizes the intuition that human behavior in high-stress environments is driven heavily by associative fear conditioning, bounded cognitive assessments, and the inescapable influence of surrounding social networks.7
The Mathematical / Algorithmic Thesis
The Agent_Zero mathematical architecture calculates an individual actor’s disposition to take a specific, irreversible action (such as participating in a violent protest or initiating a conflict) through the dynamic summation of three variables. An action  is modeled as a Boolean output, triggering if the total disposition  exceeds a specific internal activation threshold .7
The total disposition equation is structured as . The affective module, , is explicitly modeled using the Rescorla-Wagner equations for classical fear conditioning.4 The Rescorla-Wagner update rule is defined as , where  represents the agent's innate learning rate,  represents the salience of the stimulus, and  is the actual environmental threat observed at time .4 The cognitive module, , represents a localized probabilistic risk assessment.5 Rather than assuming agents have perfect global information,  is calculated through an imperfect statistical sampling of threats strictly within the agent's observable spatial network, modeling the known cognitive biases identified by Tversky and Kahneman.3
The social module, , mathematically formalizes the contagion of disposition from connected neighbors.8 This is not mere behavioral imitation, but an aggregation of the internal states of surrounding actors. The social component is calculated as , where  represents the specific edge weight mapping the trust or influence between agent  and neighbor  within the network structure.
Variable
Definition
Role in Particle Filter Architecture

Affective Fear State
Updates dynamically based on real-world threat events (e.g., GDELT violence tracking).

Cognitive Risk Assessment
Localized probability of success or survival calculated from the Neo4j spatial graph.

Social Contagion
Aggregates the internal  and  states of connected neighbors using graph traversal.

Learning Rate & Salience
Static or slowly mutating agent properties defining susceptibility to trauma or propaganda.

Activation Threshold
The mathematical tipping point at which the agent commits to overt action.

The ABM Particle Filter Implementation Plan
To integrate the Agent_Zero framework into the Neo4j and Python/Mesa Sequential Monte Carlo architecture, the graph database must store the precise neurocognitive states of each agent. Each agent node requires dynamically updated float properties mapping to .affect_v, .cognition_p, .learning_rate_alpha, and .activation_threshold_tau. The relationships between agents, typed as ``, must contain a dynamic float weight property .omega representing the susceptibility to emotional contagion across that specific tie.
During the SMC data assimilation step, live open-source data defining the environmental threat parameter  streams into the parent model. If a real-world event occurs—such as a localized state crackdown detected via NLP parsing of news wires—this threat metric is globally updated. All particles simulate their agents updating their internal Rescorla-Wagner equations. The Particle Filter calculates the likelihood of each particle's internal state by comparing the simulated aggregate protest volume against the empirically observed real-world protest volume. Particles where agents failed to reach their activation threshold  due to under-parameterized emotional contagion networks are assigned lower importance weights and culled. Particles that correctly mirror the cascading violence are preserved and replicated.

Python


import numpy as np
import mesa
from scipy.stats import norm

class AgentZero(mesa.Agent):
    def __init__(self, unique_id, model, alpha, beta, tau):
        super().__init__(unique_id, model)
        self.alpha = alpha
        self.beta = beta
        self.tau = tau
        self.v_t = 0.0  # Affective state initialized
        self.p_t = 0.0  # Cognitive state initialized
        self.action = 0

    def step_rescorla_wagner(self, lambda_t):
        # Mathematical update of affective fear conditioning based on environmental threat
        self.v_t = self.v_t + self.alpha * self.beta * (lambda_t - self.v_t)

    def calculate_social_contagion(self):
        # Cypher equivalent: MATCH (a)-->(b) RETURN sum(r.omega * (b.v_t + b.p_t))
        social_s = 0.0
        neighbors = self.model.grid.get_neighbors(self.pos, include_center=False)
        for neighbor in neighbors:
            omega = self.model.network.get_edge_weight(self.unique_id, neighbor.unique_id)
            social_s += omega * (neighbor.v_t + neighbor.p_t)
        return social_s

    def step(self):
        # Assimilate environmental threat from live data stream via parent model
        lambda_t = self.model.current_environmental_threat 
        self.step_rescorla_wagner(lambda_t)
        
        # Calculate local risk assessment (cognition)
        self.p_t = self.model.get_local_risk(self.pos) 
        
        # Aggregate total disposition
        s_t = self.calculate_social_contagion()
        d_t = self.v_t + self.p_t + s_t
        
        # Binary action trigger based on specific threshold
        self.action = 1 if d_t > self.tau else 0

def update_particle_weight(particle_model, real_world_protest_volume):
    simulated_volume = sum([agent.action for agent in particle_model.schedule.agents])
    variance = particle_model.variance_param
    # Likelihood modeled as a Gaussian density comparing simulation to real-world data
    likelihood = norm.pdf(real_world_protest_volume, loc=simulated_volume, scale=variance)
    particle_model.weight *= likelihood


2. Peter Turchin & Structural-Demographic Theory
The Theorist & The Core Concept
Peter Turchin’s Cliodynamics and the associated Structural-Demographic Theory (SDT) offer a highly deterministic, macroscopic explanation for the cyclical outbreaks of severe political instability, civil war, and state collapse.10 Originating from the historical sociology of Jack Goldstone, Turchin expanded SDT by translating historical qualitative patterns into rigorous differential equations and dynamical models.10 The framework posits that complex societies are influenced by long-term demographic and economic feedback loops.10 Sustained population growth inevitably leads to labor oversupply, which depresses real wages and generates mass immiseration.15 This dynamic simultaneously creates a "wealth pump" that concentrates capital, leading to a massive expansion in the number of elites.11 Over time, this elite overproduction outstrips the available supply of state power positions, generating fierce intra-elite competition, the fracturing of social cohesion, and the ultimate fiscal exhaustion of the state.11
The Mathematical / Algorithmic Thesis
The mathematical cornerstone of Turchin's model is the Political Stress Indicator (), a composite index that aggregates the structural pressures driving a society toward systemic failure.10 The  index integrates pressures from three distinct societal compartments: the general population, the elites, and the state architecture.11 It is constructed multiplicatively to indicate that instability requires simultaneous failures across these domains.11
The equation is formulated as . The Mass Mobilization Potential () quantifies popular distress.11 It is calculated as , where  is the inverse of the relative wage representing economic misery,  is the urbanization rate which facilitates collective action, and  is the youth bulge representing the proportion of the population highly susceptible to radicalization.11 The Elite Mobilization Potential () captures intra-elite conflict and is modeled as , where  is the inverse relative elite income and  represents the relative proportion of elites within the total population.11 Finally, State Fiscal Distress () is modeled as , representing the sovereign debt-to-GDP ratio multiplied by an ideological metric of public distrust in state institutions.11
SDT Component
Mathematical Formula
Data Assimilation Source
Political Stress Indicator

Aggregate likelihood target for Particle Filter.
Mass Mobilization Potential

World Bank demographics, ILO wage databases.
Elite Mobilization Potential

Gini coefficients, Forbes wealth tracking.
State Fiscal Distress

IMF sovereign debt APIs, GDELT sentiment tracking.

The ABM Particle Filter Implementation Plan
To integrate Turchin's Cliodynamics into the simulation engine, Neo4j must support macro-level structures. The graph should implement regional or state-level Macro-Nodes mapped as (State {id: "Country_X"}). These nodes store and update the aggregate structural variables: .gdp_per_capita, .median_wage, .urbanization_ratio, .youth_bulge, .elite_ratio, and .debt_to_gdp. Micro-agents (the Agent_Zero implementations) map to these Macro-Nodes via hierarchical edges such as or. The micro-agents' cumulative sentiment directly modifies the state's public distrust parameter .
During the SMC Data Assimilation Step, as external APIs stream demographic and economic statistics into the backend, the true macro-variables for relative wages, urbanization, and debt are forced into the Particle Filter.11 The particles then internally simulate the hidden variables, such as elite overproduction rates and shifting ideological trust. When a macro-event unfolds in reality—such as a sudden coup or mass riot tracked by GDELT—the algorithm evaluates every particle's predicted  index. Particles exhibiting a high  that mathematically aligns with the outbreak of the observed violence receive exponentially higher importance weights. Conversely, particles predicting stability in the face of structural collapse are deemed divergent and destroyed.11

Python


class MacroStateNode:
    def __init__(self, wage_rel, urb_ratio, youth_bulge, elite_income_rel, elite_ratio, debt_gdp, distrust):
        self.w_inv = 1.0 / wage_rel
        self.urb_ratio = urb_ratio
        self.youth_bulge = youth_bulge
        self.eps_inv = 1.0 / elite_income_rel
        self.elite_ratio = elite_ratio
        self.debt_gdp = debt_gdp
        self.distrust = distrust

    def compute_psi(self):
        # Turchin's Political Stress Indicator aggregation
        mmp = self.w_inv * self.urb_ratio * self.youth_bulge
        emp = self.eps_inv * self.elite_ratio
        sfd = self.debt_gdp * self.distrust
        return mmp * emp * sfd

def particle_filter_sdt_update(particle, world_bank_data, gdelt_instability_index):
    # Assimilate hard structural data into the particle's state node
    particle.state.w_inv = 1.0 / world_bank_data['relative_wage']
    particle.state.debt_gdp = world_bank_data['debt_to_gdp']
    particle.state.urb_ratio = world_bank_data['urbanization_rate']
    
    # Calculate predicted structural pressure
    predicted_psi = particle.state.compute_psi()
    
    # Map the unbounded Psi value to a probability of instability  using a logistic function
    expected_instability = np.exp(predicted_psi) / (1 + np.exp(predicted_psi))
    
    # SMC Weighting: Penalize the particle based on the divergence from observed instability
    error = abs(expected_instability - gdelt_instability_index)
    particle.weight *= np.exp(-error * 10) 


3. Alex Mintz & Poliheuristic Theory
The Theorist & The Core Concept
Alex Mintz’s Poliheuristic Theory (PH) of Foreign Policy Decision Making establishes a vital operational bridge between cognitive psychology and standard rational choice economics.20 PH addresses the failure of traditional spatial expected utility models to account for seemingly irrational geopolitical actions. The theory posits that national leaders and decision-makers do not execute exhaustive, compensatory cost-benefit analyses across all available dimensions of an issue.23 Instead, they navigate high-stress environments utilizing a strict two-stage decision calculus.21 The fundamental axiom of PH is that domestic political survival overrides all other considerations.24 Any foreign policy option that threatens a leader's domestic political standing is summarily rejected in the first stage of deliberation, regardless of its potential military, economic, or diplomatic utility.24
The Mathematical / Algorithmic Thesis
The mathematical core of Poliheuristic Theory is defined by the strict application of a noncompensatory principle during the first stage of decision-making, followed by a rational analytic expected utility calculation in the second stage.20
Let the set of available geopolitical alternatives be defined as . Let the dimensions of evaluation be defined as , representing factors such as military risk, economic cost, and domestic political capital.26 Let  denote the calculated value of alternative  mapped against dimension .24
In Stage One, the noncompensatory elimination phase, the agent identifies the critical domestic political dimension, denoted as . The agent establishes a political survival threshold, . If the value of an alternative on the political dimension falls below this threshold (), alternative  is entirely eliminated from the choice set.21 This logic is strictly noncompensatory because an extremely high value on the military dimension cannot compensate for a sub-threshold score on the political dimension.24 This yields a reduced subset of acceptable alternatives, .21 In Stage Two, the agent applies standard compensatory expected utility maximization or prospect theory processing to the surviving alternatives to minimize risk and maximize strategic benefit.21
Alternative
Domestic Political (dp​)
Military (dm​)
Economic (de​)
Stage 1 Status (Tp​=−3)
Stage 2 Expected Utility
Option 1: Invade
-5
+10
-2
Eliminated ()
N/A
Option 2: Sanction
-1
+2
-4
Survives
(-1w) + (2w) + (-4*w)
Option 3: Do Nothing
-2
-1
+5
Survives
(-2w) + (-1w) + (5*w)

The ABM Particle Filter Implementation Plan
To integrate Mintz's theories, Neo4j must map complex decision matrices to geopolitical agents. State leader nodes are connected to potential macro-event outcomes via `` edges. These specific edges store float properties for multiple evaluative dimensions, such as .val_political, .val_military, and .val_economic.28 Crucially, the leader agent nodes possess a mutable .survival_threshold attribute, which dynamically shifts based on the Turchin  index of domestic unrest.
During the SMC Data Assimilation Step, live domestic polling data and domestic unrest indices (such as GDELT civil unrest counts) stream into the parent model. The particle filter dynamically updates the noncompensatory political survival threshold () of the leader agents across all particles. If a leader takes a seemingly irrational geopolitical action in the real world—such as launching an economically disastrous war—the particle filter assesses the parallel trajectories. Particles that correctly pruned the "rational" economic alternatives because they accurately simulated the leader's internal domestic vulnerabilities will naturally predict the outbreak of war. These predictive particles receive massive weight multipliers, while particles that relied solely on spatial expected utility algorithms and predicted peace are marginalized.

Python


class PoliheuristicLeader(mesa.Agent):
    def __init__(self, unique_id, model, political_survival_threshold):
        super().__init__(unique_id, model)
        self.T_p = political_survival_threshold
        self.weights = {'military': 0.6, 'economic': 0.4}

    def evaluate_options(self, options_matrix):
        # Stage 1: Noncompensatory Elimination based on political survival
        surviving_options =
        for opt in options_matrix:
            if opt['political'] >= self.T_p:  # Strict cutoff rule
                surviving_options.append(opt)
                
        # Fallback: If all options mean political death, select the least damaging option
        if not surviving_options:
            return max(options_matrix, key=lambda x: x['political'])['id']

        # Stage 2: Analytic Processing / Expected Utility Maximization
        best_option = None
        max_utility = -float('inf')
        
        for opt in surviving_options:
            utility = (opt['military'] * self.weights['military']) + (opt['economic'] * self.weights['economic'])
            if utility > max_utility:
                max_utility = utility
                best_option = opt['id']
                
        return best_option

def particle_filter_mintz_update(particle, domestic_approval_data):
    # Live assimilation of domestic polling data alters the noncompensatory threshold
    for agent in particle.get_leader_agents():
        # A drop in approval strictly raises the threshold for political survival
        agent.T_p = calculate_threshold_from_approval(domestic_approval_data)


4. Duncan Watts & Threshold Models of Cascades on Random Networks
The Theorist & The Core Concept
Duncan Watts fundamentally altered the mathematical approach to modeling collective dynamics through his development of the Threshold Model of Global Cascades on Random Networks.31 Moving decisively beyond simple biological epidemic contagion—which models disease transmission as an independent probability per contact—Watts demonstrated that the propagation of "information cascades" requires a critical threshold of exposure.31 Phenomena such as the outbreak of riots, the adoption of radical political ideologies, and the onset of financial panics are driven by actors who constantly monitor their environment. Watts established that network heterogeneity, specifically the degree distribution and the existence of a percolating "vulnerable cluster," strictly determines whether a small localized perturbation will dissipate immediately or trigger a catastrophic global macro-shock.32
The Mathematical / Algorithmic Thesis
In the Watts cascade model, an individual node  possessing a specific network degree  changes its state (activates or rebels) if and only if a critical fraction of its direct neighbors, denoted as , are currently active.31
Let  represent the binary state of connected neighbor . Node  activates if the mathematical condition  is met.31 Watts defines a node as highly "vulnerable" if its internal fractional threshold  is low enough that exposure to a single active neighbor is sufficient to trigger its own activation, expressed formally as .32
Using a generating function mathematical framework, Watts defines the global cascade condition. A global macro-shock occurs if and only if the expected number of vulnerable neighbors connected to a vulnerable node strictly exceeds 1, allowing the contagion to branch indefinitely.32 The formal cascade condition is defined as , where  is the probability that a node of degree  is structurally vulnerable, calculated as .32
Cascade Metric
Definition
Mathematical Bounding
Agent Degree ()
Number of edges connecting an agent to neighbors.
Extracted via Neo4j topological degree queries.
Fractional Threshold ()
The ratio of active neighbors required to trigger action.
Assigned probabilistically during particle initialization.
Vulnerable Node
A node activated by a single neighbor.

Global Cascade Window
The state where a single spark can consume the network.


The ABM Particle Filter Implementation Plan
Integrating the Watts Threshold Model requires strict tracking of network topology. Every micro-agent node in the Neo4j backend requires a .degree property, an .active_state boolean flag, and a dynamically assigned .fractional_threshold.36 Because threshold checking is inherently a graph traversal problem, the cascade sequence is highly optimized for Graph Databases. The activation update step translates natively to an automated Cypher execution: MATCH (n)-->(m) WHERE m.active_state = true WITH n, count(m) AS active_neighbors WHERE (tofloat(active_neighbors) / n.degree) >= n.fractional_threshold SET n.active_state = true.
During the SMC Data Assimilation Step, when live open-source event data reports the exact location of initial protest seeds, the particle filter initializes those specific geographic nodes to an active state () across all parallel trajectories. The particles then mathematically execute the Watts fractional cascade over subsequent simulation turns. As the empirical size of the real-world protest expands or contracts over days, the particle filter calculates the error delta between the real cascade size and each particle's predicted vulnerable cluster expansion.36 The algorithm updates importance weights accordingly, aggressively culling particles whose generated network topologies failed to match the boundaries of the real-world cascade window, and replicating those that accurately projected the tipping point.33

Python


class WattsCascadeAgent(mesa.Agent):
    def __init__(self, unique_id, model, fractional_threshold):
        super().__init__(unique_id, model)
        self.phi = fractional_threshold
        self.state = 0 # 0 = inactive, 1 = active / rebelling
        self.degree = 0

    def step(self):
        if self.state == 1:
            return # Node is already part of the cascade
            
        neighbors = self.model.grid.get_neighbors(self.pos, include_center=False)
        self.degree = len(neighbors)
        if self.degree == 0:
            return
            
        # Count the absolute number of active neighbors
        active_neighbors = sum([1 for n in neighbors if n.state == 1])
        fraction_active = float(active_neighbors) / self.degree
        
        # Execute Watts fractional threshold activation logic
        if fraction_active >= self.phi:
            self.state = 1

def particle_filter_cascade_culling(particles, real_time_protest_size):
    for p in particles:
        simulated_size = sum([a.state for a in p.schedule.agents])
        
        # Calculate divergence between predicted vulnerable cluster size and real-world data
        error = abs(simulated_size - real_time_protest_size)
        
        # Update particle weight via Gaussian kernel
        p.weight *= np.exp(-0.5 * (error**2) / p.variance)


5. Martin Nowak & Evolutionary Dynamics on Graphs
The Theorist & The Core Concept
Martin Nowak’s Evolutionary Graph Theory establishes the mathematical baseline for modeling how institutional traits, state control, and political ideologies spread through structured spatial topographies.39 Classical evolutionary game theory traditionally assumes well-mixed, homogeneous populations where any actor is equally likely to interact with any other. Nowak introduces the Moran Process on Graphs to prove that the underlying topological structure of a population strictly dictates the fixation probability—the mathematical likelihood that a mutant strategy, revolutionary ideology, or invading military force completely overtakes the resident baseline population.39 This framework is paramount for predicting territorial shifts in asymmetric conflicts and the propagation of institutional decay.43
The Mathematical / Algorithmic Thesis
The Moran Process evaluates network evolution utilizing two highly distinct mathematical update rules: Birth-death (Bd) and death-Birth (dB).39 In the context of geopolitical simulations, the "birth" action corresponds to the projection of power or the propagation of an ideology, whereas "death" corresponds to institutional collapse, territorial loss, or regime change.
Let a defined graph have  total nodes. Resident nodes possess a baseline fitness of ; mutant nodes (representing the new ideological faction) possess a modified fitness of .39 Under the Birth-death (Bd) rule, an individual node is probabilistically chosen to reproduce proportional to its fitness factor, and its offspring randomly replaces a connected neighbor.39 Conversely, under the death-Birth (dB) rule, an individual node is first chosen uniformly at random to collapse (die). The surrounding neighbors then fiercely compete to project their power and fill the structural vacuum, proportional to both their internal fitness and their connecting edge weights.43
The mathematical formulation calculating the exact probability  that an adjacent node  replaces the collapsed node  under the dB update rule is structured as 43:

Where  represents the fitness multiplier of  (military or economic strength), and  represents the directed edge weight indicating geographic proximity or logistical power projection.43
Moran Update Rule
Geopolitical Analog
Mathematical Execution
Birth-death (Bd)
Aggressive Territorial Expansion
Select node proportional to fitness . Target random neighbor.
death-Birth (dB)
Power Vacuum Consolidation
Select random node to collapse. Neighbors compete via  logic.

The ABM Particle Filter Implementation Plan
Integrating Evolutionary Graph Theory into the Neo4j architecture necessitates mapping State, City, or Institutional nodes against ideological attributes. These spatial nodes possess a discrete .ideology_type property and a float .fitness_r property, which represents asymmetric power advantages such as technological superiority or economic reserves. Connecting edges possess a .logistical_weight property.
During the SMC Data Assimilation Step, the simulation operates amidst ongoing proxy conflicts or civil wars. The engine simulates the shifting boundaries of ideological and territorial control via the Moran dB process. When open-source geospatial data feeds—such as maps from the Institute for the Study of War (ISW) or Wikidata territorial bounding boxes—reveal that a specific city or province has fallen in reality, the particle filter updates the true state matrix. Particles that correctly calculated the spatial fixation probabilities based on the accuracy of their graph topology receive increased importance weights.44 Particles modeling incorrect spread trajectories due to flawed fitness assumptions are culled, allowing the swarm to adapt to the true ground conditions.

Python


import random
import numpy as np
import mesa

class MoranGeopoliticalNode(mesa.Agent):
    def __init__(self, unique_id, model, ideology, fitness):
        super().__init__(unique_id, model)
        self.ideology = ideology # 0 = Incumbent State, 1 = Insurgent Faction
        self.fitness = fitness   # The 'r' parameter

def step_death_birth_moran(model):
    # Step 1: Institutional Death - Select a node uniformly at random to collapse
    nodes = model.schedule.agents
    dead_node = random.choice(nodes)
    
    # Step 2: Birth / Power Projection - Neighbors compete to fill the vacuum
    neighbors = model.grid.get_neighbors(dead_node.pos, include_center=False)
    
    if not neighbors:
        return
        
    # Calculate total competitive pressure on the vacuum node
    denominator = sum([n.fitness * model.network.get_edge_weight(n.unique_id, dead_node.unique_id) 
                       for n in neighbors])
    
    # Map probability distribution for each competing neighbor
    probabilities = [(n.fitness * model.network.get_edge_weight(n.unique_id, dead_node.unique_id)) / denominator 
                     for n in neighbors]
    
    # Determine the victor based on weighted probabilities
    victor = np.random.choice(neighbors, p=probabilities)
    
    # The collapsed node is absorbed into the victor's ideological sphere
    dead_node.ideology = victor.ideology
    dead_node.fitness = victor.fitness


6. Damon Centola & Complex Contagion Dynamics
The Theorist & The Core Concept
Damon Centola's rigorous mathematical framework of Complex Contagion addresses the profound limitations of standard biological epidemic models when attempting to simulate the spread of highly risky, costly, or controversial social behaviors.48 Standard models assume that behavior spreads like a virus—a "simple contagion" requiring only a single contact for transmission. However, the adoption of radical political ideologies, participation in illegal strikes, or the execution of uncoordinated civil violence requires extensive social reinforcement from multiple, independent sources.48 Centola's mathematical proofs demonstrate that Mark Granovetter's universally cited "Strength of Weak Ties" theory actively fails when applied to complex contagions.49 Instead of spanning across isolated weak ties, the spread of high-risk geopolitical behavior requires "wide bridges" characterized by densely clustered overlapping networks.49
The Mathematical / Algorithmic Thesis
Centola strictly defines a behavior as a complex contagion if the threshold for behavioral adoption  is strictly greater than 1 ().48 In order for a dangerous social movement or ideological shift to successfully transmit across a structural network bridge connecting two distinct communities, the bridge width  must mathematically satisfy the condition .49 Here,  is the number of independent, redundant ties connecting a vulnerable individual to the active, mobilized community.49
If an agent  is connected to a remote mobilized network cluster via a single "weak tie" (meaning the bridge width ), but their personal behavioral threshold , the mathematical probability of the behavior cascading across that tie is strictly 0.49 Consequently, the diffusion probability  of a revolution traversing through a geographic network topology is firmly bounded by the local clustering coefficient .49 Dense, highly clustered overlapping ties provide the necessary redundant reinforcement signals required to overcome the risk aversion of the agents.49
Contagion Type
Characteristics
Network Requirement
Simulation Application
Simple Contagion
Requires 1 contact. No social risk.
Weak ties accelerate spread.
Spread of simple news, passive awareness.
Complex Contagion
Requires  independent contacts.
Wide bridges ().
Violent protests, regime defection, radicalization.

The ABM Particle Filter Implementation Plan
Executing Complex Contagion dynamics requires the Neo4j Graph Database to constantly monitor structural topology rather than just isolated node properties. The simulation engine must rapidly calculate the Local Clustering Coefficient and identify multi-edge structural holes. Neo4j Cypher queries handle bridge detection directly: MATCH (a)-->(b) WITH a, count(b) AS width WHERE width >= a.complex_threshold SET a.exposed = true.
During the SMC Data Assimilation Step, the simulation must track the propagation of dangerous social movements by analyzing NLP parsing pipelines feeding from social media and GDELT.50 The model explicitly differentiates between the spread of "awareness" (modeled as a simple contagion crossing weak ties) and the spread of "mobilization" (modeled as a complex contagion requiring clustered ties). Particles that inaccurately allow mobilization behaviors to travel freely across single weak ties will drastically over-predict the geographic spread of riots into adjacent cities. The Particle Filter's likelihood function relies on verifying the spatial constraints of the incoming empirical data, harshly culling any particles that permit complex contagions to violate the  rule, ensuring that simulated revolutions stall appropriately at structural network bottlenecks.

Python


class ComplexContagionAgent(mesa.Agent):
    def __init__(self, unique_id, model, complex_threshold):
        super().__init__(unique_id, model)
        self.T = complex_threshold # Absolute integer threshold for risky behavior (e.g., T = 3)
        self.behavior_adopted = False

    def step(self):
        if self.behavior_adopted:
            return
            
        neighbors = self.model.grid.get_neighbors(self.pos, include_center=False)
        
        # Calculate the number of independent, redundant reinforcement signals
        active_signals = sum([1 for neighbor in neighbors if neighbor.behavior_adopted])
        
        # Complex Contagion logic: Requires wide bridges (active_signals >= T)
        # A single weak tie connection (active_signals = 1) strictly fails if T > 1.
        if active_signals >= self.T:
            self.behavior_adopted = True

def analyze_bridge_width_constraint(model, community_a_nodes, community_b_nodes):
    # Evaluates the structural capacity for a macro-event to cross distinct geographic regions
    bridge_edges = model.network.get_edges_between(community_a_nodes, community_b_nodes)
    
    # If the number of edges is less than the required threshold T, the contagion mathematically halts
    return len(bridge_edges) 


7. Gerd Gigerenzer & Fast-and-Frugal Trees (FFTs)
The Theorist & The Core Concept
Gerd Gigerenzer’s development of Fast and Frugal Heuristics serves as a direct mathematical challenge to the assumption that geopolitical agents have the cognitive or computational capacity to maximize expected utility across endless probabilistic branches in volatile environments.53 In environments characterized by extreme uncertainty and deeply constrained resources, actors rely on Fast-and-Frugal Trees (FFTs).54 FFTs are simple, highly robust algorithms that allow decision-makers to make rapid binary classifications by intentionally ignoring massive amounts of available information.55 By relying on minimal data, FFTs prevent the critical statistical error of overfitting to historical noise, resulting in predictive accuracy that consistently rivals complex multiple regression models and Bayesian networks.53
The Mathematical / Algorithmic Thesis
An FFT is mathematically defined as an asymmetric decision tree utilized exclusively for binary classification problems involving  specific cues (features). A formal FFT possesses exactly  exits; there is exactly one terminal exit for each of the first  cues, and two terminal exits for the final cue.55
FFTs operate mathematically as lexicographic heuristics relying on non-compensatory weights.55 The available environmental cues, defined as , are strictly ordered according to their empirical cue validity, denoted as .59 Cue validity is defined as the mathematical probability of a positive outcome given the presence of a positive cue, expressed as .59
The classification algorithm executes sequentially 53:
Evaluate cue . If the cue matches its exit threshold, make the binary decision and immediately halt the search.
If the condition is not met, evaluate cue . If it triggers its specific exit, decide and halt.
Proceed sequentially until cue  is reached, which forces a final binary classification.
Because the architecture relies entirely on non-compensatory thresholds, a negative signal on the highly valid cue  cannot be outweighed by any mathematical combination of positive signals on subsequent, lower-validity cues.55 This drastically reduces computational overhead within the simulation while matching the performance of complex machine learning algorithms.56
FFT Component
Definition
Role in Agent Logic
Cues ()
Observable environmental data points.
E.g., Military buildup, economic sanctions, riots.
Cue Validity ()
The probability of outcome given the cue.
Dictates the strict lexicographic order of evaluation.
Non-compensatory Search
The inability of lower cues to override higher cues.
Halts computation immediately upon finding an exit.

The ABM Particle Filter Implementation Plan
To embed Fast-and-Frugal heuristics, Neo4j agent nodes must possess a ranked array property representing their specific cue hierarchy, such as .cue_military_presence, .cue_economic_shock, and .cue_regime_stability. Instead of executing computationally devastating Bayesian updates for millions of micro-agents per turn, the agents process localized threats using highly optimized, indexed Cypher queries that instantly traverse only to the first triggered exit node.
During the SMC Data Assimilation Step, the particle filter utilizes incoming real-world macro-data to dynamically recalibrate and reorder the cue validities  across the particle swarm. Every particle tests a slightly different cue hierarchy. If a particular particle's FFT order (e.g., heavily prioritizing economic cues while ignoring military mobilization) fails to accurately predict a localized real-world macro-event (such as an unpredicted military coup reported by GDELT), the particle's importance weight crashes. The particle filter essentially functions as an evolutionary survival mechanism, ensuring that only particles operating with the optimal, empirically validated fast-and-frugal cue hierarchy survive, replicate, and forecast the subsequent phases of the simulation.56

Python


class FastFrugalAgent(mesa.Agent):
    def __init__(self, unique_id, model, cue_hierarchy):
        super().__init__(unique_id, model)
        # cue_hierarchy ordered strictly by empirical validity, e.g., ['military_buildup', 'food_shortage', 'protests']
        self.cue_hierarchy = cue_hierarchy 

    def evaluate_threat_environment(self, environment_data):
        # environment_data is a dictionary mapping cues to boolean signals based on real-world parsing
        
        # FFT Algorithm Execution: Sequential non-compensatory search
        for idx, cue in enumerate(self.cue_hierarchy):
            cue_present = environment_data.get(cue, False)
            
            # For the first m-1 cues, there is a singular exit direction (e.g., Flee/Mobilize)
            if idx < len(self.cue_hierarchy) - 1:
                if cue_present:
                    return 1 # Exit Triggered: Threat recognized, act immediately and halt search
            else:
                # The final cue m forces a strict binary decision to prevent infinite loops
                if cue_present:
                    return 1 # Exit Triggered: Threat recognized
                else:
                    return 0 # Exit Triggered: Environment deemed safe, no action taken
                    
        return 0

def smc_cue_validity_update(particle, real_world_event_data):
    # Evaluate particle's FFT algorithmic accuracy against the empirical data stream
    predicted_mobilization = sum([agent.evaluate_threat_environment(agent.get_local_data()) 
                                  for agent in particle.schedule.agents])
                     
    actual_mobilization = real_world_event_data['total_mobilized']
    
    # Weight particle likelihood based on the predictive accuracy of its internal FFT hierarchy
    particle.weight *= np.exp(-abs(predicted_mobilization - actual_mobilization) / particle.scaling_factor)


Conclusion: Synthesis into the Sequential Monte Carlo Architecture
The translation of these seven distinct theoretical frameworks into executable mathematical models fundamentally upgrades the capacity of the predictive simulation engine. By systematically embedding Epstein’s neurocognitive affect formulas and Centola’s complex contagion limits into the micro-agent logic, the engine moves beyond simple randomized imitation to generate mathematically grounded localized behavior. These micro-behaviors are constrained at the decision-maker level by Mintz’s noncompensatory matrices and Gigerenzer’s fast-and-frugal lexicographic searches, heavily restricting the computational load across the simulation.
Crucially, the aggregate macro-level constraints synthesized from Turchin’s structural-demographic equations, Watts’ cascade generating functions, and Nowak’s evolutionary fixation probabilities establish the rigorous mathematical boundaries required for the Sequential Monte Carlo Particle Filter. As deterministic open-source data streams continuously into the Neo4j backend, the Particle Filter recalculates importance weights using the mathematical likelihoods derived from these very models. Parallel trajectories that violate Turchin's structural thresholds, bypass Nowak's evolutionary probabilities, or fail to adhere to Watts' cascade limits are mathematically isolated and systematically culled. The surviving particles replicate, ensuring the simulation swarm remains perpetually anchored to the true unfolding trajectory of geopolitical events without the necessity of human intervention or subjective LLM hallucination.
Citerade verk
Agent zero : toward neurocognitive foundations for generative social science - Asset Details - MBRL, hämtad maj 17, 2026, https://www.mbrl.ae/web/guest/asset-details?documentId=Library____301538
Agent zero : toward neurocognitive foundations for generative social science - RMIT University Library, hämtad maj 17, 2026, https://researchrepository.rmit.edu.au/discovery/fulldisplay/alma9921935702101341/61RMIT_INST:RMITU
Book Review: Agent_Zero by Joshua Epstein | by Steven Senior | Medium, hämtad maj 17, 2026, https://steven-senior.medium.com/book-review-agent-zero-by-joshua-epstein-8b7399d6a758
Review of Epstein, Joshua M.: Agent_Zero: Toward Neurocognitive Foundations for Generative Social Science (Princeton Studies in Complexity) - JASSS, hämtad maj 17, 2026, https://jasss.soc.surrey.ac.uk/17/4/reviews/2.html
Transcript of Episode 90 – Joshua Epstein on Agent-Based Modeling - The Jim Rutt Show, hämtad maj 17, 2026, https://jimruttshow.blubrry.net/the-jim-rutt-show-transcripts/transcript-of-episode-90-joshua-epstein-on-agent-based-modeling/
Agent_Zero and Generative Social Science - National Academies, hämtad maj 17, 2026, https://sites.nationalacademies.org/cs/groups/dbassesite/documents/webpage/dbasse_175078.pdf
Inverse Generative Social Science: Backward to the Future - JASSS, hämtad maj 17, 2026, https://www.jasss.org/26/2/9.html
AgentZero++: Modeling Fear-Based Behavior - arXiv, hämtad maj 17, 2026, https://arxiv.org/html/2510.05185v1
SFR19_16 Epstein and Chelen.indd - Forums, hämtad maj 17, 2026, https://archives.esforum.de/publications/sfr19/chaps/SFR19_16%20Epstein%20and%20Chelen.pdf
Structural-demographic theory - Wikipedia, hämtad maj 17, 2026, https://en.wikipedia.org/wiki/Structural-demographic_theory
UC Riverside - eScholarship.org, hämtad maj 17, 2026, https://escholarship.org/content/qt6qp8x28p/qt6qp8x28p.pdf
Ages of Discord: A Structural-Demographic Analysis of American History - sackett.net, hämtad maj 17, 2026, https://sackett.net/turchin_ages-of-discord.pdf
Structural-Demographic Theory: What's Next? - Peter Turchin, hämtad maj 17, 2026, https://peterturchin.com/structural-demographic-theory-whats-next/
The Science of Cycles | Mauldin Economics, hämtad maj 17, 2026, https://www.mauldineconomics.com/frontlinethoughts/the-science-of-cycles
Cliodynamics: Decoding History's Patterns with Math to Understand Our Past and Shape Our Future | by S-Ag3 | Medium, hämtad maj 17, 2026, https://medium.com/@ingartsq2/cliodynamics-decoding-historys-patterns-with-math-to-understand-our-past-and-shape-our-future-b374811e3df7
A Structural-Demographic Analysis of American History - Peter Turchin, hämtad maj 17, 2026, https://peterturchin.com/wp-content/uploads/2013/09/SDAAS_Sep17.pdf
The 2010 structural-demographic forecast for the 2010–2020 decade: A retrospective assessment | PLOS One - Research journals, hämtad maj 17, 2026, https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0237458
The 2010 structural-demographic forecast for the 2010–2020 decade: A retrospective assessment - PMC, hämtad maj 17, 2026, https://pmc.ncbi.nlm.nih.gov/articles/PMC7430736/
The Demographic-Wealth model for cliodynamics | PLOS One - Research journals, hämtad maj 17, 2026, https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0298318
Integrating Cognitive and Rational Theories of Foreign Policy Decision Making, hämtad maj 17, 2026, https://www.cambridge.org/core/journals/canadian-journal-of-political-science-revue-canadienne-de-science-politique/article/integrating-cognitive-and-rational-theories-of-foreign-policy-decision-making/69891965B2B21A43EF3DB333F6EB1984
How Do Leaders Make Decisions? : A Poliheuristic Perspective - ResearchGate, hämtad maj 17, 2026, https://www.researchgate.net/publication/236247263_How_Do_Leaders_Make_Decisions_A_Poliheuristic_Perspective
The Poliheuristic Theory of Foreign Policy Decision Making: Experimental Evidence | Request PDF - ResearchGate, hämtad maj 17, 2026, https://www.researchgate.net/publication/315049999_The_Poliheuristic_Theory_of_Foreign_Policy_Decision_Making_Experimental_Evidence
TURKISH FOREIGN POLICY TOWARDS THE CYPRUS CRISES OF 1964, 1967, AND 1974, hämtad maj 17, 2026, https://repository.bilkent.edu.tr/server/api/core/bitstreams/32a2ae95-88d6-458e-89b4-1ef64dfe587d/content
Examining the Role of Identity in Negotiation Decision Making: The Case of Cyprus - ScholarWorks@UTEP, hämtad maj 17, 2026, https://scholarworks.utep.edu/cgi/viewcontent.cgi?article=1090&context=pol_sci_papers
Key Concepts in the Poliheuristic Theory of Foreign Policy Decision Making: A Comparative Examination Using Systemist Theory - MDPI, hämtad maj 17, 2026, https://www.mdpi.com/2076-0760/12/8/446
afases 2019, hämtad maj 17, 2026, https://www.afahc.ro/afases/volum_afases_2019.pdf
CPSA Poliheuristic Paper 070517, hämtad maj 17, 2026, https://www.cpsa-acsp.ca/papers-2007/Tchantouridze.pdf
Applied Decision Analysis: Utilizing Poliheuristic Theory to Explain and Predict Foreign Policy and National Security Decisions - Portland State University, hämtad maj 17, 2026, https://web.pdx.edu/~yesilada/Readings%20Decision%20Theories/Mintz%20-%20Applied%20Decision%20Analysis.pdf
Policy Perspectives on National Security and Foreign Policy Decision Making - Moodle@Units, hämtad maj 17, 2026, https://moodle2.units.it/pluginfile.php/799484/mod_resource/content/1/REDD%20MINTZ%20PolicyPerspectivesonNationalSecurityandForeignPolicyDecisionMaking.pdf
The Decision to Attack Iraq A Noncompensatory Theory of Decision Making - ResearchGate, hämtad maj 17, 2026, https://www.researchgate.net/publication/236270797_The_Decision_to_Attack_Iraq_A_Noncompensatory_Theory_of_Decision_Making
Social contagion modeled on random networks Daniel Cicala - UCR Math, hämtad maj 17, 2026, https://math.ucr.edu/home/baez/mathematical/ACTUCR/Cicala_Social_Contagion.pdf
A simple model of global cascades on random networks - PNAS, hämtad maj 17, 2026, https://www.pnas.org/doi/10.1073/pnas.082090499
Cascades, Tipping Points, and Riots - Cornell Blogs Service, hämtad maj 17, 2026, https://blogs.cornell.edu/info2040/2015/11/16/cascades-tipping-points-and-riots/
A Simple Model of Global Cascades on Random Networks Author(s): Duncan J. Watts Source, hämtad maj 17, 2026, https://www.stat.berkeley.edu/~aldous/260-FMIE/Papers/watts.pdf
A simple model of global cascades on random hypergraphs - arXiv, hämtad maj 17, 2026, https://arxiv.org/html/2402.18850v2
Threshold model of cascades in temporal networks | Request PDF - ResearchGate, hämtad maj 17, 2026, https://www.researchgate.net/publication/228325366_Threshold_model_of_cascades_in_temporal_networks
On Watts' cascade model with random link weights | Journal of Complex Networks, hämtad maj 17, 2026, https://academic.oup.com/comnet/article/1/1/25/509278
The Impact of Heterogeneous Thresholds on Social Contagion with Multiple Initiators - PMC, hämtad maj 17, 2026, https://pmc.ncbi.nlm.nih.gov/articles/PMC4646465/
Martin NOWAK | Professor (Full) | Ph.D | Harvard University, Cambridge | Harvard | Program for Evolutionary Dynamics | Research profile - ResearchGate, hämtad maj 17, 2026, https://www.researchgate.net/profile/Martin-Nowak
Evolutionary graph theory - Wikipedia, hämtad maj 17, 2026, https://en.wikipedia.org/wiki/Evolutionary_graph_theory
A simple rule for the evolution of cooperation on graphs - PMC, hämtad maj 17, 2026, https://pmc.ncbi.nlm.nih.gov/articles/PMC2430087/
The duality of spatial death–birth and birth–death processes and limitations of the isothermal theorem - Royal Society Publishing, hämtad maj 17, 2026, https://royalsocietypublishing.org/rsos/article/2/4/140465/113446/The-duality-of-spatial-death-birth-and-birth-death
Amplifiers of selection for the Moran process with both Birth-death and death-Birth updating - PMC, hämtad maj 17, 2026, https://pmc.ncbi.nlm.nih.gov/articles/PMC11006194/
The Mixed Birth-Death/death-Birth Moran Process (Extended Abstract) - DROPS, hämtad maj 17, 2026, https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITCS.2026.29
[2511.18252] The Mixed Birth-death/death-Birth Moran Process - arXiv, hämtad maj 17, 2026, https://arxiv.org/abs/2511.18252
Amplifiers of selection for the Moran process with both Birth-death and death-Birth updating | PLOS Computational Biology - Research journals, hämtad maj 17, 2026, https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1012008
Evolutionary Graph Theory, hämtad maj 17, 2026, https://www.univ-st-etienne.fr/_attachment/random-graphs-actualite/Josep.Diaz.MoranSurv.pdf?download=true
Complex Contagion in Social Networks: Causal Evi- dence from a Country-Scale Field Experiment - Sociological Science, hämtad maj 17, 2026, https://sociologicalscience.com/download/vol_12/october/SocSci_v12_685to714.pdf
Complex Contagions and the Weakness of Long Ties, hämtad maj 17, 2026, https://repository.upenn.edu/bitstreams/cf6e30c5-211d-4a6c-981b-ca61ea263dcc/download
Complex Contagions: A Decade in Review Douglas Guilbeault, Joshua Becker and Damon Centola* Annenberg School for Communication S, hämtad maj 17, 2026, https://ndg.asc.upenn.edu/wp-content/uploads/2016/01/Guilbeault-and-Centola-Complex-Contagions-A-Decade-in-Review.pdf
Complex Contagions and the Weakness of Long Ties1 | American Journal of Sociology: Vol 113, No 3, hämtad maj 17, 2026, https://www.journals.uchicago.edu/doi/10.1086/521848
Emergent Directedness in Social Contagion - arXiv, hämtad maj 17, 2026, https://arxiv.org/html/2510.06012v1
Homo Heuristicus: Why Biased Minds Make Better Inferences, hämtad maj 17, 2026, https://sites.socsci.uci.edu/~lpearl/courses/readings/GigerenzerBrighton2009_HomoHeuristicus.pdf
Bounded Rationality: the Case of 'Fast and Frugal' Heuristics - Exploring Economics, hämtad maj 17, 2026, https://www.exploring-economics.org/en/discover/bounded-rationality-heuristics/
Fast-and-frugal trees - Wikipedia, hämtad maj 17, 2026, https://en.wikipedia.org/wiki/Fast-and-frugal_trees
FFTrees: A toolbox to create, visualize, and evaluate fast-and-frugal decision trees, hämtad maj 17, 2026, https://ideas.repec.org/a/cup/judgdm/v12y2017i4p344-368_2.html
FFTrees: A toolbox to create, visualize, and evaluate fast-and-frugal decision trees, hämtad maj 17, 2026, https://www.sas.upenn.edu/~baron/journal/17/17217/jdm17217.html
Gerd Gigerenzer - MPG.PuRe, hämtad maj 17, 2026, https://pure.mpg.de/rest/items/item_2102935_7/component/file_2563024/content
Transparent, simple and robust fast-and-frugal trees and their construction - Frontiers, hämtad maj 17, 2026, https://www.frontiersin.org/journals/human-dynamics/articles/10.3389/fhumd.2022.790033/full
FFTrees: A toolbox to create, visualize, and evaluate fast-and-frugal decision trees, hämtad maj 17, 2026, https://pearl.plymouth.ac.uk/psy-research/370/
