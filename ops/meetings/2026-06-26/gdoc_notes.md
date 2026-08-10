# Meeting notes — 2026-06-26

> Pulled from Google Doc **Pixel Agent Weekly - Meeting Notes (Abdoul + Raghav + Amaad + Matt)** on 2026-06-26.
> Source: [1zA6q0mtIGTWwnIo7IRwK1_zgE0X6QwQVKtVYjueJock](https://docs.google.com/document/d/1zA6q0mtIGTWwnIo7IRwK1_zgE0X6QwQVKtVYjueJock/edit)

| 
Attendees:    

Notes


Action items




https://github.com/MaximusAnax/pixel_agent 
Aim for first full run of OpenCUA on Babel 
Error analysis on OSWorld (blockers?)
After getting the trajectories and we have all the data, ask an agent to compute a cost estimate based on input/output tokens for what it would cost to have a frontier model do the error analysis
If ~$25, just proceed. Don’t even ask Matt.
If more expensive, check in with Matt first.
Towards GUI Agents: Vision-Language Diffusion Models for GUI Grounding
Ideas	
Generate grounding labels with an image diffusion model
Stable Diffusion 3 paper: https://arxiv.org/pdf/2403.03206 
Q: If we have an image with a red circle around where to click, how do we find the red circle?
Maybe consider traditional computer vision techniques
Maybe generate some type of shape that is highly unusual (e.g. some very specific pattern that doesn’t appear in standard UIs, but is easy for image generation models to create: houndstooth) 
Mac Sleep commands
Disable sleep: sudo pmset disablesleep 1
Enable sleep: sudo pmset disablesleep 0


 | 
Attendees:   

Notes
Abdoul
Completed PSC Bridges Quick start guide. Babel credentials not created so couldn’t set up.
Tried to serve OpenCUA-7B with vLLM on PSC Bridges-2 (cis260099p, GPU-shared, node v016) for failure analysis, but vLLM won’t start. Two related environment issues:
In py313 conda env, pip install vllm pulled vLLM 0.23 with CUDA 13 libraries. Bridges exposes CUDA 12.6 via module load cuda/12.6.1, so we get: ImportError: libcudart.so.13: cannot open shared object file
Tried creating a new cua-vllm env (Python 3.11) and running pip install vllm==0.12.0 failed because pip tried the source tarball instead of a prebuilt wheel.
SOLUTION: Used vLLM 0.11.0, and it worked fine.
What’s the lab-standard way on Bridges to run vLLM for OpenCUA (conda env name, CUDA module, vLLM version/wheel)? 
Should OSWorld VMs run locally/AWS while inference stays on Bridges/Babel?
Keep everything on bridges/babel
Raghav	
Screenspot and OSWORLD-G good to start from
Experiment results


Hugging face dataset has trajectories already generated
First, take them and run inference on them to categorize the different failure modes.
Then potentially actually generate our trajectories ourselves.
Make sure to look at relevant models (OpenCUA, Kimi, Sonnet 4.5, not old models)
Looking more closely at the model reasoning traces when analyzing trajectories.
Amaad
Babel should have alright storage
Lots of benchmarks and datasets blow up storage in this visual agent field because images are very space intensive.
Grounding (more saturated) vs full agent benchmarks
Depends on what method we are creating: is it specifically a new grounding method or a full end-to-end method? 
One simple method is a good way to go about

Action items
P0: Setup Hermes Agent
Make a Skill.md for ramping up when working on a new idea
Add instructions on how to access meeting docs (Google Workspace CLI) and update regularly. 
Share with the team.
Set up cron jobs to monitor experiments
Run Failure analysis using pre-made prompt
Make an ssh key for babel/bridges that the agent can use to ssh into those remove resources.
P3(later): Auto-research spins up agents working on a problem (Andrej Karpathy’s auto-research)
Potentially adding a prompt to look into literature in the space and help brainstorm




 | 
Attendees:    


Notes 
Updates
Abdoul
Overview of Failure Modes: 
Error Analysis Plan Draft:go
Key question: How do we identify whether an error is a perception and grounding error vs. a cognitive/planning error?
In an VLM as a Judge scenario, give the reference trajectory, the predicted trajectory, the OSWorld metric (i.e. number in [0,1]), maybe include output of tests that gave rise to that metric. 
Ask the VLM to identify why the CUA failed and classify the error into our taxonomy
Use Babel for L40S GPUs
Use different models for the agent and for the judge
CUA: Qwen3.5-VL 0.8B
Judge: Qwen3.5-VL 9B
Existing code
OpenCUA https://github.com/xlang-ai/OpenCUA 
Make sure OpenCUA is using vLLM for serving efficiency
Super excited about this paper: Memory Inception: Latent-Space KV Cache Manipulation for Steering LLMs
My takeaways:
Expanding on all these ideas, 
Ideas
World models for planning in CUA
Problem: how does a world model know what to do in a new piece of software? Maybe allow the world model to explore the software and generate more training data for itself.
Screenshot generation as a method of grounding
Last time: Videos of computer use for scaling up agents (already done: [2603.24440] CUA-Suite: Massive Human-annotated Video Demonstrations for Computer-Use Agents  )
OSWORLD-G https://arxiv.org/pdf/2505.13227	

Action items
Abdoul
Babel quick start guide (understand GPU queues), setting up env on remote machine


Updates
Abdoul + Ragav met on Monday
Reading list 
Abdoul: to plan the failure analysis
Ragav: looking at literature to understand failure modes (Literature analyis)
GUI Grounding might be the key challenge area
GUI-Perturbed https://arxiv.org/pdf/2604.14262 
Spatial reasoning is tough: e.g. click the heading above and to the right of the blue button
Paper addressing this Uground
Understanding icon meanings 
Clutter and density affect 
OCR
Failure over long horizon; number of steps (easy 3-4, medium 4-9, hard 10+)
Planning and reflecting phase can end up taking many more steps than what is required
IDEA: reward effective thinking to make system more effective? Efficient?
Visual context over time
Historical screen shots can be confusing to the model, even if we do include the action history
Do CUAs perform worse when given screenshot context? And if so, why is that?
How are video understanding models trained? Are we even using a model that was trained to understand a sequence of video frames?
Video Understanding with Large Language Models: A Survey
Learning from Online Videos at Inference Time for ComputerUse Agents
IDEA: could we train on these YouTube tutorials for computer use?
Gemma 4 was trained to understand video
Next steps
Abdoul: to plan the failure analysis
Run a small model on a benchmark (and ask an agent to do some error analysis based on the outputs)
Write up paper ideas  (3 per person?)
Amaad
Agentic Trajectory scraping from videos and synthetic augmentation to create new traces. (Are models good enough at modeling computer environments?)
Synthetic RL Environment task generation

Raghav
OSWorld and many benchmark papers have shown that agents can fail in long context and complex scenarios because they are stateless. Why don’t we try to give the agents some memory, not as screenshots, but as a learned GUI state. We can figure out ways to compress the GUIs and give the model this state + the last actions. This might also help with cases when there are sudden ads or pop-ups on screen. The model can look at the previous history and understand that something changed without taking any actions. 
Current models struggle with grounding. This problem might be worse in smaller models. What if we have two models, one for candidate selection and one that actually outputs the action. Separating perception from planning might be more efficient for small models with limited knowledge. There can be a third model as well which can additionally make tool calls like web search in case a documentation needs to be studied.
Can we use RL to teach a model the best way to solve a problem? We will ask the model to predict the state after a possible set of actions and then nudge it to choose the best action. We can supervise the reasoning traces as well to make sure the model is “thinking” correctly.
How about adding a special action that can call another model to reason about the current state. We can have two separate models, one is the main VLM taking all actions and another that has good GUI grounding that can create bounding boxes or reason about the current state. 
Can we have an LLM take the original instruction and enhance it to include some broad level directions and success metrics? A good set of instructions can help improve VLM performance. This was shown in a paper we talk about last week.
Chat & Claude Org Info
Abdoul: andiongu@andrew.cmu.edu for both
Raghav: raghavgupta@cmu.edu 



Updates
Abdoul 
Potential reading into real time strategy game literature. Links in readings doc.
SURA didn’t go through, so redo
Ragav - lit review
Better dataset, better performance in grounding
Errors: related to where to click
Qwen 3B and 7B are the most common models
Amaad
Looking into a novel dataset that has not been trained on by qwen lab, in order to differentiate
Perhaps synthetic data gen
Data augmentation (could rely on paired screenshot + html data)
Could we rely on orthogonal sources of data to better understand the meaning of icons within various application or web settings?
E.g. documentation for Powerpoint
Alt text for webpages
Adaptive test time compute to improve performance of small models (e.g. ReVL recursive approach to grounding is an example of this)
Test time compute outside of the bounds of chain of thought would be a great area to explore for further differentiation.
Icon accuracy typically much worse for models
Potential to pivot into an agentic/text-based approach but specifically focusing on the domain of relying solely on visual input. 
Would have to somehow alter the web to be understandable by text-based models
Question: What is the SOTA for small models on GUI grounding?
(see results below)
Question: What is the SOTA for small models on computer use (pixel based)?
What to read?
OSWorld-Verified(Benchmark being used by frontier labs): 
Let’s verify step by step (Process Reward Models)
What is the state of the art for grounding with a tiny model?
Should we build anything yet?
Take a smaller 1B model and run it on benchmarks to see failure modes
Better understanding exactly where the models are currently failing
Is there a method of analyzing the specific data/performance on benchmarks to pull out insights on key deficiencies? 
Making baselines/choosing which to start using.

Idea generation
If goal is to do anything with post-training, might be difficult with small models, which are def distillation trained
Next steps
Schedule regular check-in meetings for Abdoul and Raghav
Create Google Doc with reading list
Summary of what prior work has identified as the limitations of existing models for CUAs (e.g. is there existing error analysis that we can learn from?)
Look at existing open source CUAs and compare multiple options (if they exist) as to flexibility, applicability to various benchmarks, applicability to different models, etc.
Plan an error analysis of some small VLM on, say, OSWorld-Verified 
Do the error analysis (normally carrying out this analysis would be super costly in terms of human effort, but a good coding agent can probably do this semi-automatically)
Finding existing code that correctly runs benchmarks in order to help decrease the ramp up into error analysis

Side note from Amaad Feb 27, 2026

Key insight: Icon accuracy is the main differentiator (21–72% range). Text is relatively saturated (70–82%).
From Qwen3-VL paper https://arxiv.org/pdf/2511.21631
Qwen3.5 9B: https://huggingface.co/Qwen/Qwen3.5-9B 

Qwen3.5 0.8B https://huggingface.co/Qwen/Qwen3.5-0.8B 
Does NOT mention OSWorld, etc.

Qwen3 0.6B ​​https://huggingface.co/Qwen/Qwen3-0.6B-Base	
Qwen3 1.7B https://huggingface.co/Qwen/Qwen3-1.7B-Base		



Background
https://timdettmers.com/2026/01/27/building-open-coding-agent-sera/	
Moat is pursuing smaller-scale models
Security/privacy incentive for smaller models
Practicalities 
Timeline: 
Compute: Babel (just andrew ids) + PSC Bridges (create accounts here  and send me usernames https://allocations.access-ci.org/)  + Slurm (to read up on)
Abdoul: Completed PSC Bridges Sign up - username: andiongue
Raghav: Completed PSC Bridges Sign up - username: rgupta19
SURA - log hours


Github repo - put usernames here
mgormley
Raghav3003
Amaadmartin 
What research problem to pick first?
Small VLMs for computer use agents (harder to narrow down?)
What is the definition of a small VLM?
A lot existing work is already using 9B QwenVL models (older ones were 7B)
Are there lots of papers using the larger QwenVL models already?
A good laptop could serve a 7B model (maybe not every laptop)
Is 2B small? Is 4B small?
Do we care about “open weights” (e.g. QwenVL) vs “fully open source” (Molmo) distinction?	
This could be used as a way to differentiate this work: “fully open source” CUAs, no reliance on closed-training-source, closed-provenance models
Only interesting in that if we had the ability to train VLMs from scratch, we could look at how aspects of the backbone VLM affect the downstream performance of the CUA
By contrast: QwenVL is sort of a black box; we know the architecture, but we have no idea where the weights came from. So our CUA training might be redundant with its pretraining/mid/post
How to finetune this open weight models:
https://unsloth.ai/docs/models/gemma-4/train
Things we probably don’t yet know enough about to decide how to proceed next:
Details of the CUA benchmarks and where current SOTA methods fail on them
Do small VLMs lead to different kinds of failures that we could fix with better {harness, training, etc.}?
Details of the CUA harnesses eph
Details of CUA training
Streaming inputs for computer use agents (harder to sell?)
What to read?
SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents
OSWORLD: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments
Qwen
Qwen2-VL: Enhancing Vision-Language Model’s Perception of the World at Any Resolution
Qwen3-VL Technical Report



 AI generated project proposal

Project Proposal: Small Visual Agents for Pixel-Only Computer Use
This project investigates whether small vision-language models can become capable computer-use agents when restricted to pixel-only observations and realistic compute budgets, such as edge-device or laptop-scale inference. The central question is whether GUI agents truly require frontier-scale models and privileged UI representations, or whether small VLMs can succeed through better training, agent-loop design, streaming perception, and harness construction.
The first major direction is training small VLM agents for computer-use behavior. Reinforcement learning is a natural fit because the agent can interact with a UI environment, take actions, and receive feedback based on task success. However, the project should likely begin with simpler forms of supervision, such as imitation learning or supervised action prediction from computer-use demonstrations, before moving to RL. Key questions include how to define the action space, how to shape rewards, how much demonstration data is needed, and whether small models can learn useful exploration strategies from pixels alone.
A second direction is streaming visual observation. A pixel-only agent that sees isolated screenshots may miss important temporal information, such as what changed after a click, what disappeared while scrolling, or how a video, game, or dynamic UI evolves. Instead of storing all prior frames in a long Transformer context, the agent may need compressed memory, frame-difference summaries, visual state tracking, or learned temporal representations. This direction is especially relevant for tasks involving scrolling, video watching, games, and UI testing.
A third direction is agent harness design. For small models, the surrounding system may be as important as the model itself. The harness includes the observe-plan-act loop, memory, retries, action abstraction, self-checking, subgoals, and possible tool use. Iterating over harnesses is somewhat analogous to neural architecture search: the model may stay fixed while the system searches for better ways to structure perception, reasoning, and action.
A more exploratory direction is whether a pixel-only GUI agent should be allowed to use code. Code could help the agent crop images, track changes across frames, maintain structured memory, or perform visual preprocessing. This may let a small VLM compensate for limited capacity by delegating parts of perception and reasoning to external tools or subroutines.
Because these ideas compete for attention, the project should initially focus on training small VLM agents for computer-use tasks within a reliable pixel-only evaluation harness. Once a baseline trained agent exists, streaming observation and harness variants can be layered on as controlled extensions.
A possible research agenda is:
Build a baseline small VLM agent with pixel-only observations.
Train it using imitation learning or supervised action prediction from demonstrations.
Develop a reliable harness with task environments, actions, rewards, and success metrics.
Identify tasks where single-frame perception fails.
Compare streaming-memory mechanisms and harness variants.
Explore RL and optional code/tool use if the baseline is stable.
The central hypothesis is that small visual agents can become substantially more capable not only through model scaling, but through better training objectives, interaction environments, memory, and system design. The expected contribution is both a working prototype and a clearer empirical map of which interventions make pixel-only computer use feasible for small VLMs.



Next steps
Get baseline agent with a small model
Q: What is considered small here?
Loop	
Observe
Plan (taken care of by thinking)
Act
Interesting problems:
Model only see frames (e.g. when scrolling, model gets fixed point in times, so doesn’t really see all the information)
Direction: Streaming observations
Necessitates other architectures b/c Transformers would blow up on long contexts
Q: other than scrolling, when else do we care about streaming?
Watch a video
Play a game
Test a UI for a human (already done, but not streamed)
Not solved for frontier models
^^ do we need to work on frontier models for this to actually work or can we pull this off with a small model?
Streaming output tokens (might make things more expensive with the small model)
Ideally we test on edge devices
Training has lots of options, but RL seems like the most natural
\exists dataset of computer use video demonstrations
Iterating on and exploring the space of harnesses
Weirdly similar to neural architecture search (NAS)
How to build?
LangGraph (built on LangChain)
Anthropic agent’s SDK
Google’s agent SDK (maybe too close to Amaad’s work) – ADK 1.0 is Google’s LangChain equivalent
Start with a coding agent
Is there value in allowing a GUI (pixel only, no access to DOM) agent to use code? What are the use cases?
Tool use a la. CodeAct
Recursive Vision Language Models a la RLMs
Akin to subagents in coding agents
