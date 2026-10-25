# Where to share Breadcrumbs

Suggestions checked on 25 October 2026. These are recommendations; no posts
have been published or messages sent.

1. **Show HN:** a good first choice for technical feedback once the build is
   easy to install. Link directly to the repository, explain the small problem
   it solves, and be around to answer questions. Present the project itself,
   rather than a minor version announcement. The official guidance requires a
   working project readers can try and discourages requests for upvotes.
   [Show HN guidelines](https://news.ycombinator.com/showhn.html)
2. **DEV Community:** publish a practical walkthrough: one goal, one focus
   block, a useful detour, a return, and a reflection. Include screenshots or a
   short demo and invite feedback/contributors. This is a recommendation based
   on the developer audience. Follow the community's attribution and AI
   disclosure guidance when preparing the article.
   [DEV code of conduct](https://dev.to/code-of-conduct)
3. **Your own developer network:** share a short demo on your existing social
   profile or in a development community where you already participate. Ask
   for specific feedback on the timer, session continuity, and whether the
   trail helps people return to their goals. Avoid posting the same promotion
   across unrelated communities.

**Wait before r/commandline.** Its posted rules exclude projects less than a
month old, prohibit AI-written post titles/text, require disclosure when code
is partly AI-generated, and restrict generative-AI-related projects. Given
Breadcrumbs's age and agent integrations, check with moderators before using
that channel; it is not a good immediate launch destination.
[Community rules](https://www.reddit.com/r/commandline/comments/1t8pkj7/please_read_the_rules/)

Lead with this idea: **A terminal-first productivity timer that keeps your
goals in view and helps you understand where you trail off.** Demonstrate the
timer before the integrations, and include the contributor invitation.

Before sharing, make the first paragraph honest about current support:

> The timer and paired Chrome/Edge extension work on Windows, Linux and macOS.
> Native foreground-app capture currently supports Windows and Linux/X11;
> macOS and Wayland native capture are not implemented yet.

Link the short intention → start → detour → trail demo and the current
[release](https://github.com/SaroashDS/Breadcrumbs/releases/latest), then point
contributors at [concrete tickets](CONTRIBUTOR_TASKS.md). Do not advertise a
bare-name PyPI installation until the first real PyPI upload succeeds. The
released-wheel pipx/uvx commands in [INSTALL.md](INSTALL.md) work without a
piped script or Git clone.
