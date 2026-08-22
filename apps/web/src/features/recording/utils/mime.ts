export function fileExtensionForMime(mime: string): string {
  if (mime.includes("mp4")) return "mp4";
  if (mime.includes("ogg")) return "ogg";
  if (mime.includes("mpeg") || mime.includes("mp3")) return "mp3";
  if (mime.includes("wav")) return "wav";
  if (mime.includes("m4a")) return "m4a";
  return "webm";
}

export function blobToFile(blob: Blob, baseName: string): File {
  const ext = fileExtensionForMime(blob.type);
  return new File([blob], `${baseName}.${ext}`, { type: blob.type });
}
