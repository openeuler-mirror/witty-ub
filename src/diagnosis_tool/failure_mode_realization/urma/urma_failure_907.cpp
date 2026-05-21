#include "urma_failure_907.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure907> g_urma("urma_907");

bool UrmaFailure907::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'check_valid_jfr_wr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'There are invalid parameters'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure907::GetName() const
{
    return "check_valid_jfr_wr 校验 JFR 无效导致校验流程拒绝继续执行";
}

std::string UrmaFailure907::GetRootCauseDesc() const
{
    return "check_valid_jfr_wr 在执行校验前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure907::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure907::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure907::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：There are invalid parameters";
}

std::string UrmaFailure907::GetId() const
{
    return "urma_907";
}

} // namespace diag
