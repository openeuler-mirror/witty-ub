#include "urma_failure_273.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure273> g_urma("urma_273");

bool UrmaFailure273::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_register_seg' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid token id for register bondp seg')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure273::GetName() const
{
    return "bondp_register_seg 校验 segment 无效导致注册流程拒绝继续执行";
}

std::string UrmaFailure273::GetRootCauseDesc() const
{
    return "bondp_register_seg 在执行注册前发现调用方传入的 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure273::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure273::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure273::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid token id for register bondp seg";
}

std::string UrmaFailure273::GetId() const
{
    return "urma_273";
}

} // namespace diag
