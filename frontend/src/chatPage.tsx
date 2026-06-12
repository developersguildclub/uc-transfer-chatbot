import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';

interface Message {
	role: 'bot' | 'user';
	text: string;
}

interface User {
	id: number;
	email: string;
}

interface Conversation {
	id: number;
	title: string;
	updated_at: number;
}

interface ApiMessage {
	role: 'assistant' | 'user';
	content: string;
}

type AuthMode = 'login' | 'signup';

const REVEAL_INTERVAL_MS = 32;

const INITIAL_MESSAGES: Message[] = [];

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === 'object' && value !== null;
}

function isUser(value: unknown): value is User {
	return isRecord(value) && typeof value.id === 'number' && typeof value.email === 'string';
}

function isConversation(value: unknown): value is Conversation {
	return (
		isRecord(value) &&
		typeof value.id === 'number' &&
		typeof value.title === 'string' &&
		typeof value.updated_at === 'number'
	);
}

function isApiMessage(value: unknown): value is ApiMessage {
	return (
		isRecord(value) &&
		(value.role === 'assistant' || value.role === 'user') &&
		typeof value.content === 'string'
	);
}

function errorMessage(data: unknown, fallback: string) {
	return isRecord(data) && typeof data.error === 'string' ? data.error : fallback;
}

function readStreamEvent(rawEvent: string) {
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

	const parsed: unknown = JSON.parse(data);

	if (typeof parsed !== 'object' || parsed === null) {
		throw new Error('Chat stream data was invalid');
	}

	return { event, data: parsed as Record<string, unknown> };
}

function messageFromApi(message: ApiMessage): Message {
	return {
		role: message.role === 'assistant' ? 'bot' : 'user',
		text: message.content
	};
}

function messageToApi(message: Message): ApiMessage {
	return {
		role: message.role === 'bot' ? 'assistant' : 'user',
		content: message.text
	};
}

export default function ChatPage() {
	const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
	const [input, setInput] = useState('');
	const [isSending, setIsSending] = useState(false);
	const [user, setUser] = useState<User | null>(null);
	const [csrfToken, setCsrfToken] = useState('');
	const [conversations, setConversations] = useState<Conversation[]>([]);
	const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
	const [historyError, setHistoryError] = useState('');
	const [accountError, setAccountError] = useState('');
	const [authMode, setAuthMode] = useState<AuthMode | null>(null);
	const [authEmail, setAuthEmail] = useState('');
	const [authPassword, setAuthPassword] = useState('');
	const [authError, setAuthError] = useState('');
	const [isAuthSending, setIsAuthSending] = useState(false);
	const bottomRef = useRef<HTMLDivElement>(null);
	const authDialogRef = useRef<HTMLFormElement>(null);
	const authEmailRef = useRef<HTMLInputElement>(null);
	const authReturnFocusRef = useRef<HTMLElement | null>(null);

	const closeAuth = useCallback(() => {
		setAuthMode(null);
		authReturnFocusRef.current?.focus();
	}, []);

	useEffect(() => {
		let active = true;

		fetch('/api/auth/me', { credentials: 'include' })
			.then(async (res) => {
				if (!res.ok) return;

				const data: unknown = await res.json();
				if (!active) return;

				setUser(isRecord(data) && isUser(data.user) ? data.user : null);
				setCsrfToken(isRecord(data) && typeof data.csrfToken === 'string' ? data.csrfToken : '');
				setAccountError('');
			})
			.catch(() => {
				if (active) setAccountError('Could not check account status.');
			});

		return () => {
			active = false;
		};
	}, []);

	useEffect(() => {
		if (!authMode) return;

		authEmailRef.current?.focus();

		function handleKeyDown(e: KeyboardEvent) {
			const dialog = authDialogRef.current;
			if (!dialog) return;

			if (e.key === 'Escape') {
				e.preventDefault();
				closeAuth();
				return;
			}

			if (e.key !== 'Tab') return;

			const controls = Array.from(
				dialog.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled])')
			);
			const first = controls[0];
			const last = controls.at(-1);
			if (!first || !last) return;

			if (e.shiftKey && document.activeElement === first) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		}

		document.addEventListener('keydown', handleKeyDown);
		return () => document.removeEventListener('keydown', handleKeyDown);
	}, [authMode, closeAuth]);

	useEffect(() => {
		bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
	}, [messages]);

	useEffect(() => {
		if (!user) {
			return;
		}

		let active = true;

		fetch('/api/conversations', { credentials: 'include' })
			.then(async (res) => {
				if (!res.ok) throw new Error('Conversation history failed');

				const data = (await res.json()) as { conversations?: unknown };
				if (!Array.isArray(data.conversations) || !data.conversations.every(isConversation)) {
					throw new Error('Conversation history was invalid');
				}

				if (active) {
					setConversations(data.conversations);
					setHistoryError('');
				}
			})
			.catch(() => {
				if (active) setHistoryError('Could not load saved chats.');
			});

		return () => {
			active = false;
		};
	}, [user]);

	function handleReset() {
		if (isSending) return;

		setMessages(INITIAL_MESSAGES);
		setInput('');
		setActiveConversationId(null);
	}

	function openAuth(mode: AuthMode) {
		authReturnFocusRef.current =
			document.activeElement instanceof HTMLElement ? document.activeElement : null;
		setAuthMode(mode);
		setAuthEmail('');
		setAuthPassword('');
		setAuthError('');
	}

	async function handleAuthSubmit(e: FormEvent<HTMLFormElement>) {
		e.preventDefault();
		if (!authMode || isAuthSending) return;

		setIsAuthSending(true);
		setAuthError('');

		try {
			const res = await fetch(`/api/auth/${authMode}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ email: authEmail, password: authPassword })
			});
			const data: unknown = await res.json();

			if (!res.ok || !isRecord(data) || !isUser(data.user)) {
				setAuthError(errorMessage(data, 'Authentication failed'));
				return;
			}

			setUser(data.user);
			setCsrfToken(typeof data.csrfToken === 'string' ? data.csrfToken : '');
			setAccountError('');
			closeAuth();
			setAuthEmail('');
			setAuthPassword('');
		} catch {
			setAuthError('Authentication failed');
		} finally {
			setIsAuthSending(false);
		}
	}

	async function handleLogout() {
		try {
			const res = await fetch('/api/auth/logout', {
				method: 'POST',
				headers: { 'X-CSRF-Token': csrfToken },
				credentials: 'include'
			});

			if (!res.ok) {
				setAccountError('Could not log out.');
				return;
			}

			setUser(null);
			setCsrfToken('');
			setConversations([]);
			setActiveConversationId(null);
			setMessages(INITIAL_MESSAGES);
			setHistoryError('');
			setAccountError('');
		} catch {
			setAccountError('Could not log out.');
		}
	}

	async function refreshConversations() {
		if (!user) return;

		try {
			const res = await fetch('/api/conversations', { credentials: 'include' });
			if (!res.ok) throw new Error('Conversation history failed');

			const data = (await res.json()) as { conversations?: unknown };
			if (!Array.isArray(data.conversations) || !data.conversations.every(isConversation)) {
				throw new Error('Conversation history was invalid');
			}

			setConversations(data.conversations);
			setHistoryError('');
		} catch {
			setHistoryError('Could not load saved chats.');
		}
	}

	async function openConversation(conversationId: number) {
		if (isSending) return;

		try {
			const res = await fetch(`/api/conversations/${conversationId}`, { credentials: 'include' });
			if (!res.ok) {
				setHistoryError('Could not open that chat.');
				return;
			}

			const data = (await res.json()) as {
				conversation?: unknown;
				messages?: unknown;
			};
			if (
				!isConversation(data.conversation) ||
				!Array.isArray(data.messages) ||
				!data.messages.every(isApiMessage)
			) {
				throw new Error('Conversation was invalid');
			}

			setActiveConversationId(data.conversation.id);
			setMessages(data.messages.map(messageFromApi));
			setInput('');
			setHistoryError('');
		} catch {
			setHistoryError('Could not open that chat.');
		}
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
			const headers: Record<string, string> = { 'Content-Type': 'application/json' };
			if (user) headers['X-CSRF-Token'] = csrfToken;

			const res = await fetch('/api/chat', {
				method: 'POST',
				headers,
				credentials: 'include',
				body: JSON.stringify(
					user
						? { message: trimmed, conversation_id: activeConversationId }
						: { message: trimmed, messages: messages.map(messageToApi) }
				)
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
					const streamEvent = readStreamEvent(rawEvent);

					if (
						streamEvent.event === 'message_start' &&
						typeof streamEvent.data.conversation_id === 'number'
					) {
						setActiveConversationId(streamEvent.data.conversation_id);
					}

					if (
						streamEvent.event === 'text_delta' &&
						typeof streamEvent.data.text === 'string'
					) {
						streamedText += streamEvent.data.text;
						startReveal();
					}
				}

				if (done) break;
			}

			streamDone = true;
			revealText();
			await revealDone;
			await refreshConversations();
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
								width={36}
								height={36}
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
						className="group flex items-center justify-center gap-2 rounded-2xl border border-[#d8e0ec] bg-white px-4 py-3 text-sm font-semibold text-[#0b2f5f] shadow-sm shadow-[#101828]/5 transition duration-150 hover:-translate-y-0.5 hover:border-[#0b2f5f] hover:bg-[#f8fbff] hover:shadow-md active:translate-y-0 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:border-[#d8e0ec] disabled:hover:bg-white disabled:hover:shadow-sm"
						onClick={handleReset}
						disabled={isSending}
					>
						<span className="grid h-5 w-5 place-items-center rounded-full bg-[#e7eef8] text-base leading-none transition group-hover:bg-[#dce8f7]">
							+
						</span>
						New chat
					</button>

					<section
						className="flex min-h-0 max-h-44 flex-col gap-2 overflow-y-auto md:max-h-none md:flex-1"
						aria-labelledby="history-heading"
					>
						<h2
							id="history-heading"
							className="px-2 pt-2 text-[0.68rem] font-semibold tracking-[0.16em] text-[#758195] uppercase"
						>
							Chat history
						</h2>
						{!user ? (
							<p className="rounded-xl border border-dashed border-[#cfd8e6] px-3 py-4 text-sm leading-6 text-[#667085]">
								Guest chats stay in this browser. Log in to save chats.
							</p>
						) : historyError ? (
							<p className="rounded-xl border border-[#f3b9b9] bg-[#fff5f5] px-3 py-4 text-sm leading-6 text-[#9f1d1d]">
								{historyError}
							</p>
						) : conversations.length > 0 ? (
							<div className="flex flex-col gap-2">
								{conversations.map((conversation) => (
									<button
										key={conversation.id}
										type="button"
										className={`truncate rounded-2xl px-3 py-2.5 text-left text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60 ${
											conversation.id === activeConversationId
												? 'bg-[#e7eef8] text-[#0b2f5f]'
												: 'text-[#344054] hover:bg-[#edf3fb]'
										}`}
										onClick={() => openConversation(conversation.id)}
										disabled={isSending}
										aria-current={conversation.id === activeConversationId ? 'page' : undefined}
									>
										{conversation.title}
									</button>
								))}
							</div>
						) : (
							<p className="rounded-xl border border-dashed border-[#cfd8e6] px-3 py-4 text-sm leading-6 text-[#667085]">
								No conversations yet.
							</p>
						)}
					</section>

				</div>
			</aside>

			<section className="main-panel-enter flex min-h-0 flex-1 flex-col bg-white">
				<header className="sticky top-0 z-10 border-b border-[#edf1f6] bg-white/90 px-4 py-3 backdrop-blur sm:px-6">
					<div className="mx-auto flex max-w-4xl flex-col items-end gap-2">
						{accountError && (
							<p
								role="alert"
								className="max-w-full rounded-xl border border-[#f3b9b9] bg-[#fff5f5] px-3 py-1.5 text-right text-xs font-medium text-[#9f1d1d]"
							>
								{accountError}
							</p>
						)}
						<div className="flex shrink-0 items-center gap-2">
							{user ? (
								<>
									<span className="hidden max-w-56 truncate text-sm font-medium text-[#344054] sm:block">
										{user.email}
									</span>
									<button
										type="button"
										className="rounded-full border border-[#d8e0ec] px-4 py-2 text-sm font-semibold text-[#0b2f5f] transition hover:border-[#0b2f5f] hover:bg-[#f8fbff]"
										onClick={handleLogout}
									>
										Log out
									</button>
								</>
							) : (
								<>
									<button
										type="button"
										className="rounded-full px-4 py-2 text-sm font-medium text-[#101828] transition hover:bg-[#f3f6fb]"
										onClick={() => openAuth('login')}
									>
										Log in
									</button>
									<button
										type="button"
										className="rounded-full bg-[#0b2f5f] px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-[#0b2f5f]/15 transition hover:bg-[#08264d]"
										onClick={() => openAuth('signup')}
									>
										Sign up
									</button>
								</>
							)}
						</div>
					</div>
				</header>

				{authMode && (
					<div
						className="fixed inset-0 z-30 flex items-center justify-center bg-[#101828]/30 px-4 backdrop-blur-sm"
						onMouseDown={(e) => {
							if (e.target === e.currentTarget) closeAuth();
						}}
					>
						<form
							ref={authDialogRef}
							role="dialog"
							aria-modal="true"
							aria-labelledby="auth-title"
							className="w-full max-w-sm rounded-2xl border border-[#d8e0ec] bg-white p-5 shadow-2xl shadow-[#101828]/20"
							onSubmit={handleAuthSubmit}
						>
							<div className="flex items-center justify-between gap-4">
								<h2 id="auth-title" className="text-lg font-semibold text-[#101828]">
									{authMode === 'signup' ? 'Create account' : 'Log in'}
								</h2>
								<button
									type="button"
									className="grid h-9 w-9 place-items-center rounded-full text-xl leading-none text-[#667085] transition hover:bg-[#f3f6fb] hover:text-[#101828]"
									aria-label="Close account form"
									onClick={closeAuth}
								>
									×
								</button>
							</div>

							<label className="mt-5 block text-sm font-medium text-[#344054]" htmlFor="auth-email">
								Email
							</label>
							<input
								ref={authEmailRef}
								id="auth-email"
								name="email"
								className="mt-2 w-full rounded-xl border border-[#d8e0ec] px-3 py-2.5 text-sm text-[#101828] outline-none transition focus:border-[#0b2f5f] focus:ring-4 focus:ring-[#0b2f5f]/10"
								type="email"
								autoComplete="email"
								value={authEmail}
								onChange={(e) => setAuthEmail(e.target.value)}
								aria-invalid={authError ? true : undefined}
								aria-describedby={authError ? 'auth-error' : undefined}
								required
							/>

							<label className="mt-4 block text-sm font-medium text-[#344054]" htmlFor="auth-password">
								Password
							</label>
							<input
								id="auth-password"
								name="password"
								className="mt-2 w-full rounded-xl border border-[#d8e0ec] px-3 py-2.5 text-sm text-[#101828] outline-none transition focus:border-[#0b2f5f] focus:ring-4 focus:ring-[#0b2f5f]/10"
								type="password"
								autoComplete={authMode === 'signup' ? 'new-password' : 'current-password'}
								value={authPassword}
								onChange={(e) => setAuthPassword(e.target.value)}
								aria-invalid={authError ? true : undefined}
								aria-describedby={authError ? 'auth-error' : undefined}
								minLength={8}
								required
							/>

							{authError && (
								<p
									id="auth-error"
									role="alert"
									className="mt-4 rounded-xl border border-[#f3b9b9] bg-[#fff5f5] px-3 py-2 text-sm text-[#9f1d1d]"
								>
									{authError}
								</p>
							)}

							<button
								type="submit"
								className="mt-5 w-full rounded-xl bg-[#0b2f5f] px-4 py-3 text-sm font-semibold text-white shadow-sm shadow-[#0b2f5f]/15 transition hover:bg-[#08264d] disabled:cursor-not-allowed disabled:bg-[#bac6d7]"
								disabled={isAuthSending || !authEmail.trim() || authPassword.length < 8}
							>
								{isAuthSending ? 'Working...' : authMode === 'signup' ? 'Sign up' : 'Log in'}
							</button>

							<button
								type="button"
								className="mt-3 w-full rounded-xl px-4 py-2 text-sm font-medium text-[#0b2f5f] transition hover:bg-[#f3f6fb]"
								onClick={() => {
									setAuthMode(authMode === 'signup' ? 'login' : 'signup');
									setAuthError('');
									setAuthPassword('');
								}}
							>
								{authMode === 'signup' ? 'Log in instead' : 'Create an account'}
							</button>
						</form>
					</div>
				)}

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
										width={40}
										height={40}
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
