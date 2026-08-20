export class ApiClient {
  async uploadAudio(blob, filename, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/meetings");
      const form = new FormData();
      form.append("audio", blob, filename);
      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      });
      xhr.addEventListener("load", () => {
        if (xhr.status === 201) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(Object.assign(new Error("upload"), { status: xhr.status }));
        }
      });
      xhr.addEventListener("error", () => reject(new Error("network")));
      xhr.send(form);
    });
  }

  async getJob(id) {
    const resp = await fetch(`/api/meetings/${id}`);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw Object.assign(new Error("job"), { detail: body.detail, status: resp.status });
    }
    return resp.json();
  }

  audioUrl(id) {
    return `/api/meetings/${id}/audio`;
  }

  exportUrls(id) {
    return {
      docx: `/api/meetings/${id}/export/docx`,
      json: `/api/meetings/${id}/export/json`,
    };
  }

  async renameSpeakers(id, mapping) {
    const resp = await fetch(`/api/meetings/${id}/speakers`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ speakers: mapping }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw Object.assign(new Error("rename"), { detail: body.detail, status: resp.status });
    }
    return resp.json();
  }

  async reanalyze(id) {
    const resp = await fetch(`/api/meetings/${id}/analyze`, { method: "POST" });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw Object.assign(new Error("reanalyze"), { detail: body.detail, status: resp.status });
    }
    return resp.json();
  }
}
