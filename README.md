# Jev-in-the-Loop

**English** · [简体中文](README_ZH.md)

### Faster decisions. Faster progress.

**Jev-in-the-Loop explores how Jev can accelerate tasks that rely on LLM decision-making.** From choosing the next action to moving a workflow forward, we bring Jev into the decision loop to help agents turn intent into results faster.

Our focus goes beyond the browser. The bigger question is: **which decisions can Jev take on to make the whole task faster?**

Our first application: **ultrafast browser interaction, right inside Codex.** Codex understands the task and prepares the inputs. Jev quickly selects the next action, and the plugin executes it in local Chrome. Searches, clicks, typing, and navigation flow from one step to the next.

**Already using Codex? Just add Jev.** No additional text-generation model to configure. No extra OpenRouter or other text-model API key.

[Watch the demos](#from-a-prompt-to-the-page-you-want) · [Get started](#get-started) · [Installation guide](plugins/jev-browser-plugin/README.md#install-in-codex) · [Contribute](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/CONTRIBUTING.md)

## From a prompt to the page you want

<img src="docs/media/hero-browser.png" alt="Jev-in-the-Loop: Browser — our first module" width="100%" />

### One prompt. Ready to book.

> Find hotels in Kunming, Yunnan, for two adults, checking in October 13 and out October 14.
> Choose a room and open the booking form. Leave the final confirmation to me.

Change the destination, search hotels, explore the details, and select a room. A sequence of clicks becomes one continuous flow, stopping at the booking form for you to take over.

<a href="https://github.com/user-attachments/assets/a40ab93c-341f-4fbd-adcc-23bac8d92273"><img src="docs/media/demo-hotel.gif" alt="Ctrip hotel search and booking-page demo at 3× playback, with a source-time counter" width="100%" /></a>

[Watch the original MP4](https://github.com/user-attachments/assets/a40ab93c-341f-4fbd-adcc-23bac8d92273) · **3× playback** · Timer shows recording elapsed time.

### From curiosity to a course

> Search Bilibili in English for Stanford CS336 and open the first video.

Enter the query, submit the search, and open the course. From something you want to learn to the video in front of you.

<a href="https://github.com/user-attachments/assets/0a7e59a4-65af-4f65-9d15-17ac95641864"><img src="docs/media/demo-course.gif" alt="Bilibili search for Stanford CS336 and opening the first video at original speed" width="100%" /></a>

[Watch the original MP4](https://github.com/user-attachments/assets/0a7e59a4-65af-4f65-9d15-17ac95641864) · **1× playback** · Timer shows recording elapsed time.

No need to spell out every click. Say what you want to accomplish, and let the actions follow.

## Fewer clicks for you. More getting done.

**No extra model stack.**

Codex prepares search terms, destinations, and dates. Jev selects actions and inputs based on the page. Keep using your existing Codex setup—just configure a TypeSafe API key for the plugin.

**Stay in Codex.**

Install the plugin and give it a task. No separate workspace or second assistant to switch to.

**Not just fast clicks. Fast workflows.**

Search, select, scroll, and navigate within a single plugin call. Jev makes the next decision based on the current page; the execution loop observes the result and moves on. Speed should help finish the task, not just one click.

**Stop where you choose.**

Open video results, reach a hotel booking form, or leave a page ready to explore. You set the goal—and decide when to take over.

## Give it a task

Find something to learn:

```text
Use Jev to search Bilibili in English for Stanford CS336 and open the first video.
```

Prepare a trip:

```text
Use Jev to find hotels in Kunming on Ctrip for October 13–14, one room, two adults.
Open a hotel, choose a room, and stop at the booking form. Do not submit an order.
```

Start with a browser task you find yourself doing by hand.

## Get started

You'll need **Codex, Chrome**, and a **TypeSafe API key**. **uv** manages the local runtime, including Python and the plugin's dependencies.

```sh
git clone https://github.com/Tongyun1/Jev-in-the-Loop.git
cd Jev-in-the-Loop/plugins/jev-browser-plugin
```

Follow the [installation guide](plugins/jev-browser-plugin/README.md#install-in-codex) to configure your key, connect Chrome, and install the plugin. Then open a new Codex task and say: **“Use Jev to…”**

## More decisions. More possibilities.

The browser is our first application, not the boundary of the project. We want to explore other LLM-driven decisions, such as tool selection and workflow branching, and study where Jev can help existing agents.

Start with real tasks. Test speed and task completion through reproducible experiments. Turn what works into usable modules.

Have a task you'd like it to take on? [Tell us](https://github.com/Tongyun1/Jev-in-the-Loop/issues). Interested in the direction? **Star the repo** and follow what comes next.

---

[Development guide](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/CONTRIBUTING.md) · [Security & privacy](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/SECURITY.md) · [MIT License](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/LICENSE)

Built on [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast), with thanks to the upstream project. See [third-party notices](https://github.com/Tongyun1/Jev-in-the-Loop/blob/main/THIRD_PARTY_NOTICES.md).
