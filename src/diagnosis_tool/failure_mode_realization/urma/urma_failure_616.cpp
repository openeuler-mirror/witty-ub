#include "urma_failure_616.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure616> g_urma("urma_616");

bool UrmaFailure616::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_rearm_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid param'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure616::GetName() const
{
    return "bondp_rearm_jfc 校验 JFC 无效导致重挂流程拒绝继续执行";
}

std::string UrmaFailure616::GetRootCauseDesc() const
{
    return "bondp_rearm_jfc 在执行重挂前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure616::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure616::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure616::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param";
}

std::string UrmaFailure616::GetId() const
{
    return "urma_616";
}

} // namespace diag
