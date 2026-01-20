declare module 'ai' {
  export class StreamingTextResponse extends Response {
    constructor(body: ReadableStream<Uint8Array>);
  }
}

