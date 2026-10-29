# Your first beat with Agent Composer (2 minutes)

## 1. Install
Download **[AgentComposerSetup.exe](https://github.com/MarkRoyal44/FL-Studio-Agent-Composer/releases/latest/download/AgentComposerSetup.exe)** and double-click it. If Windows warns you, click **More info › Run anyway**. Say **Y** to loopMIDI.

## 2. Open FL Studio, then Agent Composer
Open FL Studio first, then **Agent Composer** from your desktop or Start menu. A small chat window opens and docks inside FL's window: it floats over your project and minimizes with FL. A minimized console opens with it: that's the app running, so leave it there.

The dot in the header turns **green** when FL is linked. If it stays gray:
1. In FL, open **Options › MIDI settings**.
2. Under Input, click **loopMIDI Port**.
3. Set **Controller type** to **Agent Composer** and turn **Enable** on.

## 3. Pick a brain
Click the gear, then go to **Brain**. Pick the one you have:

| You have | Pick |
|---|---|
| a Claude plan | **Claude Code** (install it, then run `claude` once to sign in) |
| a ChatGPT plan | **Codex** |
| a DeepSeek or Anthropic key | **DeepSeek** or **Claude API**, then paste the key |
| nothing, and you want it free | **Local (Ollama)** |

Each card says what's missing. Everything runs on your own account. See [BRAINS.md](BRAINS.md).

## 4. Just ask
Type like you'd talk to a producer in the room:
- "Make it 140 BPM."
- "Write a dark trap melody in A minor, 8 bars."
- "What plugins am I using?"
- "Mute everything but the drums."

Type `/` for instant commands that cost nothing, such as `/play`, `/stop`, `/undo` and `/snapshot`.

## 5. Approve
Every change shows an **Okay to do this?** card. Click **Approve** or **Not that**. Each change is one undo step in FL.

Want it to just go? Click **YOLO** in the header. It turns red and every change goes through without a card. Click it again to turn approvals back on.

## 6. Where things land
- **Melodies and chords**: in **Notes** you get a `.mid` file to drag into FL. Or open the piano roll and go to **Tools › Scripting › Agent Composer** to drop the notes right in.
- **Your plugins** are in the **VST Dock**: flip presets, turn knobs, park your favorites. The agent can turn the same knobs.
- **Vocal takes**: put them in **Takes** to play, rename and ask about them.
- **Teach it you**: drop lyrics, notes or a style guide into **Mini Brain**. The agent reads them before it answers and tells you which document it used.

## Good to know
- Want it as a plugin? In FL: *Options › Manage plugins › Find installed plugins* once, then **Add › Agent Composer**. The chat opens in its plugin window. The desktop window still works too and docks inside FL; turn that off in Settings › Safety & feel › **Dock inside FL**.
- It can touch your FL project, and nothing else on your computer.
- To remove it, go to **Settings › Apps › Agent Composer for FL Studio › Uninstall**.
