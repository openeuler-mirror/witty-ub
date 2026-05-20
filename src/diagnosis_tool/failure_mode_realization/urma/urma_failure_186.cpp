#include "urma_failure_186.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure186> g_urma("urma_186");

bool UrmaFailure186::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_pjfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid param jfc'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure186::GetName() const
{
    return "bondp_create_pjfr 校验 JFR 无效导致创建流程拒绝继续执行";
}

std::string UrmaFailure186::GetRootCauseDesc() const
{
    return "bondp_create_pjfr 在执行创建前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure186::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure186::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure186::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param jfc";
}

std::string UrmaFailure186::GetId() const
{
    return "urma_186";
}

} // namespace diag
