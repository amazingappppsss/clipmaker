import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  DEFAULT_SETTINGS,
  SettingsBar,
} from "@/components/upload/settings-bar";
import { VideoDropZone } from "@/components/upload/video-drop-zone";

describe("VideoDropZone", () => {
  it("accepts a video and rejects other files", () => {
    const onFile = vi.fn();
    const onReject = vi.fn();
    const { container } = render(
      <VideoDropZone onFile={onFile} onReject={onReject} />,
    );
    const input = container.querySelector(
      "input[type=file]",
    ) as HTMLInputElement;

    fireEvent.change(input, {
      target: { files: [new File(["x"], "a.mp4", { type: "video/mp4" })] },
    });
    expect(onFile).toHaveBeenCalledTimes(1);

    fireEvent.change(input, {
      target: { files: [new File(["x"], "a.txt", { type: "text/plain" })] },
    });
    expect(onReject).toHaveBeenCalledTimes(1);
    expect(onFile).toHaveBeenCalledTimes(1);
  });
});

describe("SettingsBar", () => {
  it("defaults to Auto and emits typed changes", () => {
    const onChange = vi.fn();
    render(<SettingsBar value={DEFAULT_SETTINGS} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Clips"), {
      target: { value: "5" },
    });
    expect(onChange).toHaveBeenCalledWith({
      ...DEFAULT_SETTINGS,
      clip_count: 5,
    });
  });
});
