export { SpeakersBar, type SpeakersBarProps } from "./components/speakers-bar";
export { SpeakerChip, type SpeakerChipProps } from "./components/speaker-chip";
export { SpeakerTag, type SpeakerTagProps } from "./components/speaker-tag";
export {
  RenameForm,
  renameSchema,
  type RenameFormProps,
  type RenameFormValues,
} from "./components/rename-form";
export { useRenameSpeakers, type RenameInput } from "./hooks/use-rename-speakers";
export {
  useSpeakerSample,
  type SpeakerSampleController,
  type UseSpeakerSampleOptions,
} from "./hooks/use-speaker-sample";
export { speakerColorFor, speakerColorSlot, SPEAKER_PALETTE } from "./utils/palette";
