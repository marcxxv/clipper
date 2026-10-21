# Visual overview

A simplified introduction to Clipper. For components, dependencies and data paths, see [System architecture](ARCHITECTURE.md).

![Clipper illustrated overview](architecture/overview.png)

The source video, waveform and phone previews are illustrations, not pipeline screenshots.

To regenerate the illustration from the repository root:

```sh
python -m pip install Pillow==11.3.0
python docs/architecture/render-overview.py
```

The renderer uses bundled licensed fonts in `docs/architecture/fonts/` and requires no paid graphics service. Commit the renderer and regenerated PNG together; inspect the image at 720 pixels wide. This optional illustration is maintained separately from the architecture checks.

Design direction: [Signal to Story](architecture/visual-direction.md).
