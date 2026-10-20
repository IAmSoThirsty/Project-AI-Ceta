// Project-AI: CETA native owner ceremony. No authority/grant issuance.
// Input/output are private inherited pipes. Only hardware-origin input in the
// explicitly interactive window can invoke desktop UserConsentVerifier.
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <userconsentverifierinterop.h>
#include <bcrypt.h>
#include <sddl.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Security.Credentials.UI.h>
#include <winrt/Windows.Data.Json.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace winrt;
using namespace Windows::Foundation;
using namespace Windows::Security::Credentials::UI;
using namespace Windows::Data::Json;
static_assert(sizeof(void*) == 8, "Windows x64 required");
static_assert(sizeof(TOKEN_STATISTICS) == 56, "Token ABI changed");

struct Handle {
    HANDLE value{};
    Handle() = default;
    explicit Handle(HANDLE v) : value(v) {}
    Handle(Handle const&) = delete;
    ~Handle() { if (value && value != INVALID_HANDLE_VALUE) CloseHandle(value); }
};
static void need(bool value, char const* code) { if (!value) throw std::runtime_error(code); }
static std::string json_quote(std::string const& value) {
    std::string result = "\"";
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') { result += '\\'; result += static_cast<char>(c); }
        else { need(c >= 32 && c < 127, "OUTPUT_STRING_RANGE"); result += static_cast<char>(c); }
    }
    return result + '"';
}
using Object = std::map<std::string, std::string>;
static std::string object(Object const& values) {
    std::string result = "{"; bool first = true;
    for (auto const& [name, value] : values) { if (!first) result += ','; first = false; result += json_quote(name) + ':' + value; }
    return result + '}';
}
static std::string hex(std::uint8_t const* data, size_t count) {
    constexpr char digits[] = "0123456789abcdef"; std::string result; result.reserve(count * 2);
    for (size_t i = 0; i < count; ++i) { result += digits[data[i] >> 4]; result += digits[data[i] & 15]; }
    return result;
}
static std::string sha(std::string const& input) {
    BCRYPT_ALG_HANDLE algorithm{}; BCRYPT_HASH_HANDLE hash{};
    need(BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) == 0, "HASH_PROVIDER");
    std::array<std::uint8_t, 32> output{};
    try {
        need(BCryptCreateHash(algorithm, &hash, nullptr, 0, nullptr, 0, 0) == 0, "HASH_CREATE");
        need(BCryptHashData(hash, reinterpret_cast<PUCHAR>(const_cast<char*>(input.data())), static_cast<ULONG>(input.size()), 0) == 0, "HASH_UPDATE");
        need(BCryptFinishHash(hash, output.data(), static_cast<ULONG>(output.size()), 0) == 0, "HASH_FINISH");
    } catch (...) { if (hash) BCryptDestroyHash(hash); BCryptCloseAlgorithmProvider(algorithm, 0); throw; }
    BCryptDestroyHash(hash); BCryptCloseAlgorithmProvider(algorithm, 0); return hex(output.data(), output.size());
}
static std::string commitment(char const* domain, std::string const& wire) {
    std::string preimage = std::string("CETA:kernel:") + domain; preimage += '\0'; preimage += wire;
    return "sha256:" + sha(preimage);
}
static std::wstring wide(std::string const& value) {
    int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0);
    need(count > 0, "UTF8_INVALID"); std::wstring result(count, L'\0');
    need(MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), result.data(), count) == count, "UTF8_INVALID");
    return result;
}
static std::string utf8(std::wstring const& value) { return to_string(hstring(value)); }
static std::string sid(PSID value) {
    need(value && IsValidSid(value), "TOKEN_SID_INVALID"); LPWSTR text{};
    need(ConvertSidToStringSidW(value, &text) != FALSE, "TOKEN_SID_TEXT");
    std::string result;
    try { result = utf8(text); } catch (...) { LocalFree(text); throw; }
    need(LocalFree(text) == nullptr, "TOKEN_SID_TEXT_RELEASE"); return result;
}
static std::vector<std::uint8_t> token_data(HANDLE token, TOKEN_INFORMATION_CLASS kind) {
    DWORD bytes{}; SetLastError(0);
    need(!GetTokenInformation(token, kind, nullptr, 0, &bytes) && GetLastError() == ERROR_INSUFFICIENT_BUFFER && bytes && bytes <= 65536, "TOKEN_QUERY_SIZE");
    std::vector<std::uint8_t> result(bytes); DWORD returned{};
    need(GetTokenInformation(token, kind, result.data(), bytes, &returned) && returned == bytes, "TOKEN_QUERY"); return result;
}
static std::uint64_t filetime(FILETIME value) { return (std::uint64_t(value.dwHighDateTime) << 32) | value.dwLowDateTime; }
static std::string image_path() {
    std::vector<wchar_t> buffer(32768); DWORD count = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    need(count && count < buffer.size(), "IMAGE_PATH"); return utf8(std::wstring(buffer.data(), count));
}
static std::string image_hash() {
    auto path = wide(image_path()); Handle image(CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
    need(image.value != INVALID_HANDLE_VALUE, "IMAGE_OPEN"); BY_HANDLE_FILE_INFORMATION info{}; LARGE_INTEGER size{};
    need(GetFileInformationByHandle(image.value, &info) && !(info.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY)) &&
         GetFileSizeEx(image.value, &size) && size.QuadPart > 0 && size.QuadPart <= 134217728, "IMAGE_IDENTITY");
    std::string bytes; bytes.reserve(static_cast<size_t>(size.QuadPart)); std::array<char, 65536> buffer{}; DWORD read{};
    do { need(ReadFile(image.value, buffer.data(), static_cast<DWORD>(buffer.size()), &read, nullptr), "IMAGE_READ"); bytes.append(buffer.data(), read); } while (read);
    need(bytes.size() == static_cast<size_t>(size.QuadPart), "IMAGE_CHANGED"); return "sha256:" + sha(bytes);
}
static Object provenance() {
    Handle token; need(OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token.value), "TOKEN_OPEN");
    auto before = token_data(token.value, TokenStatistics);
    auto user = token_data(token.value, TokenUser), logon = token_data(token.value, TokenLogonSid);
    auto integrity = token_data(token.value, TokenIntegrityLevel), elevation = token_data(token.value, TokenElevationType);
    auto ui = token_data(token.value, TokenUIAccess), session = token_data(token.value, TokenSessionId), app = token_data(token.value, TokenIsAppContainer);
    need(user.size() >= sizeof(TOKEN_USER) && logon.size() >= sizeof(TOKEN_GROUPS) && integrity.size() >= sizeof(TOKEN_MANDATORY_LABEL), "TOKEN_STRUCT_ABI");
    auto groups = reinterpret_cast<TOKEN_GROUPS const*>(logon.data());
    need(groups->GroupCount == 1 && (groups->Groups[0].Attributes & SE_GROUP_LOGON_ID) == SE_GROUP_LOGON_ID, "TOKEN_LOGON");
    need(app.size() == 4 && *reinterpret_cast<DWORD*>(app.data()) == 0, "APP_CONTAINER_DENIED");
    need(elevation.size() == 4 && (ui.size() == 1 || ui.size() == 4) && session.size() == 4, "TOKEN_SCALAR_ABI");
    auto ui_access = ui.size() == 1 ? DWORD(ui[0]) : *reinterpret_cast<DWORD*>(ui.data()); need(ui_access <= 1, "TOKEN_UI_ACCESS");
    auto restriction = token_data(token.value, TokenHasRestrictions); need(restriction.size() == 1 || restriction.size() == 4, "TOKEN_RESTRICTION_ABI");
    auto restricted = restriction.size() == 1 ? DWORD(restriction[0]) : *reinterpret_cast<DWORD*>(restriction.data()); need(restricted <= 1, "TOKEN_RESTRICTION_VALUE");
    auto restricted_groups = token_data(token.value, TokenRestrictedSids); need(restricted_groups.size() >= offsetof(TOKEN_GROUPS, Groups), "TOKEN_RESTRICTED_ABI");
    auto restricted_count = reinterpret_cast<TOKEN_GROUPS const*>(restricted_groups.data())->GroupCount;
    need(offsetof(TOKEN_GROUPS, Groups) + size_t(restricted_count) * sizeof(SID_AND_ATTRIBUTES) <= restricted_groups.size(), "TOKEN_RESTRICTED_ABI");
    auto statistics = reinterpret_cast<TOKEN_STATISTICS const*>(before.data());
    need(before.size() == sizeof(TOKEN_STATISTICS) && statistics->TokenType == TokenPrimary, "TOKEN_STATISTICS_ABI");
    auto label = reinterpret_cast<TOKEN_MANDATORY_LABEL const*>(integrity.data());
    FILETIME creation{}, exit{}, kernel{}, cpu{}; need(GetProcessTimes(GetCurrentProcess(), &creation, &exit, &kernel, &cpu), "PROCESS_TIME");
    DWORD terminal{}; need(ProcessIdToSessionId(GetCurrentProcessId(), &terminal) && terminal == *reinterpret_cast<DWORD*>(session.data()), "PROCESS_SESSION");
    auto after = token_data(token.value, TokenStatistics); need(before == after, "TOKEN_CHANGED");
    return {{"authentication_high", std::to_string(statistics->AuthenticationId.HighPart)}, {"authentication_low", std::to_string(statistics->AuthenticationId.LowPart)},
        {"creation_time", std::to_string(filetime(creation))}, {"elevation_type", std::to_string(*reinterpret_cast<DWORD*>(elevation.data()))},
        {"image_digest", json_quote(image_hash())}, {"integrity_sid", json_quote(sid(label->Label.Sid))},
        {"logon_sid", json_quote(sid(groups->Groups[0].Sid))}, {"pid", std::to_string(GetCurrentProcessId())},
        {"restricted", restricted ? "true" : "false"}, {"restricted_sid_count", std::to_string(restricted_count)}, {"integrity_attributes", std::to_string(label->Label.Attributes)}, {"modified_id_high", std::to_string(statistics->ModifiedId.HighPart)}, {"modified_id_low", std::to_string(statistics->ModifiedId.LowPart)}, {"terminal_session", std::to_string(terminal)},
        {"token_id_high", std::to_string(statistics->TokenId.HighPart)}, {"token_id_low", std::to_string(statistics->TokenId.LowPart)},
        {"ui_access", std::to_string(ui_access)}, {"user_sid", json_quote(sid(reinterpret_cast<TOKEN_USER*>(user.data())->User.Sid))}};
}

// Narrow integer-only canonical JSON for the two declared request domains.
// Enrollment adds canonical backslash escapes in ordinary volume-GUID paths.
struct CanonicalRequest {
    std::string const& bytes; size_t at{}, nodes{};
    char take() { need(at < bytes.size(), "REQUEST_TRUNCATED"); return bytes[at++]; }
    std::string string() {
        need(take() == '"', "REQUEST_STRING"); std::string result;
        while (true) {
            char c = take(); if (c == '"') return result;
            if (c == '\\') { c = take(); need(c == '\\' || c == '"', "REQUEST_STRING_ESCAPE"); }
            else need(c >= 32 && c < 127, "REQUEST_STRING_RANGE");
            result += c;
        }
    }
    void value(unsigned depth = 0) {
        need(depth <= 24 && ++nodes <= 4096 && at < bytes.size(), "REQUEST_BOUNDS"); char c = bytes[at];
        if (c == '{') {
            ++at; std::string prior; bool first = true;
            if (at < bytes.size() && bytes[at] == '}') { ++at; return; }
            while (true) { auto key = string(); need(first || prior < key, "REQUEST_KEY_ORDER_OR_DUPLICATE"); first = false; prior = key;
                need(take() == ':', "REQUEST_COLON"); value(depth + 1); char delimiter = take(); if (delimiter == '}') return; need(delimiter == ',', "REQUEST_OBJECT"); }
        }
        if (c == '[') { ++at; if (at < bytes.size() && bytes[at] == ']') { ++at; return; }
            while (true) { value(depth + 1); char delimiter = take(); if (delimiter == ']') return; need(delimiter == ',', "REQUEST_ARRAY"); } }
        if (c == '"') { string(); return; }
        for (auto literal : {"true", "false", "null"}) {
            size_t count = strlen(literal); if (bytes.compare(at, count, literal) == 0) { at += count; return; }
        }
        bool negative = c == '-'; if (negative) ++at;
        need(at < bytes.size() && bytes[at] >= '0' && bytes[at] <= '9', "REQUEST_INTEGER");
        size_t start = at; std::uint64_t number = 0, limit = negative ? 9223372036854775808ull : 9223372036854775807ull;
        while (at < bytes.size() && bytes[at] >= '0' && bytes[at] <= '9') { unsigned digit = bytes[at++] - '0'; need(number <= (limit - digit) / 10, "REQUEST_INTEGER_RANGE"); number = number * 10 + digit; }
        need(!(at - start > 1 && bytes[start] == '0') && !(negative && number == 0), "REQUEST_INTEGER_CANONICAL");
    }
    void check() { value(); need(at == bytes.size(), "REQUEST_TRAILING_OR_NONCANONICAL"); }
};
static bool identifier(std::string const& value) {
    if (value.empty() || value.size() > 160) return false;
    auto alpha = [](char c) { return c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9'; };
    if (!alpha(value[0])) return false;
    return std::all_of(value.begin(), value.end(), [&](char c) { return alpha(c) || c == '.' || c == '_' || c == ':' || c == '/' || c == '-'; });
}
static std::uint64_t ticks() { LARGE_INTEGER value{}; need(QueryPerformanceCounter(&value), "QPC"); return value.QuadPart; }
struct Channels {
    HANDLE input{}, output{}, cancel{}; ULONGLONG deadline{};
    bool cancelled() const { DWORD status = WaitForSingleObject(cancel, 0); need(status == WAIT_TIMEOUT || status == WAIT_OBJECT_0, "CANCEL_EVENT"); return status == WAIT_OBJECT_0; }
    bool expired() const { return GetTickCount64() >= deadline; }
    std::string read(size_t count) {
        need(count <= 40960, "FRAME_BOUND"); std::string result;
        while (result.size() < count) {
            need(!cancelled() && !expired(), "INPUT_CANCELLED_OR_EXPIRED"); DWORD available{};
            need(PeekNamedPipe(input, nullptr, 0, nullptr, &available, nullptr), "INPUT_PIPE");
            if (!available) { WaitForSingleObject(cancel, 5); continue; }
            char buffer[4096]; DWORD actual{}, wanted = static_cast<DWORD>(std::min<size_t>({sizeof(buffer), available, count - result.size()}));
            need(ReadFile(input, buffer, wanted, &actual, nullptr) && actual && actual <= wanted, "INPUT_READ"); result.append(buffer, actual);
        }
        return result;
    }
    std::uint32_t number() { auto raw = read(4); std::uint32_t value{}; memcpy(&value, raw.data(), 4); return value; }
    std::string text(size_t maximum) { auto count = number(); need(count <= maximum, "FRAME_FIELD_BOUND"); return read(count); }
    void write(std::string const& body) {
        need(body.size() <= 16384, "OUTPUT_BOUND"); std::string wire = "CETAAO01"; std::uint32_t size = static_cast<std::uint32_t>(body.size()); wire.append(reinterpret_cast<char*>(&size), 4); wire += body;
        DWORD written{}; need(WriteFile(output, wire.data(), static_cast<DWORD>(wire.size()), &written, nullptr) && written == wire.size(), "OUTPUT_WRITE");
    }
};
struct Challenge {
    unsigned mode{}; unsigned timeout{}; bool enrollment{}; std::string id, nonce, body, request_digest, display_digest, display;
};
static Challenge input(Channels& channel, bool enrollment = false) {
    need(channel.read(8) == "CETAAP01", "FRAME_MAGIC"); Challenge value;
    value.enrollment = enrollment;
    value.mode = channel.number(); value.timeout = channel.number();
    need(value.mode >= 1 && value.mode <= 4 && value.timeout >= 20 && value.timeout <= 300000, "MODE_OR_TIMEOUT");
    value.id = channel.text(160); need(identifier(value.id), "CHALLENGE_ID");
    auto nonce = channel.read(32); need(std::any_of(nonce.begin(), nonce.end(), [](char c) { return c != 0; }), "NONCE_REQUIRED");
    value.nonce = hex(reinterpret_cast<std::uint8_t const*>(nonce.data()), nonce.size());
    value.body = channel.text(32768); value.request_digest = channel.text(71); value.display_digest = channel.text(71);
    while (true) {
        DWORD extra{}; SetLastError(0);
        if (!PeekNamedPipe(channel.input, nullptr, 0, nullptr, &extra, nullptr)) { need(GetLastError() == ERROR_BROKEN_PIPE, "INPUT_EOF"); break; }
        need(extra == 0 && !channel.cancelled() && !channel.expired(), "TRAILING_OR_UNFINISHED_INPUT");
        WaitForSingleObject(channel.cancel, 5);
    }
    channel.deadline = GetTickCount64() + value.timeout;
    if (value.mode == 1) { need(!enrollment && value.body.empty() && value.request_digest.empty() && value.display_digest.empty(), "AVAILABILITY_HAS_REQUEST"); return value; }
    need(!value.body.empty(), "REQUEST_REQUIRED"); CanonicalRequest{value.body}.check();
    auto request = JsonObject::Parse(hstring(wide(value.body)));
    std::set<std::wstring> expected = enrollment ? std::set<std::wstring>{L"actor_session",L"adapter_commitment",L"allowed_operations",L"approval_mode",L"assurance",L"authority_budget",L"authority_generation",L"ceremony_nonce",L"challenge_id",L"clock_session_nonce",L"database",L"deadline",L"environment_commitment",L"evidence_reserve_bytes",L"helper_commitment",L"helper_identity",L"installation_id",L"kind",L"maximum_effect_duration_ns",L"maximum_effects",L"maximum_observation_age_ns",L"maximum_session_ns",L"maximum_workers",L"operation_limits",L"owner_facts",L"owner_session_nonce",L"policy_commitment",L"policy_generation",L"principal_id",L"private_root",L"profile",L"recovery_budget",L"request_id",L"resource_limit",L"runtime_profile",L"scope_id",L"source_commitment",L"ui_commitment",L"ui_identity",L"worker_image_commitment"} :
      std::set<std::wstring>{L"request_id",L"scope_id",L"task_id",L"proposal_id",L"principal_id",L"actor_session",L"owner_session_nonce",L"operation",L"process_identity",L"job_digest",L"expected_limit",L"target_limit",L"original_limit",L"task_revision",L"policy_commitment",L"adapter_commitment",L"environment_commitment",L"source_commitment",L"observer_commitment",L"operation_budget",L"required_outcome_bytes",L"deadline",L"maximum_observation_age_ns",L"maximum_duration_ns",L"consequences",L"restoration_of",L"original_request_commitment",L"profile"};
    need(request.Size() == expected.size(), "REQUEST_FIELDS"); for (auto const& item : request) need(expected.erase(std::wstring(item.Key())), "REQUEST_FIELDS");
    if (enrollment) {
        need(request.GetNamedString(L"profile") == L"ceta-owner-enrollment-data-v1" &&
             request.GetNamedString(L"kind") == L"OWNER_ENROLLMENT_REQUEST" &&
             request.GetNamedString(L"assurance") == L"DATA_ONLY" &&
             request.GetNamedString(L"runtime_profile") == L"ceta-owned-real-effect-v1" &&
             request.GetNamedString(L"approval_mode") == L"SEPARATE_CANONICAL_APPROVAL_PER_EFFECT", "ENROLLMENT_PROFILE");
        need(to_string(request.GetNamedString(L"challenge_id")) == value.id, "ENROLLMENT_CHALLENGE");
        auto semantic = to_string(request.GetNamedString(L"ceremony_nonce"));
        need(semantic.size() == 32 && std::all_of(semantic.begin(), semantic.end(), [](char c) {return c >= '0' && c <= '9' || c >= 'a' && c <= 'f';}) &&
             std::any_of(semantic.begin(), semantic.end(), [](char c) {return c != '0';}), "ENROLLMENT_NONCE");
        need(value.request_digest == commitment("owner-enrollment-input-v1", value.body), "ENROLLMENT_COMMITMENT");
        value.display = "{\"assurance\":\"DATA_ONLY\",\"display_profile\":\"ceta-owner-enrollment-display-v1\",\"input_commitment\":" + json_quote(value.request_digest) + ",\"request\":" + value.body + '}';
        need(value.display_digest == commitment("owner-enrollment-display-v1", value.display), "ENROLLMENT_DISPLAY_COMMITMENT");
        return value;
    }
    need(request.GetNamedString(L"profile") == L"ceta-owned-real-effect-v1", "REQUEST_PROFILE");
    need(request.GetNamedString(L"operation") == L"owned-worker.cpu-cap" || request.GetNamedString(L"operation") == L"owned-worker.cpu-restore", "REQUEST_OPERATION");
    need(identifier(to_string(request.GetNamedString(L"request_id"))), "REQUEST_ID");
    need(value.request_digest == commitment("owned-cpu-request-v1", value.body), "REQUEST_COMMITMENT");
    value.display = "{\"display_profile\":\"ceta-owned-cpu-approval-display-v1\",\"request\":" + value.body + ",\"request_commitment\":" + json_quote(value.request_digest) + '}';
    need(value.display_digest == commitment("owned-cpu-approval-display-v1", value.display), "DISPLAY_COMMITMENT");
    return value;
}
struct View {
    Challenge const& challenge; Channels& channels; HWND window{}, edit{}; bool click{}, cancelled{}, display_exact{};
    IAsyncOperation<UserConsentVerificationResult> verification{nullptr}; HRESULT native_hresult = S_OK;
    std::wstring text;
};
static bool display_current(View const& view) {
    int count = GetWindowTextLengthW(view.edit); if (count < 0 || size_t(count) != view.text.size()) return false;
    std::vector<wchar_t> bytes(size_t(count) + 1); return GetWindowTextW(view.edit, bytes.data(), count + 1) == count && std::wstring(bytes.data(), count) == view.text;
}
static bool hardware_input(HWND window) {
    INPUT_MESSAGE_SOURCE source{};
    return GetCurrentInputMessageSource(&source) && source.originId == IMO_HARDWARE && source.deviceType != IMDT_UNAVAILABLE && GetForegroundWindow() == window;
}
static LRESULT CALLBACK window_proc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    auto view = reinterpret_cast<View*>(GetWindowLongPtrW(window, GWLP_USERDATA));
    if (message == WM_NCCREATE) { view = reinterpret_cast<View*>(reinterpret_cast<CREATESTRUCTW*>(lparam)->lpCreateParams); SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(view)); }
    if (!view) return DefWindowProcW(window, message, wparam, lparam);
    if (message == WM_CLOSE || message == WM_KEYUP && wparam == VK_ESCAPE) { view->cancelled = true; return 0; }
    if (message == WM_LBUTTONUP || message == WM_KEYUP && (wparam == VK_RETURN || wparam == VK_SPACE)) {
        RECT area{}; GetClientRect(window, &area);
        bool hit = message == WM_KEYUP || HIWORD(lparam) >= area.bottom - 75 && LOWORD(lparam) >= 20 && LOWORD(lparam) < area.right / 2;
        if (view->challenge.mode == 3 && hit && !view->click && !view->cancelled && !view->channels.cancelled() && !view->channels.expired() && view->display_exact && display_current(*view) && hardware_input(window)) {
            view->click = true;
            try {
                auto interop = get_activation_factory<UserConsentVerifier, ::IUserConsentVerifierInterop>();
                hstring message_text = L"Approve the exact Project-AI: CETA request displayed in this window. Display commitment: " + hstring(wide(view->challenge.display_digest));
                check_hresult(interop->RequestVerificationForWindowAsync(window, reinterpret_cast<HSTRING>(get_abi(message_text)),
                    guid_of<IAsyncOperation<UserConsentVerificationResult>>(), put_abi(view->verification)));
            } catch (hresult_error const& error) { view->native_hresult = error.code(); }
            catch (...) { view->native_hresult = E_FAIL; }
            InvalidateRect(window, nullptr, TRUE);
        }
        return 0;
    }
    if (message == WM_PAINT) {
        PAINTSTRUCT paint{}; HDC dc = BeginPaint(window, &paint); RECT area{}; GetClientRect(window, &area);
        RECT button{20, area.bottom - 65, area.right / 2, area.bottom - 20}; DrawEdge(dc, &button, EDGE_RAISED, BF_RECT);
        DrawTextW(dc, view->click ? L"Authentication requested" : L"Continue to Windows authentication", -1, &button, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
        EndPaint(window, &paint); return 0;
    }
    return DefWindowProcW(window, message, wparam, lparam);
}
static void create_view(View& view, bool visible) {
    WNDCLASSW cls{}; cls.lpfnWndProc = window_proc; cls.hInstance = GetModuleHandleW(nullptr); cls.lpszClassName = L"CETA.NativeOwnerApproval.V1"; cls.hCursor = LoadCursorW(nullptr, MAKEINTRESOURCEW(32512)); cls.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1);
    need(RegisterClassW(&cls) || GetLastError() == ERROR_CLASS_ALREADY_EXISTS, "WINDOW_CLASS");
    view.window = CreateWindowExW(0, cls.lpszClassName, view.challenge.enrollment ? L"Project-AI: CETA — bounded owner enrollment" : L"Project-AI: CETA — exact request approval", WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT, 980, 740, nullptr, nullptr, cls.hInstance, &view);
    need(view.window != nullptr, "WINDOW_CREATE");
    view.text = (view.challenge.enrollment ? L"Enroll only this exact bounded owner session. Every CPU effect requires its own separate approval. This ceremony performs no CPU effect. Closing cancels.\r\n" : L"Review the complete immutable request below. Closing this window cancels.\r\n") +
        std::wstring(L"Request commitment: ") + wide(view.challenge.request_digest) +
        L"\r\nDisplay commitment: " + wide(view.challenge.display_digest) + L"\r\nExact request and consequences:\r\n" + wide(view.challenge.display);
    view.edit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", L"", WS_CHILD | WS_VISIBLE | WS_VSCROLL | ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL,
        15, 15, 930, 605, view.window, nullptr, cls.hInstance, nullptr);
    need(view.edit != nullptr, "DISPLAY_CREATE"); SendMessageW(view.edit, EM_SETLIMITTEXT, 65535, 0);
    need(SetWindowTextW(view.edit, view.text.c_str()), "DISPLAY_SET");
    int count = GetWindowTextLengthW(view.edit); std::vector<wchar_t> readback(static_cast<size_t>(count) + 1);
    need(GetWindowTextW(view.edit, readback.data(), count + 1) == count, "DISPLAY_READBACK");
    view.display_exact = std::wstring(readback.data(), count) == view.text; need(view.display_exact, "DISPLAY_MISMATCH");
    if (visible) { ShowWindow(view.window, SW_SHOWNORMAL); UpdateWindow(view.window); }
}
static std::string interop_module() {
    auto factory = get_activation_factory<UserConsentVerifier, ::IUserConsentVerifierInterop>();
    auto vtable = *reinterpret_cast<void***>(factory.get()); HMODULE module{};
    need(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        reinterpret_cast<LPCWSTR>(vtable[6]), &module), "INTEROP_MODULE");
    std::array<wchar_t, 32768> path{}; DWORD count = GetModuleFileNameW(module, path.data(), static_cast<DWORD>(path.size()));
    need(count && count < path.size(), "INTEROP_MODULE_PATH"); return utf8(std::wstring(path.data(), count));
}
static Object prepared(Channels& channels) {
    auto started = ticks(); auto module = interop_module();
    auto availability = UserConsentVerifier::CheckAvailabilityAsync();
    while (availability.Status() == winrt::Windows::Foundation::AsyncStatus::Started && !channels.cancelled() && !channels.expired()) WaitForSingleObject(channels.cancel, 10);
    if (availability.Status() == winrt::Windows::Foundation::AsyncStatus::Started) {
        availability.Cancel(); need(false, "PREPARATION_CANCELLED_OR_EXPIRED");
    }
    need(!channels.cancelled() && !channels.expired() && availability.Status() == winrt::Windows::Foundation::AsyncStatus::Completed, "PREPARATION_UNAVAILABLE");
    auto available = availability.GetResults(); LARGE_INTEGER frequency{};
    need(QueryPerformanceFrequency(&frequency), "QPC_FREQUENCY");
    return {{"authentication_invoked", "false"}, {"availability", std::to_string(static_cast<int>(available))},
        {"finished_qpc", std::to_string(ticks())}, {"interop_module", json_quote(module)},
        {"phase", json_quote("PREPARED")}, {"protocol", json_quote("ceta-native-owner-approval-v1")},
        {"provenance", object(provenance())}, {"qpc_frequency", std::to_string(frequency.QuadPart)},
        {"started_qpc", std::to_string(started)}};
}
static Object ceremony(Challenge const& challenge, Channels& channels) {
    Object result{{"authentication_invoked", "false"}, {"availability", "null"}, {"body_sha256", json_quote(sha(challenge.body))},
        {"challenge_id", json_quote(challenge.id)}, {"display_commitment", json_quote(challenge.display_digest)}, {"display_exact", "false"},
        {"display_sha256", json_quote(sha(challenge.display))}, {"hardware_click", "false"}, {"mode", std::to_string(challenge.mode)},
        {"native_hresult", "0"}, {"native_result", "null"}, {"nonce", json_quote(challenge.nonce)},
        {"protocol", json_quote("ceta-native-owner-approval-v1")}, {"request_commitment", json_quote(challenge.request_digest)},
        {"status", json_quote("UNAVAILABLE")}};
    if (channels.cancelled() || challenge.mode == 4) { result["status"] = json_quote("CANCELLED"); return result; }
    result["interop_module"] = json_quote(interop_module());
    auto availability = UserConsentVerifier::CheckAvailabilityAsync();
    while (availability.Status() == winrt::Windows::Foundation::AsyncStatus::Started && !channels.cancelled() && !channels.expired()) WaitForSingleObject(channels.cancel, 10);
    if (availability.Status() == winrt::Windows::Foundation::AsyncStatus::Started) { availability.Cancel(); result["status"] = json_quote(channels.cancelled() ? "CANCELLED" : "TIMED_OUT"); return result; }
    need(availability.Status() == winrt::Windows::Foundation::AsyncStatus::Completed, "AVAILABILITY_ASYNC");
    auto available = availability.GetResults(); result["availability"] = std::to_string(static_cast<int>(available));
    if (challenge.mode == 1 || available != UserConsentVerifierAvailability::Available) { result["status"] = json_quote(available == UserConsentVerifierAvailability::Available ? "AVAILABLE" : "UNAVAILABLE"); return result; }
    View view{challenge, channels};
    try {
        create_view(view, challenge.mode == 3); result["display_exact"] = "true";
        if (challenge.mode == 2) { result["status"] = json_quote("DISPLAY_BOUND_UNSHOWN"); DestroyWindow(view.window); return result; }
        bool cancel_requested = false;
        while (true) {
            MSG message{}; while (PeekMessageW(&message, nullptr, 0, 0, PM_REMOVE)) { TranslateMessage(&message); DispatchMessageW(&message); }
            bool cancel = view.cancelled || channels.cancelled(), expired = channels.expired();
            if (view.verification && (cancel || expired) && !cancel_requested) { view.verification.Cancel(); cancel_requested = true; }
            if (view.native_hresult < 0) { result["native_hresult"] = std::to_string(view.native_hresult); result["status"] = json_quote("UNAVAILABLE"); break; }
            if (view.verification && view.verification.Status() != winrt::Windows::Foundation::AsyncStatus::Started) {
                if (view.verification.Status() == winrt::Windows::Foundation::AsyncStatus::Completed) {
                    auto native = view.verification.GetResults(); result["native_result"] = std::to_string(static_cast<int>(native));
                    result["status"] = json_quote(cancel ? "CANCELLED" : expired ? "TIMED_OUT" : native == UserConsentVerificationResult::Verified ? "VERIFIED" : "DENIED");
                } else { result["native_hresult"] = std::to_string(view.verification.ErrorCode().value); result["status"] = json_quote(cancel ? "CANCELLED" : "UNAVAILABLE"); }
                break;
            }
            if (!view.verification && (cancel || expired)) { result["status"] = json_quote(cancel ? "CANCELLED" : "TIMED_OUT"); break; }
            MsgWaitForMultipleObjectsEx(1, &channels.cancel, 20, QS_ALLINPUT, MWMO_INPUTAVAILABLE);
        }
        result["hardware_click"] = view.click ? "true" : "false"; result["authentication_invoked"] = view.verification ? "true" : "false";
        DestroyWindow(view.window);
    } catch (...) { if (view.window) DestroyWindow(view.window); throw; }
    return result;
}
static HANDLE handle_arg(wchar_t const* value) {
    need(value && *value, "HANDLE_ARGUMENT"); std::wstring text(value);
    need(text.size() <= 20 && std::all_of(text.begin(), text.end(), [](wchar_t c) { return c >= L'0' && c <= L'9'; }), "HANDLE_ARGUMENT");
    unsigned long long number = std::stoull(text); need(number && number != ~0ull, "HANDLE_ARGUMENT");
    HANDLE handle = reinterpret_cast<HANDLE>(number); DWORD flags{};
    need(GetHandleInformation(handle, &flags) && flags & HANDLE_FLAG_INHERIT, "INHERITED_HANDLE_REQUIRED"); return handle;
}
int wmain(int argc, wchar_t** argv) {
    bool enrollment = argc == 6 && std::wstring(argv[5]) == L"prepare-enrollment-v1";
    if (argc != 5 && !enrollment) return 64;
    try {
        init_apartment(apartment_type::multi_threaded);
        Handle input_handle(handle_arg(argv[1])), output_handle(handle_arg(argv[2])), cancel_handle(handle_arg(argv[3])), gate_handle(handle_arg(argv[4]));
        need(input_handle.value != output_handle.value && input_handle.value != cancel_handle.value && output_handle.value != cancel_handle.value && gate_handle.value != input_handle.value && gate_handle.value != output_handle.value && gate_handle.value != cancel_handle.value, "HANDLE_ALIAS");
        need(GetFileType(input_handle.value) == FILE_TYPE_PIPE && GetFileType(output_handle.value) == FILE_TYPE_PIPE, "PRIVATE_PIPE_REQUIRED");
        Channels channels{input_handle.value, output_handle.value, cancel_handle.value, GetTickCount64() + 10000};
        Object result;
        try {
            if (enrollment) channels.write(object(prepared(channels)));
            while (true) {
                DWORD gate_status = WaitForSingleObject(gate_handle.value, 0); need(gate_status == WAIT_OBJECT_0 || gate_status == WAIT_TIMEOUT, "START_GATE_INVALID"); if (gate_status == WAIT_OBJECT_0) break;
                need(!channels.cancelled() && !channels.expired(), "START_GATE_CANCELLED_OR_EXPIRED"); WaitForSingleObject(channels.cancel, 5);
            }
            auto challenge = input(channels, enrollment); auto started = ticks(); result = ceremony(challenge, channels);
            result["started_qpc"] = std::to_string(started); result["finished_qpc"] = std::to_string(ticks());
            LARGE_INTEGER frequency{}; need(QueryPerformanceFrequency(&frequency), "QPC_FREQUENCY"); result["qpc_frequency"] = std::to_string(frequency.QuadPart);
        } catch (hresult_error const& error) { result = {{"error", json_quote("NATIVE_WINRT_UNAVAILABLE")}, {"native_hresult", std::to_string(error.code().value)}, {"status", json_quote("ERROR")}}; }
        catch (...) { result = {{"error", json_quote("NATIVE_PROTOCOL_OR_RUNTIME_REJECTED")}, {"status", json_quote("ERROR")}}; }
        result["provenance"] = object(provenance()); channels.write(object(result)); return 0;
    } catch (...) { return 65; }
}
