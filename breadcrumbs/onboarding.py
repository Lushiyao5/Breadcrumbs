"""Replayable feature tour. Reading it never enables capture or starts a timer."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from .widgets import CommandBar

TOUR_VERSION = 1
TOUR_STEPS = (
    ("Welcome to Breadcrumbs", "Plan a block. Follow your attention. Leave yourself a way back.\n\n"
     "This tour introduces every part of the app, one step at a time. Reading it does not start "
     "a timer, enable tracking, or change your preferences.\n\n"
     "Use Next and Back, or the arrow keys. Skip anytime; press ? from the timer to replay. "
     "On small terminals, scroll the text with your mouse wheel."),
    ("Write your intentions", "Press E to edit intentions. Try: 'Fix the login error' and 'Add a regression test'.\n\n"
     "Ctrl+B adds a task. Enter continues a checklist. F2 checks or unchecks the current task. "
     "Escape returns to timer shortcuts. Drafts save automatically, even before you start.\n\n"
     "Keep the generated session name or type a unique name before starting. Unchecked tasks "
     "and notes carry forward; completed tasks stay in that block's history."),
    ("Pick a rhythm", "Press 1 for Focus, 2 for a short break, or 3 for a long break. "
     "Enter custom minutes and choose Set timer for a standalone block.\n\n"
     "P offers 25/5, 50/10, and 60/10 rhythms. C configures durations and full Focus blocks "
     "per long break. Only a full Focus countdown advances the round; a full long break resets it. "
     "Custom and early-finished work still count toward work totals.\n\n"
     "Space starts, pauses, or resumes. Auto-start focus/break options are in Config."),
    ("Choose your working scope", "Starting a Focus or custom block offers three choices: "
     "choose scope, reuse your previous scope, or continue without tracking.\n\n"
     "Select planned apps, domains such as docs.python.org, individual browser pages, "
     "or supported terminal agents. Ctrl+S saves; Escape cancels without starting.\n\n"
     "B > Scope / source changes scope later. Each running span keeps its own scope snapshot. "
     "Capture runs only during running Focus/custom blocks, never breaks or pauses."),
    ("Connect Chrome or Edge", "Open C > Browser connection for the extension folder, local address, and pairing token.\n\n"
     "In chrome://extensions or edge://extensions, enable Developer mode, choose Load unpacked, "
     "and select that folder. Open the Breadcrumbs extension, paste the address/token, and pair.\n\n"
     "Return to the scope picker to select an open page or domain. Exact-page rules include query "
     "parameters; a similar title is not the same URL. Domain rules also allow subdomains. "
     "Selecting a browser app does not override your page/domain rules."),
    ("Use browser timer controls", "The extension finds the current terminal session automatically. "
     "The popup shows the countdown and follows your app theme. Start, Pause, Resume, "
     "and Finish work without switching back to the terminal.\n\n"
     "Finish asks for a second confirmation, then opens the reflection in the terminal. "
     "Cancel keeps the block. Busy dialogs disable remote controls.\n\n"
     "Sharing and timer controls are separate: Stop sharing stops tab reports, while the timer "
     "can keep running. Disconnect removes the extension's saved pairing."),
    ("Recognize terminal agents", "Open Claude Code or Codex CLI, then reopen B > Scope / source "
     "and choose a detected running agent.\n\n"
     "Breadcrumbs checks the process and a temporary marker in its active terminal title. "
     "A background process alone does not count as focus. Markers are removed when tracking stops.\n\n"
     "Pinned tab titles, multiplexers, and editor-integrated terminals can prevent verification. "
     "Select the terminal app itself for broader host-level scope when appropriate. "
     "Unverified context is shown as Unknown rather than guessed."),
    ("Read and annotate your trail", "The small trail beside intentions pulses during capture and freezes on pause. "
     "Click it or press B for visits, timestamps, durations, app colors, and logos. "
     "The bottom status line describes the current context.\n\n"
     "In scope matches your plan. Deviation is outside it; it need not mean wasted time. "
     "Unknown means verification was unavailable. Away and Excluded stay separate.\n\n"
     "Select a visit: A marks In scope, S marks Supporting, V marks Deviation. Unknown, away, "
     "and excluded observations keep their labels. Return to matching context to rejoin "
     "the main lane. Use the block selector to review older trails."),
    ("Pause, leave, and recover", "Space pauses without ending the block. Q saves and quits. "
     "Reopen Breadcrumbs to choose a saved block; recovery opens paused.\n\n"
     "From a shell: breadcrumbs sessions lists saves; breadcrumbs --resume NAME resumes one; "
     "breadcrumbs --name NAME names a new block. Checkpoints save about every second.\n\n"
     "Time while the app is closed is not counted. Activity spans stay separate across pauses "
     "and recovery. F, Reset, or a timer change offers Keep working, Finish early, or "
     "End session, so you decide how to record partial work."),
    ("Reflect and review", "When a work block finishes, write what you accomplished and optionally "
     "rate focus from 1 to 5. Ctrl+S saves; Escape skips the reflection.\n\n"
     "H opens history with intentions, reflections, elapsed work, and status. The header "
     "shows today's work minutes and completed work blocks using your computer's local date.\n\n"
     "breadcrumbs export --output sessions.json saves session records. Add --activity "
     "to include observations, annotations, scope, and running spans. Add --limit 20 "
     "to export only the newest 20 blocks."),
    ("Make it feel like yours", "C opens Config; Ctrl+S saves and Escape cancels. Choose Midnight Arcade, "
     "Game Boy, or Sunset Drive.\n\n"
     "Choose Arcade, Victory, or Gentle completion sounds. Preview plays the selected pack "
     "without saving, even when completion sounds are off. Outside Windows, sound uses the terminal bell.\n\n"
     "Enable the optional pixel companion; M pets it and N changes it. Reading cards can be Off, "
     "Qur'an, or Quotes, in every block or breaks only. Set their rotation interval "
     "and switch the book animation independently."),
    ("Your data and your first block", "Sessions and preferences stay locally in ~/.breadcrumbs. Existing ~/.tlock "
     "data is reused in place. BREADCRUMBS_HOME selects another directory; legacy TLOCK_HOME "
     "is also supported. The tlock command still works.\n\n"
     "Tracking is optional. The extension sends domains and URL hashes, not raw URL paths/queries. "
     "Hashes are not anonymous; titles are optional. The extension excludes private/internal tabs. "
     "App-only capture cannot reliably identify private windows.\n\n"
     "Native app capture supports Windows and Linux/X11. The timer and paired browser work "
     "without native capture. Check updates with breadcrumbs update --check; install with breadcrumbs update.\n\n"
     "Ready? Close the tour, press E, write one task, press Escape, then Space. Choose scope "
     "or continue without tracking. Press ? while ready or paused to replay this tour."),
)


class OnboardingScreen(ModalScreen[None]):
    BINDINGS = [("escape", "close", "Skip"), ("right", "next", "Next"),
                ("left", "back", "Back"), ("q", "close", "Close tour")]
    CSS = """
    OnboardingScreen { align: center middle; background: #090b12e8; }
    #tour-card { width: 90%; max-width: 84; height: 90%; max-height: 34;
        padding: 1 2; background: #151927; border: round #70e1c1; }
    #tour-progress { height: 1; color: #78869f; }
    #tour-title { height: auto; margin: 1 0; color: #ffd166; text-style: bold; }
    #tour-scroll { height: 1fr; }
    #tour-copy { height: auto; }
    #tour-actions { height: 3; margin-top: 1; }
    #tour-actions Button { width: 1fr; min-width: 6; margin-right: 1; }
    OnboardingScreen.theme-gameboy #tour-card { background: #1c2a14; }
    OnboardingScreen.theme-sunset #tour-card { background: #281438; }
    """

    def __init__(self):
        super().__init__()
        self.step = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="tour-card"):
            yield Static("", id="tour-progress", markup=False)
            yield Static("", id="tour-title", markup=False)
            with VerticalScroll(id="tour-scroll"):
                yield Static("", id="tour-copy", markup=False)
            with Horizontal(id="tour-actions"):
                yield Button("Skip", id="tour-skip")
                yield Button("Back", id="tour-back")
                yield Button("Next", id="tour-next", variant="success")
        yield CommandBar("LEFT / RIGHT steps · TAB buttons · ESC close · scroll for more")

    def on_mount(self):
        self._refresh_step()
        self.query_one("#tour-next", Button).focus()

    def _refresh_step(self):
        title, body = TOUR_STEPS[self.step]
        self.query_one("#tour-progress", Static).update(f"Feature tour · {self.step + 1} of {len(TOUR_STEPS)}")
        self.query_one("#tour-title", Static).update(title)
        self.query_one("#tour-copy", Static).update(body)
        self.query_one("#tour-back", Button).disabled = self.step == 0
        self.query_one("#tour-next", Button).label = "Let's begin" if self.step == len(TOUR_STEPS) - 1 else "Next"
        self.query_one("#tour-scroll", VerticalScroll).scroll_home(animate=False)

    def action_next(self):
        if self.step == len(TOUR_STEPS) - 1:
            self.action_close()
        else:
            self.step += 1
            self._refresh_step()

    def action_back(self):
        self.step = max(0, self.step - 1)
        self._refresh_step()

    def action_close(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        event.stop()
        if event.button.id == "tour-next":
            self.action_next()
        elif event.button.id == "tour-back":
            self.action_back()
        else:
            self.action_close()
