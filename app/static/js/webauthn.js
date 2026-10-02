/**
 * VIBE-FASHION 생체인증 (WebAuthn / Passkey) 클라이언트 라이브러리
 * - Windows Hello, Touch ID, Face ID, 모바일 지문 인식 지원
 */

// Base64URL <-> ArrayBuffer 변환 유틸리티
function base64urlToBuffer(base64url) {
    if (!base64url) return new Uint8Array().buffer;
    let base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4) {
        base64 += '=';
    }
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

function bufferToBase64url(buffer) {
    if (!buffer) return '';
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// 생체인증 지원 여부 확인
function isWebAuthnSupported() {
    return !!(window.PublicKeyCredential && navigator.credentials && navigator.credentials.create);
}

/**
 * 1. 생체인증(Passkey) 기기 등록
 * - 마이페이지 등 로그인된 상태에서 호출
 */
async function registerBiometrics(onSuccessCallback = null) {
    if (!isWebAuthnSupported()) {
        alert("현재 사용 중인 브라우저 또는 기기에서 생체인증(WebAuthn/Passkey)을 지원하지 않습니다.");
        return;
    }

    try {
        // 1) 서버에서 등록 옵션 획득
        const optRes = await fetch("/auth/webauthn/register-options", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        
        if (!optRes.ok) {
            const err = await optRes.json();
            alert(err.message || "생체인증 등록 옵션을 불러오지 못했습니다.");
            return;
        }

        const options = await optRes.json();

        // 2) 바이너리 필드(challenge, user.id)를 ArrayBuffer로 변환
        options.challenge = base64urlToBuffer(options.challenge);
        options.user.id = base64urlToBuffer(options.user.id);

        if (options.excludeCredentials) {
            options.excludeCredentials.forEach(cred => {
                cred.id = base64urlToBuffer(cred.id);
            });
        }

        // 3) 브라우저 생체인증 프롬프트 호출 (Windows Hello / Touch ID / Face ID)
        const credential = await navigator.credentials.create({
            publicKey: options
        });

        if (!credential) {
            alert("생체인증 등록이 취소되었습니다.");
            return;
        }

        // 4) 서버 전송용 payload 직렬화
        const payload = {
            id: credential.id,
            rawId: bufferToBase64url(credential.rawId),
            type: credential.type,
            response: {
                clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
                attestationObject: bufferToBase64url(credential.response.attestationObject),
            }
        };

        // 5) 서버 검증 및 자격증명 저장
        const verifyRes = await fetch("/auth/webauthn/register-verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const verifyData = await verifyRes.json();
        if (verifyData.success) {
            alert(verifyData.message || "생체인증이 성공적으로 등록되었습니다! 🍓");
            if (onSuccessCallback) {
                onSuccessCallback(verifyData);
            } else {
                location.reload();
            }
        } else {
            alert(verifyData.message || "생체인증 검증에 실패했습니다.");
        }

    } catch (err) {
        console.error("생체인증 등록 오류:", err);
        if (err.name === "NotAllowedError") {
            alert("생체인증 등록이 취소되었거나 시간 초과되었습니다.");
        } else if (err.name === "InvalidStateError") {
            alert("이 기기에는 이미 등록된 생체인증 키가 존재합니다.");
        } else {
            alert("생체인증 등록 중 오류가 발생했습니다: " + (err.message || err));
        }
    }
}

/**
 * 2. 생체인증(Passkey)으로 로그인
 * - 로그인 화면 또는 로그인 모달에서 원클릭 호출
 * @param {string|null} email - 특정 계정의 생체인증 조회용 이메일 (선택)
 */
async function loginWithBiometrics(email = null) {
    if (!isWebAuthnSupported()) {
        alert("현재 사용 중인 브라우저 또는 기기에서 생체인증을 지원하지 않습니다.");
        return;
    }

    try {
        // 1) 서버에서 로그인 옵션 획득
        const optRes = await fetch("/auth/webauthn/login-options", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email || "" })
        });

        if (!optRes.ok) {
            const err = await optRes.json();
            alert(err.message || "생체인증 로그인 정보를 불러오지 못했습니다.");
            return;
        }

        const options = await optRes.json();

        // 2) 바이너리 필드(challenge, allowCredentials.id) 변환
        options.challenge = base64urlToBuffer(options.challenge);
        if (options.allowCredentials && options.allowCredentials.length > 0) {
            options.allowCredentials.forEach(cred => {
                cred.id = base64urlToBuffer(cred.id);
            });
        }

        // 3) 브라우저 생체인증 프롬프트 호출 (지문 / Face ID / Windows Hello)
        const assertion = await navigator.credentials.get({
            publicKey: options
        });

        if (!assertion) {
            alert("생체인증 로그인이 취소되었습니다.");
            return;
        }

        // 4) 서버 전송용 assertion payload 직렬화
        const payload = {
            id: assertion.id,
            rawId: bufferToBase64url(assertion.rawId),
            type: assertion.type,
            response: {
                clientDataJSON: bufferToBase64url(assertion.response.clientDataJSON),
                authenticatorData: bufferToBase64url(assertion.response.authenticatorData),
                signature: bufferToBase64url(assertion.response.signature),
                userHandle: assertion.response.userHandle ? bufferToBase64url(assertion.response.userHandle) : null,
            }
        };

        // 5) 서버 검증 및 자동 로그인 처리
        const verifyRes = await fetch("/auth/webauthn/login-verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const verifyData = await verifyRes.json();
        if (verifyData.success) {
            window.location.href = verifyData.redirect || "/";
        } else {
            alert(verifyData.message || "생체인증 로그인에 실패했습니다.");
        }

    } catch (err) {
        console.error("생체인증 로그인 오류:", err);
        if (err.name === "NotAllowedError") {
            // 사용자가 취소한 경우 조용히 처리하거나 가벼운 알림
            console.log("생체인증 취소됨");
        } else {
            alert("생체인증 로그인 중 오류가 발생했습니다: " + (err.message || err));
        }
    }
}
