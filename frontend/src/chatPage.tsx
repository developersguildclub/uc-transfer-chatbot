import { type FormEvent, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';

interface Message {
	role: 'bot' | 'user';
	text: string;
}

const CHAT_MESSAGES_STORAGE_KEY = 'uc-transfer-chatbot:messages';
const REVEAL_INTERVAL_MS = 32;

const INITIAL_MESSAGES: Message[] = [];

function isMessage(value: unknown): value is Message {
	return (
		typeof value === 'object' &&
		value !== null &&
		'role' in value &&
		'text' in value &&
		(value.role === 'bot' || value.role === 'user') &&
		typeof value.text === 'string'
	);
}

function loadStoredMessages() {
	try {
		const storedMessages = localStorage.getItem(CHAT_MESSAGES_STORAGE_KEY);
		if (!storedMessages) return INITIAL_MESSAGES;

		const parsedMessages: unknown = JSON.parse(storedMessages);
		return Array.isArray(parsedMessages) && parsedMessages.every(isMessage)
			? parsedMessages
			: INITIAL_MESSAGES;
	} catch {
		return INITIAL_MESSAGES;
	}
}

function readTextDelta(rawEvent: string) {
	let event = '';
	let data = '';

	for (const rawLine of rawEvent.split('\n')) {
		const line = rawLine.replace(/\r$/, '');

		if (line.startsWith('event:')) {
			event = line.slice('event:'.length).trim();
		}

		if (line.startsWith('data:')) {
			data += line.slice('data:'.length).trimStart();
		}
	}

	if (event !== 'text_delta') {
		return null;
	}

	const parsed: unknown = JSON.parse(data);

	if (typeof parsed !== 'object' || parsed === null || !('text' in parsed)) {
		throw new Error('Chat stream text was missing');
	}

	if (typeof parsed.text !== 'string') {
		throw new Error('Chat stream text was invalid');
	}

	return parsed.text;
}

function conversationTitle(messages: Message[]) {
	const firstUserMessage = messages.find((message) => message.role === 'user')?.text;

	if (!firstUserMessage) return 'Current chat';
	if (firstUserMessage.length <= 48) return firstUserMessage;

	return `${firstUserMessage.slice(0, 45)}...`;
}

export default function ChatPage() {
	const [messages, setMessages] = useState<Message[]>(loadStoredMessages);
	const [input, setInput] = useState('');
	const [isSending, setIsSending] = useState(false);
	const bottomRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
	}, [messages]);

	useEffect(() => {
		localStorage.setItem(CHAT_MESSAGES_STORAGE_KEY, JSON.stringify(messages));
	}, [messages]);

	function handleReset() {
		setMessages(INITIAL_MESSAGES);
		setInput('');
		setIsSending(false);
		localStorage.removeItem(CHAT_MESSAGES_STORAGE_KEY);
	}

	async function handleSend() {
		const trimmed = input.trim();
		if (!trimmed || isSending) return;

		const nextMessages: Message[] = [...messages, { role: 'user', text: trimmed }];

		setMessages(nextMessages);
		setInput('');
		setIsSending(true);

		let streamedText = '';
		let shownText = '';
		let streamDone = false;
		let revealTimer: number | undefined;
		let finishReveal = () => {};
		const revealDone = new Promise<void>((resolve) => {
			finishReveal = resolve;
		});

		function writeAssistantMessage(text: string) {
			setMessages((prev) => {
				const next = [...prev];
				const lastMessage = next.at(-1);

				if (!lastMessage || lastMessage.role !== 'bot') {
					return [...next, { role: 'bot', text }];
				}

				next[next.length - 1] = {
					...lastMessage,
					text
				};

				return next;
			});
		}

		function revealText() {
			const remaining = streamedText.length - shownText.length;

			if (remaining > 0) {
				const count = Math.min(remaining, Math.max(4, Math.min(28, Math.ceil(remaining / 6))));
				shownText = streamedText.slice(0, shownText.length + count);
				writeAssistantMessage(shownText);
			}

			if (streamDone && shownText.length === streamedText.length) {
				if (revealTimer !== undefined) {
					window.clearInterval(revealTimer);
				}
				finishReveal();
			}
		}

		function startReveal() {
			if (revealTimer !== undefined) return;

			revealText();
			revealTimer = window.setInterval(revealText, REVEAL_INTERVAL_MS);
		}

		try {
			const res = await fetch('/api/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ message: trimmed, messages: nextMessages })
			});

			if (!res.ok) {
				throw new Error('Chat request failed');
			}

			if (!res.body) {
				throw new Error('Chat response was not streamable');
			}

			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { value, done } = await reader.read();

				buffer += decoder.decode(value, { stream: !done });

				const rawEvents = buffer.split('\n\n');
				buffer = rawEvents.pop() ?? '';

				for (const rawEvent of rawEvents) {
					const text = readTextDelta(rawEvent);

					if (text) {
						streamedText += text;
						startReveal();
					}
				}

				if (done) break;
			}

			streamDone = true;
			revealText();
			await revealDone;
		} catch {
			if (revealTimer !== undefined) {
				window.clearInterval(revealTimer);
			}

			setMessages((prev) => [
				...prev,
				{ role: 'bot', text: "Sorry, I couldn't get a response. Please try again." }
			]);
		} finally {
			setIsSending(false);
		}
	}

	function handleSubmit(e: FormEvent<HTMLFormElement>) {
		e.preventDefault();
		handleSend();
	}

	const hasMessages = messages.length > 0;

	return (
		<div className="app-shell-enter flex min-h-dvh flex-col bg-white text-[#101828] md:flex-row">
			<aside className="sidebar-enter flex border-b border-[#e3e8f0] bg-[#f7f8fb] p-3 md:min-h-dvh md:w-72 md:flex-col md:border-r md:border-b-0">
				<div className="flex w-full min-w-0 flex-col gap-4">
					<div className="brand-card rounded-3xl border border-transparent p-2">
						<a
							href="/"
							className="group flex items-center gap-3 rounded-2xl text-sm font-semibold text-[#101828] transition hover:text-[#0b2f5f]"
							aria-label="UC Transfer Chatbot home"
						>
							<img
								src="/favicon.png"
								className="h-9 w-9 rounded-xl transition duration-300 group-hover:scale-[1.04]"
								alt="Logo of Developer's Guild"
							/>
							<span>UC Transfer Chatbot</span>
						</a>
						<nav className="mt-4 flex flex-col gap-2" aria-label="External links">
							<a
								href="https://developersguild.vercel.app/"
								className="sidebar-link-tab group"
								target="_blank"
								rel="noreferrer"
							>
								<span>visit our website!</span>
								<span aria-hidden="true">-&gt;</span>
							</a>
							<a
								href="https://github.com/developersguildclub/uc-transfer-chatbot"
								className="sidebar-link-tab sidebar-link-tab-small group"
								target="_blank"
								rel="noreferrer"
							>
								<span>star this repo!</span>
								<span aria-hidden="true">-&gt;</span>
							</a>
						</nav>
					</div>

					<button
						type="button"
						className="group flex items-center justify-center gap-2 rounded-2xl border border-[#d8e0ec] bg-white px-4 py-3 text-sm font-semibold text-[#0b2f5f] shadow-sm shadow-[#101828]/5 transition duration-150 hover:-translate-y-0.5 hover:border-[#0b2f5f] hover:bg-[#f8fbff] hover:shadow-md active:translate-y-0 active:scale-[0.99]"
						onClick={handleReset}
					>
						<span className="grid h-5 w-5 place-items-center rounded-full bg-[#e7eef8] text-base leading-none transition group-hover:bg-[#dce8f7]">
							+
						</span>
						New chat
					</button>

					<section
						className="hidden min-h-0 flex-1 flex-col gap-2 md:flex"
						aria-labelledby="history-heading"
					>
						<h2
							id="history-heading"
							className="px-2 pt-2 text-[0.68rem] font-semibold tracking-[0.16em] text-[#758195] uppercase"
						>
							Chat history
						</h2>
						{/* TODO: Replace localStorage-only chat state with conversation persistence. */}
						{/* TODO: Replace localStorage-only chat state with conversation persistence. */}
						{hasMessages ? (
							<button
								type="button"
								className="truncate rounded-2xl bg-[#e7eef8] px-3 py-2.5 text-left text-sm font-medium text-[#0b2f5f] transition hover:bg-[#dce8f7]"
								onClick={() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' })}
							>
								{conversationTitle(messages)}
							</button>
						) : (
							<p className="rounded-xl border border-dashed border-[#cfd8e6] px-3 py-4 text-sm leading-6 text-[#667085]">
								No conversations yet.
							</p>
						)}
					</section>

					<div className="mt-auto hidden border-t border-[#e8edf5] pt-4 md:block">
						{/* TODO: Place authenticated account/profile controls here after auth integration. */}
					</div>
				</div>
			</aside>

			<section className="main-panel-enter flex min-h-0 flex-1 flex-col bg-white">
				<header className="sticky top-0 z-10 border-b border-[#edf1f6] bg-white/90 px-4 py-3 backdrop-blur sm:px-6">
					<div className="mx-auto flex max-w-4xl justify-end">
						<div className="flex shrink-0 items-center gap-2">
							{/* TODO: Connect these controls to auth when auth backend exists. */}
							<button
								type="button"
								className="rounded-full px-4 py-2 text-sm font-medium text-[#101828] opacity-60"
								disabled
							>
								Log in
							</button>
							<button
								type="button"
								className="rounded-full bg-[#0b2f5f] px-4 py-2 text-sm font-semibold text-white opacity-60 shadow-sm shadow-[#0b2f5f]/15"
								disabled
							>
								Sign up
							</button>
						</div>
					</div>
				</header>

				<main className="flex-1 overflow-y-auto px-4 pt-8 pb-36 sm:px-6">
					<div
						className={`mx-auto flex min-h-full max-w-4xl flex-col ${
							hasMessages ? 'justify-end gap-6' : 'justify-center'
						}`}
					>
						{hasMessages ? (
							messages.map((msg, i) =>
								msg.role === 'bot' ? (
									<article key={i} className="message-enter flex gap-3">
										<div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#e7eef8] text-xs font-semibold text-[#0b2f5f] shadow-sm">
											AI
										</div>
										<div
											className={`assistant-message max-w-[min(44rem,100%)] min-w-0 rounded-[1.35rem] border border-[#e3e8f0] bg-[#f8fafc] px-4 py-3 text-sm leading-7 text-[#101828] shadow-sm shadow-[#101828]/5 ${
												isSending && i === messages.length - 1 ? 'streaming-bubble' : ''
											}`}
										>
											<ReactMarkdown>{msg.text}</ReactMarkdown>
										</div>
									</article>
								) : (
									<article key={i} className="message-enter flex justify-end">
										<div className="max-w-[min(36rem,86%)] rounded-[1.35rem] bg-[#0b2f5f] px-4 py-3 text-sm leading-7 text-white shadow-sm shadow-[#0b2f5f]/15">
											{msg.text}
										</div>
									</article>
								)
							)
						) : (
							<section className="hero-enter mx-auto w-full max-w-3xl text-center">
								<div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border border-[#e0e7f2] bg-white shadow-lg shadow-[#101828]/5">
									<img
										src="/favicon.png"
										className="h-10 w-10 rounded-xl"
										alt="Logo of Developer's Guild"
									/>
								</div>
								<p className="text-sm font-semibold text-[#0b2f5f]">UC Transfer Chatbot</p>
								<h1 className="mt-3 text-4xl font-semibold tracking-tight text-balance text-[#101828] sm:text-6xl">
									What should we figure out first?
								</h1>
								<p className="mx-auto mt-5 max-w-xl text-base leading-7 text-pretty text-[#667085]">
									Ask about transfer courses, campus requirements, ASSIST.org articulation, or what
									to clarify with a counselor.
								</p>
							</section>
						)}

						{isSending && messages.at(-1)?.role === 'user' && (
							<article className="message-enter flex gap-3" aria-live="polite">
								<div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#e7eef8] text-xs font-semibold text-[#0b2f5f] shadow-sm">
									AI
								</div>
								<div className="rounded-[1.35rem] border border-[#e3e8f0] bg-[#f8fafc] px-4 py-3 text-sm text-[#667085] shadow-sm">
									Thinking...
								</div>
							</article>
						)}

						<div ref={bottomRef} />
					</div>
				</main>

				<footer className="composer-enter sticky bottom-0 border-t border-[#edf1f6] bg-white/90 px-4 py-4 backdrop-blur-xl sm:px-6">
					<form
						className="mx-auto flex max-w-4xl items-center gap-3 rounded-[1.75rem] border border-[#d7deea] bg-white p-2 shadow-2xl shadow-[#101828]/10 transition duration-150 focus-within:-translate-y-0.5 focus-within:border-[#0b2f5f] focus-within:ring-4 focus-within:ring-[#0b2f5f]/10 hover:border-[#c9d4e5]"
						onSubmit={handleSubmit}
					>
						<label className="sr-only" htmlFor="chat-composer">
							Ask the transfer advisor
						</label>
						<input
							id="chat-composer"
							className="min-h-12 min-w-0 flex-1 bg-transparent px-3 text-base text-[#101828] outline-none placeholder:text-[#7b8797]"
							type="text"
							placeholder="Ask about courses, requirements, recommendations..."
							value={input}
							onChange={(e) => setInput(e.target.value)}
							disabled={isSending}
							aria-label="Ask the transfer advisor"
						/>
						<button
							type="submit"
							className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#0b2f5f] text-white shadow-sm shadow-[#0b2f5f]/15 transition hover:-translate-y-0.5 hover:bg-[#08264d] hover:shadow-md active:translate-y-0 active:scale-95 disabled:cursor-not-allowed disabled:bg-[#bac6d7] disabled:shadow-none"
							aria-label="Send message"
							disabled={isSending || !input.trim()}
						>
							{SendIcon()}
						</button>
					</form>
				</footer>
			</section>
		</div>
	);
}

function SendIcon() {
	return (
		<svg
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			strokeWidth="1.5"
			stroke="currentColor"
			className="size-6"
		>
			<path
				strokeLinecap="round"
				strokeLinejoin="round"
				d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5"
			/>
		</svg>
	);
}
