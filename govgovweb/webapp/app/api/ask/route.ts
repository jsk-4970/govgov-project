import { StreamingTextResponse } from 'ai';

type NodeLikeProcess = {
  env?: Record<string, string | undefined>;
};

export const runtime = 'edge';

/**
 * Flask APIから回答を取得してストリーミングで返す
 * バックエンドAPIはServer-Sent Events (SSE)形式でストリーミングレスポンスを返す
 */
async function* streamAnswerFromBackend(question: string) {
  const globalProcess = (globalThis as { process?: NodeLikeProcess }).process;
  const backendUrl =
    globalProcess?.env?.BACKEND_API_URL ?? 'http://localhost:8080';
  const apiUrl = `${backendUrl}/api/ask`;

  // タイムアウト設定（60秒）
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, 60000);

  try {
    console.log(`[LOG] Calling backend API: ${apiUrl}`);
    console.log(`[LOG] Request body: ${JSON.stringify({ question })}`);
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);

    console.log(`[LOG] Response status: ${response.status} ${response.statusText}`);
    console.log(`[LOG] Response headers:`, Object.fromEntries(response.headers.entries()));
    console.log(`[LOG] Content-Type: ${response.headers.get('content-type')}`);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[LOG] Backend API HTTP error: ${response.status} ${response.statusText}`);
      console.error(`[LOG] Error response body: ${errorText}`);
      throw new Error(`Backend API error: ${response.status} ${response.statusText}`);
    }

    const contentType = response.headers.get('content-type') || '';
    
    // SSE形式（text/event-stream）のレスポンスを処理
    if (contentType.includes('text/event-stream')) {
      console.log(`[LOG] Detected SSE format, processing stream...`);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      if (!reader) {
        throw new Error('Response body reader is not available');
      }

      let buffer = '';
      let eventLines: string[] = [];
      let hasData = false;
      let latestSources: string[] = [];
      let sourcesEmitted = false;

      const processEventPayload = (
        payload: string,
      ): { done: boolean; chunks: string[] } => {
        const normalized = payload.replace(/\r/g, '');
        if (!normalized) {
          return { done: false, chunks: [] };
        }

        const trimmed = normalized.trim();
        if (trimmed === '[DONE]') {
          console.log(`[LOG] Received [DONE] marker, ending stream`);
          return { done: true, chunks: [] };
        }

        hasData = true;

        let chunks: string[] = [];

        if (/^[\[{]/.test(trimmed)) {
          try {
            const parsed = JSON.parse(trimmed) as unknown;

            if (typeof parsed === 'string') {
              chunks.push(parsed);
            } else if (parsed && typeof parsed === 'object') {
              const obj = parsed as Record<string, unknown>;
              const textChunks: string[] = [];

              if (typeof obj.delta === 'string') {
                textChunks.push(obj.delta);
              } else if (
                obj.delta &&
                typeof obj.delta === 'object' &&
                typeof (obj.delta as Record<string, unknown>).text === 'string'
              ) {
                textChunks.push((obj.delta as Record<string, unknown>).text as string);
              }

              if (typeof obj.answer === 'string') {
                textChunks.push(obj.answer);
              }

              if (typeof obj.text === 'string') {
                textChunks.push(obj.text);
              }

              if (Array.isArray(obj.output)) {
                for (const entry of obj.output) {
                  if (typeof entry === 'string') {
                    textChunks.push(entry);
                  } else if (
                    entry &&
                    typeof entry === 'object' &&
                    typeof (entry as Record<string, unknown>).text === 'string'
                  ) {
                    textChunks.push((entry as Record<string, unknown>).text as string);
                  }
                }
              }

              if (textChunks.length > 0) {
                chunks = textChunks.filter(Boolean);
              }

              const sourceCandidates =
                Array.isArray(obj.sources)
                  ? obj.sources
                  : Array.isArray(obj.references)
                    ? obj.references
                    : obj.type === 'sources' && Array.isArray(obj.data)
                      ? obj.data
                      : null;

              if (sourceCandidates && sourceCandidates.length > 0) {
                latestSources = sourceCandidates.map((source) => String(source));
              }

              if (obj.showSources === true && latestSources.length > 0 && !sourcesEmitted) {
                chunks.push(
                  '\n\n参照元:\n' +
                    latestSources
                      .slice(0, 3)
                      .map((source) => `- ${source}`)
                      .join('\n') +
                    '\n',
                );
                sourcesEmitted = true;
              }
            }
          } catch (jsonError) {
            console.warn('[LOG] Failed to parse SSE payload as JSON:', jsonError);
          }
        }

        if (chunks.length === 0) {
          chunks = [normalized];
        }

        return { done: false, chunks };
      };

      const flushEventLines = (): { done: boolean; chunks: string[] } => {
        if (eventLines.length === 0) {
          return { done: false, chunks: [] };
        }

        const payload = eventLines.join('\n');
        eventLines = [];

        const { done, chunks } = processEventPayload(payload);
        return { done, chunks };
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const rawLine of lines) {
          const line = rawLine.replace(/\r$/, '');

          if (line.startsWith('data:')) {
            let data = line.slice(5);
            if (data.startsWith(' ')) {
              data = data.slice(1);
            }
            eventLines.push(data);
          } else if (line.trim() === '') {
            const { done: doneProcessing, chunks } = flushEventLines();

            for (const chunk of chunks) {
              if (chunk) {
                yield chunk;
              }
            }

            if (doneProcessing) {
              if (!sourcesEmitted && latestSources.length > 0) {
                yield '\n\n参照元:\n';
                for (const source of latestSources.slice(0, 3)) {
                  yield `- ${source}\n`;
                }
                sourcesEmitted = true;
              }
              return;
            }
          } else {
            // event: / id: 等のフィールドは現状無視
            continue;
          }
        }
      }

      if (buffer) {
        const line = buffer.replace(/\r$/, '');
        if (line.startsWith('data:')) {
          let data = line.slice(5);
          if (data.startsWith(' ')) {
            data = data.slice(1);
          }
          eventLines.push(data);
        }
      }

      const { done: streamEnded, chunks: remainingChunks } = flushEventLines();

      for (const chunk of remainingChunks) {
        if (chunk) {
          yield chunk;
        }
      }

      if (streamEnded) {
        if (!sourcesEmitted && latestSources.length > 0) {
          yield '\n\n参照元:\n';
          for (const source of latestSources.slice(0, 3)) {
            yield `- ${source}\n`;
          }
          sourcesEmitted = true;
        }
        return;
      }

      if (!sourcesEmitted && latestSources.length > 0) {
        yield '\n\n参照元:\n';
        for (const source of latestSources.slice(0, 3)) {
          yield `- ${source}\n`;
        }
        sourcesEmitted = true;
      }

      if (!hasData) {
        console.warn(`[LOG] No data received from SSE stream`);
        throw new Error('No data received from backend API');
      }

      return;
    }

    // JSON形式のレスポンスを処理（後方互換性のため）
    console.log(`[LOG] Detected JSON format, parsing response...`);
    const data = await response.json();
    console.log(`[LOG] Response data:`, JSON.stringify(data, null, 2));

    if (!data.ok) {
      console.error(`[LOG] Backend API returned ok=false`);
      console.error(`[LOG] Error message: ${data.error || 'No error message'}`);
      throw new Error(data.error || 'Backend API returned error');
    }

    const answer: string = data.answer || '';
    const sources: string[] = data.sources || [];
    console.log(`[LOG] Answer length: ${answer.length}, Sources count: ${sources.length}`);
    console.log(`[LOG] Answer preview: ${answer.substring(0, 200)}...`);

    // 回答をストリーミングで返す（速度優先で大きめのチャンクに分割）
    const chunkSize = Math.max(80, Math.ceil(answer.length / 10));
    for (let i = 0; i < answer.length; i += chunkSize) {
      yield answer.slice(i, i + chunkSize);
    }

    // 参照元URLがある場合は追加表示
    if (sources.length > 0) {
      yield '\n\n参照元:\n';
      for (const source of sources.slice(0, 3)) {
        yield `- ${source}\n`;
      }
    }
  } catch (error) {
    clearTimeout(timeoutId);
    console.error('[LOG] Backend API call failed:', error);
    console.error('[LOG] Error type:', error instanceof Error ? error.constructor.name : typeof error);
    console.error('[LOG] Error message:', error instanceof Error ? error.message : String(error));
    console.error('[LOG] Error stack:', error instanceof Error ? error.stack : 'No stack trace');
    
    // タイムアウトエラーの場合は特別なメッセージを返す
    if (error instanceof Error && (error.name === 'AbortError' || error.message.includes('aborted'))) {
      const timeoutMessage = `リクエストがタイムアウトしました。処理に時間がかかっている可能性があります。

しばらく時間をおいてから再度お試しください。`;

      yield timeoutMessage;
      return;
    }
    
    // エラー時はフォールバックメッセージを返す
    const fallbackMessage = `申し訳ございません。現在システムが混雑しているか、一時的なエラーが発生しています。

しばらく時間をおいてから再度お試しください。

※ この回答はAIによる参考情報であり、100%の正確性を保証するものではありません。`;

    yield fallbackMessage;
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();

    // useChatはmessages配列を送信するので、最後のユーザーメッセージから質問を抽出
    let question: string;
    if (body.messages && Array.isArray(body.messages)) {
      // messagesフォーマット（useChatから）
      const lastMessage = body.messages[body.messages.length - 1];
      if (lastMessage && lastMessage.role === 'user') {
        question = lastMessage.content;
      } else {
        return new Response('Invalid request: last message must be from user', {
          status: 400,
        });
      }
    } else if (body.question && typeof body.question === 'string') {
      // 直接questionフォーマット（後方互換性）
      question = body.question;
    } else {
      return new Response('Invalid request: messages or question is required', {
        status: 400,
      });
    }

    if (!question || typeof question !== 'string') {
      return new Response('Invalid request: question is required', {
        status: 400,
      });
    }

    // ReadableStreamを作成
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          for await (const chunk of streamAnswerFromBackend(question)) {
            controller.enqueue(encoder.encode(chunk));
          }
          controller.close();
        } catch (error) {
          controller.error(error);
        }
      },
    });

    // StreamingTextResponseを返す
    return new StreamingTextResponse(stream);
  } catch (error) {
    console.error('Error in /api/ask:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
}
