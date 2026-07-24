"use strict";

document.addEventListener("DOMContentLoaded", function () {
    const assistantWindow =
        document.querySelector(".assistant-window");

    const chatForm =
        document.getElementById("chat-form");

    const messageInput =
        document.getElementById("chat-message-input");

    const sendButton =
        document.getElementById("send-button");

    const messageHistory =
        document.getElementById("message-history");

    const typingIndicator =
        document.getElementById("typing-indicator");

    const conversationTitle =
        document.getElementById("conversation-title");

    const closeButton =
        document.getElementById("close-window");

    const minimizeButton =
        document.getElementById("minimize-window");

    if (
        !assistantWindow ||
        !chatForm ||
        !messageInput ||
        !sendButton ||
        !messageHistory
    ) {
        return;
    }

    const sendUrl =
        assistantWindow.dataset.sendUrl;

    const csrfToken =
        chatForm.querySelector(
            "input[name='csrfmiddlewaretoken']"
        ).value;

    function scrollToLatestMessage() {
        messageHistory.scrollTop =
            messageHistory.scrollHeight;
    }

    function resizeTextarea() {
        messageInput.style.height = "auto";

        messageInput.style.height =
            Math.min(messageInput.scrollHeight, 150) + "px";
    }

    function setLoadingState(isLoading) {
        sendButton.disabled = isLoading;
        messageInput.disabled = isLoading;
        typingIndicator.hidden = !isLoading;

        if (isLoading) {
            scrollToLatestMessage();
        }
    }

    function removeWelcomePanel() {
        const welcomePanel =
            document.getElementById("welcome-panel");

        if (welcomePanel) {
            welcomePanel.remove();
        }
    }

    function escapeHtml(value) {
        const container =
            document.createElement("div");

        container.textContent = value;

        return container.innerHTML;
    }

    function formatMessageText(value) {
        return escapeHtml(value)
            .replace(/\n/g, "<br>");
    }

    function createMessageElement(
        role,
        content,
        timeLabel
    ) {
        const article =
            document.createElement("article");

        let roleClass = "chat-message-system";
        let avatar = "!";
        let senderName = "Система";

        if (role === "ENGINEER") {
            roleClass = "chat-message-engineer";
            avatar = "И";
            senderName = "Инженер";
        }

        if (role === "AI") {
            roleClass = "chat-message-ai";
            avatar = "AI";
            senderName = "AI асистент";
        }

        article.className =
            `chat-message ${roleClass}`;

        article.innerHTML = `
            <div class="message-avatar">
                ${avatar}
            </div>

            <div class="message-content">
                <header class="message-header">
                    <strong>
                        ${senderName}
                    </strong>

                    <time>
                        ${timeLabel}
                    </time>
                </header>

                <div class="message-text">
                    ${formatMessageText(content)}
                </div>
            </div>
        `;

        return article;
    }

    function appendMessage(
        role,
        content,
        timeLabel = null
    ) {
        removeWelcomePanel();

        const currentTime =
            timeLabel ||
            new Date().toLocaleTimeString(
                "bg-BG",
                {
                    hour: "2-digit",
                    minute: "2-digit",
                }
            );

        const messageElement =
            createMessageElement(
                role,
                content,
                currentTime
            );

        messageHistory.appendChild(messageElement);

        scrollToLatestMessage();
    }

    async function sendMessage(content) {
        const response = await fetch(
            sendUrl,
            {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({
                    content: content,
                }),
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "Съобщението не можа да бъде изпратено."
            );
        }

        return data;
    }

    chatForm.addEventListener(
        "submit",
        async function (event) {
            event.preventDefault();

            const content =
                messageInput.value.trim();

            if (!content) {
                return;
            }

            appendMessage(
                "ENGINEER",
                content
            );

            messageInput.value = "";
            resizeTextarea();
            setLoadingState(true);

            try {
                const result =
                    await sendMessage(content);

                if (
                    result.conversation &&
                    result.conversation.title &&
                    conversationTitle
                ) {
                    conversationTitle.textContent =
                        result.conversation.title;
                }

                const returnedMessage =
                    result.message;

                if (
                    returnedMessage &&
                    returnedMessage.content
                ) {
                    appendMessage(
                        returnedMessage.role,
                        returnedMessage.content
                    );
                } else {
                    appendMessage(
                        "SYSTEM",
                        "Получен е празен отговор от системата."
                    );
                }

            } catch (error) {
                appendMessage(
                    "SYSTEM",
                    error.message
                );

            } finally {
                setLoadingState(false);
                messageInput.focus();
            }
        }
    );

    messageInput.addEventListener(
        "input",
        resizeTextarea
    );

    messageInput.addEventListener(
        "keydown",
        function (event) {
            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {
                event.preventDefault();

                chatForm.requestSubmit();
            }
        }
    );

    if (closeButton) {
        closeButton.addEventListener(
            "click",
            function () {
                window.close();
            }
        );
    }

    if (minimizeButton) {
        minimizeButton.addEventListener(
            "click",
            function () {
                window.blur();

                if (window.opener) {
                    window.opener.focus();
                }
            }
        );
    }

    window.addEventListener(
        "resize",
        function () {
            localStorage.setItem(
                "globalAiWindowWidth",
                String(window.outerWidth)
            );

            localStorage.setItem(
                "globalAiWindowHeight",
                String(window.outerHeight)
            );
        }
    );

    window.addEventListener(
        "beforeunload",
        function () {
            localStorage.setItem(
                "globalAiWindowScreenX",
                String(window.screenX)
            );

            localStorage.setItem(
                "globalAiWindowScreenY",
                String(window.screenY)
            );

            localStorage.setItem(
                "globalAiWindowWidth",
                String(window.outerWidth)
            );

            localStorage.setItem(
                "globalAiWindowHeight",
                String(window.outerHeight)
            );
        }
    );

    resizeTextarea();
    scrollToLatestMessage();
    messageInput.focus();
});
