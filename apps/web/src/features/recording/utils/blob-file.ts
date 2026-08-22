export function concatChunks(chunks: readonly Blob[], type: string): Blob | null {
  if (chunks.length === 0) return null;
  return new Blob(chunks as BlobPart[], { type });
}
