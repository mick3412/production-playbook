<!-- Copied 2026-10-28 from https://feedmedia.notion.site/How-to-edit-videos-with-Claude-every-effect-from-my-video-4041d073e26281f690a6f4ab2f5f1e93 for reference. GIF demos not copied. -->

# How to edit videos with Claude: every effect from my video

> The prompts below include the exact styling I used in my video: fonts, colours, sizes and timing. Swap any of it for your own style.

## Setup

Install Claude Code, then paste this:

```
Set me up to edit videos with you. Install Remotion, FFmpeg, Whisper (with word-level timestamps) and yt-dlp. Check each one runs.
```

For anything behind your head you need a person cutout. On a Mac it's built in: tell Claude to use Apple Vision person segmentation. On Windows or Linux, run pip install rembg.

## 1. Storyboard first

（示範動畫，未複製）

Before Claude edits anything, have it write a storyboard, so you both agree on what the video looks like first.

```
Before you touch the footage, write a storyboard as a table: one row per beat with the time, my exact words, what's on screen, and the tool. Don't render anything until I approve it.
```

## 2. Text behind your head

（示範動畫，未複製）

```
Cut me out with person segmentation. In Remotion, put the title "Text behind / your head" on two lines between the footage and my cutout, so my head covers part of the letters. Font: Geist Pixel Square, 150 px, #F4F4F2, centred at 20% and 27% of the frame height. Each line fades up over 12 frames (ease-out cubic, rising 2% of the frame), the second 4 frames after the first.
```

## 3. Captions

（示範動畫，未複製）

```
Transcribe my clip with Whisper, word-level timestamps. Caption it in Remotion: Helvetica Neue Bold, 64 px, white, soft shadow, centred at 61.5% of the frame height. Up to 3 words at a time. The word being spoken sits on a coral (#D97757) box with 8 px rounded corners; the others have no box. Each chunk cuts on exactly when its first word is spoken.
```

Make it better: don't put a coloured box behind every caption. Highlight only the word being spoken.

## 4. Tool labels

（示範動畫，未複製）

When I name a tool, its logo appears and the name slides out of it.

```
When I say a tool's name, show its logo (110 px, rounded corners) at 61.5% of the frame height. It fades up over 12 frames (ease-out cubic). Then it slides left while the name (bold white, 92 px tall) slides out from behind it to the right, over 12 frames, so logo and name end up centred together.
```

## 5. Repo cards

（示範動畫，未複製）

```
When I mention an open-source tool, show its GitHub repo card at the top of the frame: 85% of the frame width, fading up over 12 frames (ease-out cubic, rising 2% of the frame). Build the card to look like GitHub's dark theme: owner/name, Public badge, description, stars and forks.
```

## 6. Prompt bar

（示範動畫，未複製）

```
Draw a prompt bar as a vector graphic in Remotion: a dark rounded bar (#2B2B2B, fully rounded ends) with my prompt typing in, white Inter text, and a coral (#D97757) send button with an up arrow. Place it at 22.5% of the frame height, 92.6% of the frame wide. Make it a reusable component so every prompt in the video looks the same.
```

## 7. Colour change with a slider

（示範動畫，未複製）

```
Make a warm version of my clip with FFmpeg: colorchannelmixer=rr=1.17:gg=1.10:bb=1.03,eq=saturation=1.12. In Remotion, start on the warm version, then wipe it off with a thin white vertical line moving right to left over 30 frames (ease-in-out cubic).
```

## 8. Magazine cover

（示範動畫，未複製）

```
Turn this shot into a magazine cover with my person cutout: a thin gold frame, a cream serif masthead "CLAUDE" behind my head, cover lines in the top corners and a barcode on the left. The masthead goes behind me, everything else in front. Bring each element in on a stressed word.
```

## 9. Real screenshots

（示範動畫，未複製）

```
Fade up this screenshot of my editor timeline above my head: 90% of the frame wide, rounded corners, soft shadow, 12 frames (ease-out cubic).
```

Make it better: a real screenshot looks much better than a mocked-up editor. Use the real thing whenever you can.

## 10. Transitions

（示範動畫，未複製）

```
On the word "this", shrink my shot into a picture of itself, 3 levels deep, landing above my head. Hold, then push through it into the next shot.
```

Make it better: these zooms are a bit much. I'd go with a whip pan instead:

（示範動畫，未複製）

```
Whip-pan between these two shots. In the last 6 frames of the first shot, slide it left by 8% of the frame width while blurring it up to 50 px (ease-in). Cut. The next shot starts 8% to the right, fully blurred, and settles into place over 6 frames (ease-out cubic). It should feel like one fast camera move.
```

## 11. Moody grade

（示範動畫，未複製）

```
Grade my clip with FFmpeg: curves to pull the highlights down and lift the blacks, saturation down 15%, then a soft vignette.
Above my head, show a grading panel like Lightroom's (Tone Curve, Basic, Effects) and move each control as I say it, with the shot regrading live.
```

## 12. Wall of reels

（示範動畫，未複製）

```
Shrink my shot into the centre of a 3x3 grid and fill the other 8 tiles with these reels, popping in one per frame.
```

（示範動畫，未複製）

To grab the reels, use yt-dlp. It's free and downloads videos from Instagram, TikTok, YouTube, pretty much anywhere.

```
Download these reels with yt-dlp: [paste links]
```

## 13. Pause and explain

（示範動畫，未複製）

The format of the whole video: the clip plays in a window, freezes on a click with the timecode holding, then shrinks to the side while I explain.

```
Play this clip in a window in the top left (54% of the frame wide). On a mouse-click sound, freeze it and stop the timecode in the corner. 10 frames later, shrink the window to the left side (24% wide, rounded corners) over 12 frames (ease-out cubic) while I talk. When I'm done, grow it back and let it play.
```

## 14. Jump cuts

（示範動畫，未複製）

```
Cut every pause longer than 0.22 s, never inside a word. Alternate normal and tight framing (1.15x) on every cut. No zooms or transitions.
```
