'use client';

import { useEffect, useRef, useState } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

// Suggestion examples that populate the input field
const suggestionExamples = [
  'こども家庭庁で7兆円無駄遣いされてるって本当？',
  'デジタル庁の予算について教えて',
  'マイナンバー制度の目的と予算は？'
];

// Pre-defined answers for specific suggestions
const predefinedAnswers: Record<string, string> = {
  'こども家庭庁で7兆円無駄遣いされてるって本当？': `令和5年度のこども家庭庁当初予算案（一般会計・特別会計）は、4.8兆円です。

こども家庭庁は、
妊娠・出産・子育て・教育・虐待防止・障害児支援・ひとり親支援まで、
子どもに関わる施策を省庁横断的に統合した司令塔として運営しています。

「お金がかかりすぎ」という声が出る背景には、こども家庭庁の予算の多くが
義務的支出（保育所運営・児童手当等）＝日々の社会基盤の維持費であることが知られていない点があります。

1. 予算の規模

令和5年度の当初予算（一般会計＋特別会計）は 約4.8兆円。
補正を含めると 約5.2兆円規模 です。

これは、保育所の運営・児童手当・出産・妊娠期支援・障害児支援・児童虐待防止・放課後児童クラブなど、既存の子ども関連事業が"省庁から移管された結果"であり、突然増えた支出ではありません。

2. 主な使い道（何をしているのか）

こども家庭庁が所管する主な政策は以下の通りです。
いずれも社会の基盤として必要不可欠で、削減すると生活に直接影響します。

(1) 子育て支援（約3.6兆円）

保育所・認定こども園の運営
保育士の処遇改善（給与の引き上げ等）
放課後児童クラブの整備
保育の受け皿拡大
こども食堂等への支援

(2) 妊娠〜出産・産後の支援（約1,905億円）

伴走型支援（妊婦・低年齢児家庭の相談・訪問）
産後ケアの利用料減免
低所得世帯の妊婦の初回受診料支援
成育医療の広域連携支援

(3) 児童虐待防止・社会的養育（約1,721億円）

児童相談所の体制強化（AIも活用）
里親支援の強化
退所後支援の拡充

(4) 障害児支援（約4,745億円の内数）

発達支援センターの機能強化
地域支援体制の整備

(5) ひとり親家庭等の自立支援（約1,694億円）

職業訓練給付の拡充
同行支援の強化
困窮家庭への食堂支援

(6) 高等教育の無償化（5,311億円）

低所得世帯の大学進学を支える修学支援新制度

3. なぜ予算が大きいのか

保育・給付などの"社会基盤"にかかる費用が大半
　→ これらは削減すると保育所が倒れ、子育て世帯が直撃されます。

少子化対策は将来の労働力・社会保障を支える基盤
　→ 投資を怠ると将来の税収減・社会保障費増につながります。

省庁横断の子ども施策を一元化したため"見える化"されただけ
　→ 予算が急増したわけではなく、厚労省等に分散していた支出をまとめた形です。`,
  'デジタル庁の予算について教えて': `令和5年度のデジタル庁予算は 約4,951億円 です。主な内訳は次のとおりです。

情報システムの整備・運用（約4,812億円）
　ガバメントクラウド、各府省共通システム、マイナポータル改善、自治体システム標準化など。

デジタル社会形成（約13億円）
　マイナンバー利用促進、準公共分野のデータ連携、規制改革のデジタル原則、Web3環境整備、デジタル推進委員の全国展開など。

デジタル庁の運営費（約88億円）
　人件費、デジタル人材採用、コンプライアンス・調達改革、広報など。

デジタル庁予算の大部分は「国・自治体の情報システム統一やガバメントクラウド整備」で、庁舎や組織運営ではなく、行政サービスの基盤整備に使われています。`,
  'マイナンバー制度の目的と予算は？': `令和6年度（2024年度）のデジタル庁「マイナンバー制度の推進」事業の執行額は、約10.8億円（1,075,365千円）です。

デジタル庁は、マイナンバー制度を
デジタル社会の基盤 として位置づけ、国民の利便性向上、行政の効率化、 より公平・公正な社会の実現を目指しています。

この事業の予算は、制度の普及と利用を促進するための 広報活動とコールセンター運営が中心であることが知られていない点があります。

1. 予算の規模

令和6年度（2024年度）の予算・執行状況は以下の通りです。

当初予算： 284,657千円（約2.8億円）
補正予算： 450,000千円（4.5億円）
前年度から繰越し： 790,072千円（約7.9億円）
事業規模（計）： 1,542,779千円（約15.4億円）
執行額： 1,075,365千円（約10.8億円）

これは、マイナンバーカードの利便性・安全性の広報や、制度に関する国民の疑問に答えるコールセンターの運営など、制度の普及と利用促進のために使われた費用です。

2. 主な使い道（何をしているのか）

令和6年度（2024年度）の執行額（約10.8億円）の主な支出先と業務内容は以下の通りです。

(1) 広報関係業務（約8.5億円）

株式会社読売広告社ほか（846,553千円）
マイナンバーカードの利便性・安全性に係る広報 、健康保険証利用促進のデモ体験事業 などを実施しています。
※ここから「株式会社博報堂DYメディアパートナーズほか（622,724千円）」 や「株式会社白組ほか（64,812千円）」 などへ広報業務が再委託されています。

(2) コールセンター運営業務（約2.1億円）

富士ソフトサービスビューロ株式会社（207,119千円）
マイナンバー総合フリーダイヤル（コールセンター）の設置・運営 を行っています。

(3) 広報資料の印刷・発送業務（約1,578万円）

三松堂印刷株式会社ほか（15,780千円）
リーフレットやポスターの印刷、梱包、発送業務 を行っています。

(4) インターネットによるアンケート調査（約674万円）

ネットエイジア株式会社（3,888千円）
株式会社モニタス（2,856千円）
マイナンバーカードの普及促進等に関するアンケート調査 を実施しています。

(5) 広報用物品の購入・保守など（約191万円）

ヤマダデンキ株式会社ほか（1,906千円）
顔認証付きカードリーダー用パソコンの購入 や、着ぐるみ「マイナちゃん」のクリーニング などを行っています。

3. なぜこの予算が必要なのか

デジタル社会の基盤の「普及・利用促進」が目的のため
予算の大部分は、制度の普及と利用促進を強力に推進するための広報活動と、国民からの質問に対応するコールセンターの運営という2大業務に使われています。

国民の理解と不安払拭が重要課題のため
事業の概要として「マイナンバーカードの利便性・安全性について、国民の不安を払拭しつつ、正しい認知・理解を得られるよう様々なチャネルにおいて主体的に広報を実施する」ことが明記されています。`
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isComposing, setIsComposing] = useState(false);
  const [loadingMessageIndex, setLoadingMessageIndex] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Loading messages that will cycle through
  const loadingMessages = [
    'GovGovが参考文献を検索しています',
    'GovGovが政府の情報を分析しています',
    'GovGovが必要な情報を取得しています',
    'GovGovが回答を生成しています'
  ];

  // 新しいメッセージが追加されたら自動スクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Cycle through loading messages while loading
  useEffect(() => {
    if (isLoading) {
      setLoadingMessageIndex(0);
      const interval = setInterval(() => {
        setLoadingMessageIndex((prev) => (prev + 1) % loadingMessages.length);
      }, 2500); // Change message every 2.5 seconds

      return () => clearInterval(interval);
    }
  }, [isLoading, loadingMessages.length]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // IME変換中（日本語入力の予測変換中）はEnterを無視
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleCompositionStart = () => {
    setIsComposing(true);
  };

  const handleCompositionEnd = () => {
    setIsComposing(false);
  };

  const handleCopy = async (content: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(messageId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsGenerating(false);
      setIsLoading(false);
    }
  };

  const handleRegenerate = async () => {
    if (messages.length < 2) return;

    // Remove last assistant message
    const newMessages = messages.slice(0, -1);
    setMessages(newMessages);

    // Get the last user message
    const lastUserMessage = newMessages[newMessages.length - 1];

    // Regenerate response
    await generateResponse(newMessages, lastUserMessage);
  };

  const generateResponse = async (currentMessages: Message[], userMessage: Message) => {
    setIsLoading(true);
    setIsGenerating(true);

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
    };

    setMessages((prev) => [...prev, assistantMessage]);

    // Check if there's a predefined answer for this question
    const predefinedAnswer = predefinedAnswers[userMessage.content];

    if (predefinedAnswer) {
      // Simulate RAG processing with 5-second delay
      try {
        await new Promise(resolve => setTimeout(resolve, 5000));

        // Start transition
        setIsTransitioning(true);
        await new Promise(resolve => setTimeout(resolve, 350));
        setIsLoading(false);
        await new Promise(resolve => setTimeout(resolve, 50));
        setIsTransitioning(false);

        // Simulate streaming effect with the predefined answer
        const chunkSize = 50;
        let accumulatedContent = '';

        for (let i = 0; i < predefinedAnswer.length; i += chunkSize) {
          accumulatedContent += predefinedAnswer.slice(i, i + chunkSize);

          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = {
              ...newMessages[newMessages.length - 1],
              content: accumulatedContent,
            };
            return newMessages;
          });

          // Small delay between chunks for streaming effect
          if (i + chunkSize < predefinedAnswer.length) {
            await new Promise(resolve => setTimeout(resolve, 30));
          }
        }
      } catch (error: any) {
        console.error('Error:', error);
      } finally {
        setIsLoading(false);
        setIsGenerating(false);
        abortControllerRef.current = null;
      }
      return;
    }

    abortControllerRef.current = new AbortController();

    // タイムアウト設定（60秒）
    const timeoutId = setTimeout(() => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    }, 60000);

    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [...currentMessages, userMessage],
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`サーバーエラー: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('レスポンスの読み取りに失敗しました');
      }

      let accumulatedContent = '';
      let isFirstChunk = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        accumulatedContent += chunk;

        // First chunk received - start transition
        if (isFirstChunk && accumulatedContent.trim().length > 0) {
          isFirstChunk = false;
          setIsTransitioning(true);
          // Wait for the fade-out animation to complete
          await new Promise(resolve => setTimeout(resolve, 350));
          setIsLoading(false);
          // Small delay before fade-in starts
          await new Promise(resolve => setTimeout(resolve, 50));
          setIsTransitioning(false);
        }

        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...newMessages[newMessages.length - 1],
            content: accumulatedContent,
          };
          return newMessages;
        });
      }
    } catch (error: any) {
      console.error('Error:', error);

      if (error.name === 'AbortError') {
        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...newMessages[newMessages.length - 1],
            content: newMessages[newMessages.length - 1].content || 'リクエストがタイムアウトしました。処理に時間がかかっている可能性があります。\n\nしばらく時間をおいてから再度お試しください。',
          };
          return newMessages;
        });
      } else {
        const errorMessage = error.message || 'エラーが発生しました';
        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...newMessages[newMessages.length - 1],
            content: `❌ ${errorMessage}\n\n時間をおいて再試行してください。問題が続く場合は、ネットワーク接続を確認してください。`,
          };
          return newMessages;
        });
      }
    } finally {
      clearTimeout(timeoutId);
      setIsLoading(false);
      setIsGenerating(false);
      abortControllerRef.current = null;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    await generateResponse(messages, userMessage);
  };

  // Handle suggestion click - populate input field
  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
  };

  return (
    <div className="flex flex-col h-screen relative">
      {/* Decorative shapes in corners */}
      <div className="decorative-shape shape-top-left"></div>
      <div className="decorative-shape shape-top-right"></div>
      <div className="decorative-shape shape-bottom-left"></div>
      <div className="decorative-shape shape-bottom-right"></div>

      {/* Header */}
      <header className="px-4 sm:px-8 md:px-12 lg:px-16 py-3 sm:py-4 md:py-6 lg:py-8 relative z-10 text-center">
        <h1
          className="font-inter mb-1.5 sm:mb-2 md:mb-3 text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-[4rem]"
          style={{
            letterSpacing: '-0.02em',
            lineHeight: '1.1',
            color: 'var(--text-black)',
            fontStyle: 'italic',
            fontWeight: 400
          }}
        >
          GovGov
        </h1>
        <p
          className="font-noto font-medium mb-1 sm:mb-1.5 md:mb-2 text-base sm:text-lg md:text-xl lg:text-2xl"
          style={{
            color: 'var(--text-black)',
            lineHeight: '1.3'
          }}
        >
          政府の予算を透明に
        </p>
        <p
          className="font-inter font-light text-xs sm:text-sm md:text-base"
          style={{
            color: 'var(--text-gray)',
            lineHeight: '1.4'
          }}
        >
          Making Government Budgets Transparent.
        </p>
      </header>

      {/* Chat display area */}
      <main className="flex-1 overflow-y-auto px-4 sm:px-6 md:px-8 py-4 sm:py-6 pb-32 sm:pb-28 relative z-10">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="text-center mt-8 sm:mt-12 md:mt-16 lg:mt-20 px-4">
              <h2
                className="font-semibold mb-2 sm:mb-3 md:mb-4 text-lg sm:text-xl md:text-2xl lg:text-3xl"
                style={{
                  color: 'var(--text-black)',
                  lineHeight: '1.4'
                }}
              >
                何でも質問してください
              </h2>
              <p
                className="text-xs sm:text-sm md:text-base lg:text-lg leading-relaxed mb-6 sm:mb-8 md:mb-10"
                style={{
                  color: 'var(--text-gray)',
                  lineHeight: '1.6'
                }}
              >
                行政事業レビューに関する質問に、AIがお答えします。<br className="hidden sm:inline" />
                <span className="sm:hidden"> </span>予算、事業内容、成果指標などについてお聞きください。
              </p>

              {/* Suggestion Examples */}
              <div>
                <h3
                  className="text-sm sm:text-base md:text-lg font-semibold mb-3 sm:mb-4"
                  style={{ color: 'var(--text-black)' }}
                >
                  質問の例
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 max-w-4xl mx-auto">
                  {suggestionExamples.map((example, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(example)}
                      className="suggestion-card"
                      style={{
                        padding: '1rem 1.25rem',
                        borderRadius: '12px',
                        border: '1px solid var(--border-gray)',
                        backgroundColor: 'white',
                        color: 'var(--text-gray)',
                        fontSize: '0.875rem',
                        cursor: 'pointer',
                        transition: 'all 0.3s ease',
                        boxShadow: '0 1px 4px rgba(0, 0, 0, 0.08)',
                        textAlign: 'center',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        minHeight: '60px'
                      }}
                    >
                      <span>{example}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message, index) => {
                const isLatestAssistant = message.role === 'assistant' && index === messages.length - 1;
                const isGeneratingThisMessage = isLatestAssistant && isGenerating;

                return (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.role === 'user' ? 'justify-end' : 'justify-start'
                    } ${message.role === 'assistant' && isLatestAssistant ? 'response-slide-in' : 'animate-fadeIn'}`}
                  >
                    <div className="w-full sm:max-w-[85%] md:max-w-[75%] lg:max-w-[70%]">
                      {message.content ? (
                        <div
                          className="text-sm sm:text-base message-bubble"
                          style={{
                            padding: '0.75rem 1rem',
                            borderRadius: '16px',
                            backgroundColor: message.role === 'user' ? 'var(--medium-blue)' : 'white',
                            color: message.role === 'user' ? 'white' : 'var(--text-black)',
                            lineHeight: '1.6',
                            boxShadow: message.role === 'user' ? '0 2px 8px rgba(0,0,0,0.1)' : '0 2px 12px rgba(0,0,0,0.08)',
                            border: message.role === 'assistant' ? '1px solid var(--border-gray)' : 'none'
                          }}
                        >
                          <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                            {message.content}
                            {isGeneratingThisMessage && (
                              <span className="typing-cursor"></span>
                            )}
                          </div>
                        </div>
                      ) : null}
                    {message.role === 'assistant' && message.content && (
                      <div className="flex gap-2 mt-2">
                        <button
                          onClick={() => handleCopy(message.content, message.id)}
                          className="text-xs sm:text-sm action-button"
                          style={{
                            padding: '0.375rem 0.625rem',
                            borderRadius: '10px',
                            border: '1px solid var(--border-gray)',
                            backgroundColor: 'white',
                            color: 'var(--text-gray)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            transition: 'all 0.2s'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = 'var(--medium-blue)';
                            e.currentTarget.style.color = 'var(--medium-blue)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = 'var(--border-gray)';
                            e.currentTarget.style.color = 'var(--text-gray)';
                          }}
                        >
                          {copiedId === message.id ? (
                            <>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <polyline points="20 6 9 17 4 12"></polyline>
                              </svg>
                              コピー済み
                            </>
                          ) : (
                            <>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                              </svg>
                              コピー
                            </>
                          )}
                        </button>
                        {messages[messages.length - 1].id === message.id && !isGenerating && (
                          <button
                            onClick={handleRegenerate}
                            className="text-xs sm:text-sm action-button"
                            style={{
                              padding: '0.375rem 0.625rem',
                              borderRadius: '10px',
                              border: '1px solid var(--border-gray)',
                              backgroundColor: 'white',
                              color: 'var(--text-gray)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem',
                              transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.borderColor = 'var(--medium-blue)';
                              e.currentTarget.style.color = 'var(--medium-blue)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.borderColor = 'var(--border-gray)';
                              e.currentTarget.style.color = 'var(--text-gray)';
                            }}
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <polyline points="23 4 23 10 17 10"></polyline>
                              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                            </svg>
                            再生成
                          </button>
                        )}
                      </div>
                    )}
                    </div>
                  </div>
                );
              })}
              {/* Loading UI */}
              {isLoading && (
                <div className={`flex justify-start ${isTransitioning ? 'loading-fade-out' : 'animate-fadeIn'}`}>
                  <div className="flex items-center gap-3 sm:gap-4">
                    <div
                      className="loading-icon-bounce w-14 h-14 sm:w-16 sm:h-16 md:w-20 md:h-20"
                      style={{
                        borderRadius: '50%',
                        backgroundColor: 'white',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                    >
                      <img
                        src="/govgov-icon.png"
                        alt="govgov"
                        className="w-10 h-10 sm:w-11 sm:h-11 md:w-14 md:h-14"
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <span
                        key={loadingMessageIndex}
                        className="loading-message-text text-sm sm:text-base font-semibold"
                        style={{
                          color: 'var(--text-black)'
                        }}
                      >
                        {loadingMessages[loadingMessageIndex]}
                      </span>
                      <div className="flex items-center gap-1.5 h-4 sm:h-5">
                        <div className="thinking-dot w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full" style={{
                          backgroundColor: '#2B9FD9',
                          boxShadow: '0 0 8px rgba(43, 159, 217, 0.5)'
                        }}></div>
                        <div className="thinking-dot w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full" style={{
                          backgroundColor: '#2B9FD9',
                          boxShadow: '0 0 8px rgba(43, 159, 217, 0.5)'
                        }}></div>
                        <div className="thinking-dot w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full" style={{
                          backgroundColor: '#2B9FD9',
                          boxShadow: '0 0 8px rgba(43, 159, 217, 0.5)'
                        }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Chat input area - fixed at bottom */}
      <footer
        className="fixed bottom-0 left-0 right-0 px-3 py-2 sm:px-4 sm:py-3 md:px-6 md:py-4"
        style={{
          borderTop: '1px solid var(--border-gray)',
          backgroundColor: 'var(--background-white)',
          zIndex: 100
        }}
      >
        <form
          onSubmit={handleSubmit}
          className="max-w-4xl mx-auto flex gap-2 items-center"
        >
          <textarea
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            placeholder="行政事業について質問してください..."
            disabled={isLoading}
            rows={1}
            className="flex-1 text-sm sm:text-base"
            style={{
              padding: '0.625rem 0.875rem',
              borderRadius: '20px',
              border: '1px solid #d1d5db',
              outline: 'none',
              transition: 'border-color 0.2s, box-shadow 0.2s',
              backgroundColor: 'white',
              resize: 'none',
              fontFamily: 'inherit',
              lineHeight: '1.4',
              minHeight: '40px',
              maxHeight: '120px',
              overflowY: 'auto'
            }}
            onFocus={(e) => {
              e.target.style.borderColor = 'var(--medium-blue)';
              e.target.style.boxShadow = '0 0 0 1px var(--medium-blue)';
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#d1d5db';
              e.target.style.boxShadow = 'none';
            }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = Math.min(target.scrollHeight, 120) + 'px';
            }}
          />
          {isGenerating ? (
            <button
              type="button"
              onClick={handleStopGeneration}
              className="w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0"
              style={{
                backgroundColor: '#EF4444',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s',
                boxShadow: '0 1px 3px rgba(239, 68, 68, 0.3)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.opacity = '0.9';
                e.currentTarget.style.transform = 'scale(1.05)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = '1';
                e.currentTarget.style.transform = 'scale(1)';
              }}
            >
              <svg
                className="w-3.5 h-3.5 sm:w-4 sm:h-4"
                fill="white"
                viewBox="0 0 24 24"
              >
                <rect x="6" y="6" width="12" height="12" rx="1"></rect>
              </svg>
            </button>
          ) : (
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0"
              style={{
                backgroundColor: 'var(--medium-blue)',
                border: 'none',
                cursor: isLoading || !input.trim() ? 'not-allowed' : 'pointer',
                opacity: isLoading || !input.trim() ? 0.5 : 1,
                transition: 'all 0.2s',
                boxShadow: '0 1px 3px rgba(50, 141, 202, 0.3)'
              }}
              onMouseEnter={(e) => {
                if (!isLoading && input.trim()) {
                  e.currentTarget.style.opacity = '0.9';
                  e.currentTarget.style.transform = 'scale(1.05)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = isLoading || !input.trim() ? '0.5' : '1';
                e.currentTarget.style.transform = 'scale(1)';
              }}
            >
              <svg
                className="w-3.5 h-3.5 sm:w-4 sm:h-4"
                fill="none"
                stroke="white"
                strokeWidth="2.5"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            </button>
          )}
        </form>
        <p
          className="text-[9px] sm:text-[10px] md:text-xs text-center mt-1.5 sm:mt-2 mb-0 px-2 leading-tight"
          style={{
            color: 'var(--text-gray)',
            opacity: 0.8
          }}
        >
          ※ このサービスはAIによる回答であり、100%の正確性を保証するものではありません
        </p>
      </footer>
    </div>
  );
}
