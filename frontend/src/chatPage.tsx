import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

interface Message {
	role: 'bot' | 'user';
	text: string;
}

const CHAT_MESSAGES_STORAGE_KEY = 'uc-transfer-chatbot:messages';

// TODO Chat Bot Name
const INITIAL_MESSAGES: Message[] = [
	{
		role: 'bot',
		text: "Hey! I'm (idk what name yet) 👋 I can help you navigate UC transfer requirements. What would you like to know?"
	}
];

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

		try {
			const res = await fetch('/api/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ message: trimmed, messages: nextMessages })
			});

			if (!res.ok) {
				throw new Error('Chat request failed');
			}

			const data = await res.json();
			if (typeof data.reply !== 'string') {
				throw new Error('Chat response was invalid');
			}

			setMessages((prev) => [...prev, { role: 'bot', text: data.reply }]);
		} catch {
			setMessages((prev) => [
				...prev,
				{ role: 'bot', text: "Sorry, I couldn't get a response. Please try again." }
			]);
		} finally {
			setIsSending(false);
		}
	}

	function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
		if (e.key === 'Enter') handleSend();
	}

	return (
		<div className="flex h-dvh flex-col bg-[radial-gradient(ellipse_at_center,#0E0E0E_25%,#106070_200%)]">
			<header className="flex flex-row items-center justify-between border-b pr-4">
				<a href="/">
					<img src="/favicon.png" className="h-20 p-2" alt="Logo of Developer's Guild" />
				</a>
				<button className="btn rounded-3xl btn-xl btn-primary" onClick={handleReset}>
					Reset
				</button>
			</header>

			<main className="flex-1 overflow-y-auto p-4">
				<div className="flex min-h-full flex-col justify-end p-4">
					{messages.map((msg, i) =>
						msg.role === 'bot' ? (
							<div key={i} className="chat-start chat">
								<div className="chat-bubble bg-primary/50">
									<ReactMarkdown>{msg.text}</ReactMarkdown>
								</div>
							</div>
						) : (
							<div key={i} className="chat-end chat">
								<div className="chat-bubble bg-primary text-primary-content">{msg.text}</div>
							</div>
						)
					)}
					{isSending && (
						<div className="chat-start chat">
							<div className="chat-bubble bg-primary/50">
								<span
									className="loading loading-md loading-dots"
									aria-label="Waiting for response"
								/>
							</div>
						</div>
					)}
				</div>
				<div ref={bottomRef} />
			</main>

			<div className="flex flex-row gap-4 border-t p-4">
				<input
					className="input w-full rounded-3xl input-primary"
					type="text"
					placeholder="Ask about courses to take, requirements, recommendations,..."
					value={input}
					onChange={(e) => setInput(e.target.value)}
					onKeyDown={handleKeyDown}
					disabled={isSending}
				/>
				<button
					className="btn btn-circle btn-primary"
					onClick={handleSend}
					aria-label="Send"
					disabled={isSending}
				>
					{SendIcon()}
				</button>
			</div>
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
