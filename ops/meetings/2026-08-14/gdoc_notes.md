# Meeting notes — 2026-08-14

> Pulled from Google Doc **Pixel Agent Meeting Notes (Abdoul + Raghav + Amaad + Matt)** on 2026-08-14.
> Source: [1zA6q0mtIGTWwnIo7IRwK1_zgE0X6QwQVKtVYjueJock](https://docs.google.com/document/d/1zA6q0mtIGTWwnIo7IRwK1_zgE0X6QwQVKtVYjueJock/edit)

## Tab: Everyone


Progress from last time
Raghav: 
Incorporate human trajectories in LLM as a judge
Use frontier models for OSWorld 
$150 for Opus 5 (high)
2 of 10 tasks failed
July 31: CUA Debug [2608.02643] CUADebug: Diagnosing and Repairing Computer-Use Agent Failures
Very similar to what we were doing in terms of using analyzing failure modes, having a taxonomy, 
Our novelty relative to this would be using human trajectories
NeurIPS example policy on concurrent work: What is the policy on comparisons to recent work? Papers appearing online after March 1st, 2025 are generally considered concurrent to NeurIPS submissions.  Authors are not expected to compare to those.
Abdoul
Investigate a broader swath of related work
CUADebug paper also has CUA Error Bench
Other papers
July 30: How benchmarks mis-score: https://arxiv.org/abs/2607.28367	
Amaad
List of human annotated trajectories for CUA benchmarks:
Questions
Action items for this time
Matt to give OpenAI API access
Idea generation (if using AI to help)
Don’t just ask for ideas, you’re liable to get old ones, or uninteresting ones
Ask a model to critique a specific paper: what would you have done differently, or improved on? 
Refining an existing idea: for example, I want to use an image generation model to markup a screenshot of a GUI in order to aid in reasoning about the interface or to aid in grounding; what are 10 ways I could go about this?
Here’s my idea: _____. What are the 10 papers that most closely relate to this idea and how does each one connect to my idea or limit its novelty?
How to spend your time in the AI-in-Research Age?
You must read papers.
Favor directions with technical depth.
If we write the analysis paper, we need to:
What are our goals?
To create a reusable framework for error analysis of computer use agents (CUAs) based on existing human trajectories (really any gold trajectories are fine) for a benchmark. 
To answer the research question for someone who does not have the resources to do expensive human error analysis: How much do successful (gold) trajectories improve the automated error analysis of a CUA? What properties of a set of successful trajectories influence that improvement?
^^^ has anyone else already answered this question?
Paper showing how to do error analysis without golden traces: Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents

Pick the benchmarks with human trajectories that we want to analyze
For each of the benchmarks that Amaad identified, determine exactly what exists in each of the human “trajectories” (i.e. real browser actions or notes)
Determine to what extent modern CUA work still relies on this benchmark
For each benchmark we choose:
Obtain the gold standard trajectories
If human trajectories are present, use those.
If only human notes about the steps a human would take are present (e.g. OSWorld-Human): get gold standard (AI assisted) trajectories by providing the human notes to a frontier model as it completes the task (gold standard would require that these have 100% success rate)
Use an offline model to get AI trajectories
Evaluate success rate of AI trajectories on the benchmark
Use LLM as a judge to perform error analysis on the AI trajectories by providing the judge with the gold trajectories
Use LLM as a judge to perform error analysis on the AI trajectories WITHOUT providing gold trajectories
Randomly sample some error and perform human error analysis on AI trajectories so that we can compare error agreement rates between human/judge(with human rajectories), human/judge (without gold trajectories), judge (with gold trajectories) / judge (without gold trajectories)
What are the contributions of the above? (DEFINITELY out of date now that we updated the “goal” above)
We provide a new method for performing error analysis of arbitrary AI trajectories using VLM-as-a-judge augmented with human/gold trajectories (at a cost similar to generating the trajectories in the first place)
We provide a taxonomy of error types and analyze N benchmarks (Benchmark A, Benchmark B, Benchmark C) and present a cross-cutting analysis 
For OSWorld, we show how to generate gold standard trajectories from notes about how to complete each task – these gold trajectories can be used in the absence of human trajectories.
Best Matches for Agent ↔ Human Trajectory Comparison
1. OSWorld-Human
Environment: Desktop / OS
Human data: Human-determined reference trajectory for OSWorld tasks
Useful for: Step count, redundant actions, path efficiency, agent/human efficiency ratio
Dataset / Code: https://github.com/WukLab/osworld-human
Paper: https://arxiv.org/abs/2506.16042
Notes: Closest match to our intended analysis; explicitly designed to benchmark CUA efficiency against human trajectories.
2. WebArena — Human Trajectories
Environment: Web
Human data: 179 human trajectories on actual WebArena benchmark tasks
Format: Playwright traces containing actions, HTML state, network traffic, etc.
Useful for: Agent vs. human step count, path efficiency, unnecessary actions, strategy divergence
Direct trajectory data: https://drive.google.com/drive/folders/1NrN_sawtYK2V_uHnmmS8ugmGIKUAsPgt?usp=sharing
Resource page: https://github.com/web-arena-x/webarena/blob/main/resources/README.md
Benchmark repo: https://github.com/web-arena-x/webarena
Notes: One of the strongest non-OSWorld options because these are human executions of benchmark tasks rather than unrelated training demonstrations.
3. VisualWebArena — Human Trajectories
Environment: Multimodal web
Human data: 233 human trajectories, one from each task-template type
Format: Playwright traces with HTML pages, actions, etc.
Useful for: Same analyses as WebArena, with more visually grounded tasks
Direct trajectory data: https://drive.google.com/drive/folders/1S_fDzB1VUTwUphWPKZ0DdjJOAXjGz94g
Benchmark repo: https://github.com/web-arena-x/visualwebarena
Notes: Particularly promising for CUA-style analysis because agents need visual understanding in addition to web navigation. Human success on the released set was ~89%.
4. ClawBench
Environment: Live websites / browser
Human data: Human reference runs for benchmark tasks
Recorded information: Video, screenshots, browser actions, HTTP traffic, and agent messages
Useful for: Agent/human trajectory divergence, strategy comparison, state-transition comparison
Benchmark repo: https://github.com/TIGER-AI-Lab/ClawBench
Dataset: https://huggingface.co/datasets/TIGER-Lab/ClawBench
Paper: https://arxiv.org/abs/2604.08523
Notes: The benchmark's evaluator explicitly compares agent trajectories with human reference trajectories across the recorded evidence layers. Very relevant, although we should verify how conveniently the underlying human reference runs can be bulk-downloaded before committing to it.
5. A3 — Android Agent Arena / AITK
Environment: Android / mobile
Human data: Average of ~3 successful human trajectories for each of 100 benchmark tasks
Annotations: Human-labelled essential-state transitions within trajectories
Useful for: Multiple-human-path analysis, strategy variation, optimal-path estimation, agent divergence from valid human strategies
Toolkit / benchmark: https://github.com/YuxiangChai/AITK
Paper: https://arxiv.org/abs/2501.01149
Notes: Especially interesting because there are multiple valid human trajectories per task rather than a single “gold” path. The public AITK supports human and agent trajectory collection; we should verify whether the authors expose the complete original ~300 human trajectories as a standalone downloadable archive.
Additional Human-Trajectory Datasets
6. OmniGUI
Environment: Smartphone / Android
Human data: 708 expert-demonstrated episodes, 2,572 action steps
Modalities: Screenshots + video + audio + action history
Dataset: https://huggingface.co/datasets/OmniGUI/OmniGUI
Code: https://github.com/omni-gui/OmniGUI
Paper: https://arxiv.org/abs/2605.18758
Notes: More of a step-level action-prediction benchmark than a full interactive OSWorld-style benchmark, but human trajectories are directly available.
7. VideoCUA / CUA-Suite
Environment: Desktop applications
Human data: ~10,000 human-demonstrated tasks across 87 desktop applications
Format: Continuous 30 FPS screen video + millisecond-level mouse/keyboard/action logs
Dataset: https://huggingface.co/datasets/ServiceNow/VideoCUA
Project: https://cua-suite.github.io/
Paper: https://arxiv.org/abs/2603.24440
Notes: Excellent large-scale human trajectory corpus. Particularly useful for measuring detailed temporal behavior, cursor behavior, action sequences, and human interaction patterns.
8. UI-Vision
Environment: Desktop
Human data: Human demonstrations with action trajectories, UI labels, bounding boxes, clicks, drags, and keyboard input
Coverage: 83 software applications
Repo: https://github.com/uivision/UI-Vision
Project: https://uivision.github.io/
Paper: https://arxiv.org/abs/2503.15661
Notes: Primarily designed for offline grounding/action-prediction evaluation rather than interactive end-to-end task completion.
9. Mind2Web
Environment: Web
Human data: 2,350 tasks across 137 websites with crowdsourced/manual action sequences
Dataset: https://huggingface.co/datasets/osunlp/Mind2Web
Repo: https://github.com/OSU-NLP-Group/Mind2Web
Project: https://osu-nlp-group.github.io/Mind2Web/
Notes: Includes full traces/snapshots and human action sequences, but evaluation is primarily offline rather than executing an agent and human from the exact same reproducible environment state.
10. WebLINX
Environment: Web
Human data: ~2,300 expert human demonstrations / ~100K interactions
Dataset: https://huggingface.co/datasets/McGill-NLP/WebLINX
Repo: https://github.com/McGill-NLP/weblinx
Project: https://mcgill-nlp.github.io/weblinx/
Notes: Human demonstrations are directly exposed, and WebLINX is now integrated into BrowserGym, which could make agent↔demonstration comparisons easier.
11. Android in the Wild (AITW)
Environment: Android
Human data: ~715K human demonstration episodes covering ~30K unique instructions
Dataset / Code: https://github.com/google-research/google-research/tree/master/android_in_the_wild
Paper: https://arxiv.org/abs/2307.10088
Notes: Extremely large human demonstration dataset containing screens, actions, precise gestures, and natural-language instructions. Better suited to large-scale behavioral analysis than apples-to-apples interactive benchmark comparison.
12. WebChain
Environment: Real-world websites
Human data: 31,725 human-annotated trajectories / ~318K interaction steps across 428 domains
Annotations: Screenshots, HTML/AX-tree state, action types, coordinates, bounding boxes, selectors, XPath, timestamps, etc.
Dataset: https://huggingface.co/datasets/webagentlab/webchain
Repo: https://github.com/sicheng-fan/WebChain
Paper: https://arxiv.org/abs/2603.05295
Notes: Probably one of the most interesting datasets for large-scale analysis of “what does a human trajectory look like?” It includes a 150-trace evaluation subset in addition to the larger training corpus.
13. PC Agent-E Human Trajectories
Environment: Windows / desktop
Human data: 312 human-annotated computer-use trajectories
Dataset: https://huggingface.co/datasets/henryhe0123/PC-Agent-E
Repo: https://github.com/GAIR-NLP/PC-Agent-E
Paper: https://arxiv.org/abs/2505.13909
Notes: Useful desktop human demonstration data, but the 312 trajectories are training data and should not be treated as human reference trajectories for the 141 WindowsAgentArena-V2 benchmark tasks.
Suggested Priority for Our Project
Tier 1 — direct human ↔ agent benchmark comparison
OSWorld-Human
WebArena Human Trajectories
VisualWebArena Human Trajectories
ClawBench
A3
Tier 2 — useful for extending trajectory metrics / validating human behavior patterns6. OmniGUI7. VideoCUA / CUA-Suite8. WebChain9. Mind2Web10. WebLINX11. AITW12. UI-Vision13. PC Agent-E


TODO:
Abdoul will read the space of other benchmarks besides OSWorld and determine whether existing error analysis on those benchmarks would render our idea for error analysis not novel
Run OSWorld analysis
Get “human” traces: Run OSWorld with a frontier model that looks at the human notes from OSWorld-Human and see how many it passes in that case (do we get 100%? If not why not?)

 everyone
Meetings with Abdoul + Raghav (see below and tab)
Directions
OSWorld error analysis
Release a (proper) OSWorld-Human dataset with actual trajectories
PROBLEM: websites / software will drift and then they won’t be valid anymore
Problem: frontier models are evaluated on OSWorld v2.0, so is this benchmark still relevant?
Is this only relevant to small models if frontier models don’t really have many errors
Better CUA (e.g. generation based)
Better CUA (e.g. small model)
Now that we have the environ for OSworld + a grounding model
How much farther to…
A) use a frontier model
B) use a frontier model that looks at the human trajectories
C) use <insert favorite local model> instead
Other benchmarks?
https://arxiv.org/pdf/2412.14161 TheAgentCompany
https://arxiv.org/abs/2510.22780v2  How Do AI Agents Do Human Work? Comparing AI and Human Workflows Across Diverse Occupations
WebArena might have human trajectories
 |
Attendees:  

Notes
Updated the website by combining Abdoul and Raghav’s original viewers
Ran OSWORLD using OSWORLD-human dataset as guide
Used UITARS-72B as the grounding model: achieves a success rate of 60/361 tasks
There are many different errors that prevent the creation of gold labels
incomplete human steps in OSWORLD-human (the instructions ask the model to type something in a search bar but never instructs the model to press enter)
model moves on to the next action while the screen is being loaded from the previous action
OSWORLD initialization error where the initial environment has not been loaded properly.
Action items
Abdoul 
Improve judge calibration based on gold labels for 5 specific task that meet the following criteria:
HumanAgent succeeded in task
OpenCUA 7b and 3b both failed task
Judge made a conclusion on what failure modes and steps
Raghav
Dive deeper into human agent
find a method of transforming human trajectories into more accurate instructions that lead to higher human agent success rate
Figure out initialization bugs/ osworld benchmark issues that lead to hanging states and such (i.e., Why is chrome not opened on setup?)




From Monday meeting
Traces are from OpenCUA-3B and OpenCUA-7B
Judge over the traces is Sonnet-4.6
OSWorld-Human is not folded in
TODO:
OSWorld evaluation script should generate some information about why a trace succeeded or failed. This should be visible to a human alongside the traces. It should also be given to the Judge (probably both the task description JSON file, AND the functions that describe what these different things do, e.g. what is “is_expected_tabs” For example, some of these are defined in https://github.com/xlang-ai/OSWorld/tree/main/desktop_env/evaluators/metrics )
OSWorld-Human traces need to be visible alongside the OpenCUA traces
Need to create an “Oracle Agent” that can run in OpenCUA and carry out the actions taken by a human so that we can generate a screenshot for every step
Consolidate good features from HTML annotation tools (Raghav and Abdoul each have one)
Identify which OSWorld task ID you’re looking at
Use a canonical set of tasks in a canonical order
Include the real task description from the task JSON
Support multiple failure modes (possibly ordered as in Abdoul’s setup)
Clicking on Image should show a much larger version of the image on the screen, that can be clicked away.
Show the thinking trace and the actual actions taken
Think carefully about how to space efficiently present BOTH the AI trace and the human trace side-by-side. Maybe optionally show only images and no text. 
Include a “failing step” integer, identified by a human
Default to hiding the reasoning trace, and then click to reveal
Always show the action taken
Left hand side navbar that shows each task, with its category, prompt, number of steps
Manual annotation
Pick a specific set of, say, 10 traces
Raghav to manually annotate those
Abdoul to manually annotate those
Compute inter-annotator agreement between various pairs (human1/human2, human1/judge, human2/judge)
Task ID

Example task:
Task ID for test: 06fe7178-4491-4589-810f-2e2bc9502122
https://github.com/xlang-ai/OSWorld/blob/main/evaluation_examples/examples/chrome/06fe7178-4491-4589-810f-2e2bc9502122.json 

{
  "evaluator": {
    "func": "is_expected_tabs",
    "result": {
      "type": "open_tabs_info"
    },
    "expected": {
      "type": "rule",
      "rules": {
        "type": "url",
        "urls": [
          "https://www.lonelyplanet.com",
          "https://www.airbnb.com",
          "https://www.tripadvisor.com"
        ]
      }
    }
  }
}

 | 
Attendees:    

Notes
OSWorld-Human https://arxiv.org/pdf/2506.16042 
Error analysis: https://arxiv.org/pdf/2606.31270 
Idea
Give the Judge both the agent and human trajectory 
Ask it to select all failure modes that apply to the agent trajectory (rather than the primary / secondary approach)
Both Raghav and Abdoul manually annotate some failures (pick just one OpenCUA model) and compare: (1) inter-annotator agreement between Judge and (each) human and (2) inter-annotator agreement between human A and human B
Agree on how to share trajectories (i.e. common data format)
ChatGPT Initial Research into the space. Relevant papers to be added to reading list


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


published
ours
7B ScreenSpot V2 (1,272 samples)
88.8
88.7
7B OSWorld-G (564 samples)
31.4
34.8
32B ScreenSpot V2 (1,272 samples)
87.0
91.5
32B OSWorld-G (564 samples)
46.5
48.8

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

Qwen3.5-9B
Qwen3.5-4B
ScreenSpot Pro
65.2
60.3
OSWorld-Verified
41.8
35.6
AndroidWorld
57.8
58.6

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



## Tab: Raghav + Abdoul

 | 
Attendees:  

Notes
Raghav working on getting human trajectory screenshots from OSWORLD Human datatset via a benchmark environment
Abdoul started editing html and judge logic. 
Open questions:
How might we update our taxonomy
Should we prioritize failure modes based on:
Step of occurrence(earlier = more important)
Our own refined prioritization function(to be designed more intentionally)
Impact(ie. How many downstream failures could be tied back to this one) 
Action items
Finish gathering screenshots of human trajectories, then merge into repo. 
Start with pilot trajectories. Path: errorAnalysis/data/review_packets/pilot_taxonomy_paired_20260703/taxonomy_discovery_labels.csv
Refining judge logic to incorporate both human and model screenshots per step in trace, to refine the judge’s assessment.
Reading more into failure analysis papers to see what ways of categorizing failures exist
