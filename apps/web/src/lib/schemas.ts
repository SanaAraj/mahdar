import { z } from "zod";

export const jobStatusSchema = z.enum([
  "received",
  "converting",
  "transcribing",
  "diarizing",
  "assembling",
  "analyzing",
  "done",
  "failed",
]);
export type JobStatus = z.infer<typeof jobStatusSchema>;

export const stageStateSchema = z.enum(["pending", "running", "done", "skipped", "error"]);
export type StageState = z.infer<typeof stageStateSchema>;

export const stageSchema = z.object({
  key: z.string(),
  label_ar: z.string(),
  state: stageStateSchema,
  note_ar: z.string().nullish(),
});
export type Stage = z.infer<typeof stageSchema>;

export const sentenceSchema = z.object({
  id: z.string(),
  start: z.number(),
  end: z.number(),
  text: z.string(),
  speaker: z.string().nullish(),
});
export type Sentence = z.infer<typeof sentenceSchema>;

export const speakerSchema = z.object({
  id: z.string(),
  label: z.string(),
  first_start: z.number(),
});
export type Speaker = z.infer<typeof speakerSchema>;

export const dueDateSchema = z.object({
  raw: z.string().nullish(),
  gregorian: z.string().nullish(),
  hijri: z.string().nullish(),
});
export type DueDate = z.infer<typeof dueDateSchema>;

const citedFields = {
  segment_ids: z.array(z.string()).default([]),
};

export const topicSchema = z.object({
  ...citedFields,
  title: z.string(),
  summary: z.string(),
});
export type Topic = z.infer<typeof topicSchema>;

export const decisionSchema = z.object({
  ...citedFields,
  text: z.string(),
});
export type Decision = z.infer<typeof decisionSchema>;

export const directiveSchema = z.object({
  ...citedFields,
  text: z.string(),
});
export type Directive = z.infer<typeof directiveSchema>;

export const taskPrioritySchema = z.enum(["عالية", "متوسطة", "منخفضة"]);
export type TaskPriority = z.infer<typeof taskPrioritySchema>;

export const taskItemSchema = z.object({
  ...citedFields,
  description: z.string(),
  owner: z.string().nullish(),
  due: dueDateSchema.default({}),
  priority: taskPrioritySchema.nullish(),
});
export type TaskItem = z.infer<typeof taskItemSchema>;

export const analysisSchema = z.object({
  title: z.string(),
  attendees: z.array(z.string()).default([]),
  topics: z.array(topicSchema).default([]),
  decisions: z.array(decisionSchema).default([]),
  directives: z.array(directiveSchema).default([]),
  tasks: z.array(taskItemSchema).default([]),
});
export type Analysis = z.infer<typeof analysisSchema>;

export const meetingJobSchema = z.object({
  id: z.string(),
  created_at: z.string(),
  status: jobStatusSchema,
  stages: z.array(stageSchema).default([]),
  duration_s: z.number().nullish(),
  error_ar: z.string().nullish(),
  sentences: z.array(sentenceSchema).default([]),
  speakers: z.array(speakerSchema).default([]),
  analysis: analysisSchema.nullish(),
  date_gregorian: z.string().nullish(),
  date_hijri: z.string().nullish(),
});
export type MeetingJob = z.infer<typeof meetingJobSchema>;

export const exportMetaSchema = z.object({
  id: z.string(),
  created_at: z.string(),
  date_gregorian: z.string().nullish(),
  date_hijri: z.string().nullish(),
  duration_s: z.number().nullish(),
});
export type ExportMeta = z.infer<typeof exportMetaSchema>;

export const exportMeetingSchema = z.object({
  meta: exportMetaSchema,
  speakers: z.array(speakerSchema),
  sentences: z.array(sentenceSchema),
  analysis: analysisSchema.nullish(),
});
export type ExportMeeting = z.infer<typeof exportMeetingSchema>;
